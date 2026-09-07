"""
splitter.py — Potong audio per chapter/surah menjadi MP3 (fitur Mini YT).

Pola ffmpeg mengikuti ClipForge (`server/services/filterHelpers.js buildCutArgs`):
- Input-side seek: `-ss <start>` SEBELUM `-i`
- Window durasi: `-t <dur>` (dur = end - start)
- Re-encode penuh ke format target + `-y`

Untuk kasus murottal Juz Amma, modul ini juga bisa:
1. Mencocokkan judul chapter ke urutan kanonik surah 78-114 (Juz 30).
2. Mendeteksi surah yang LONCAT/hilang di antara dua chapter berurutan
   (mis. "Surah Al Lahab" lalu "Surah Al Falaq" → Al Ikhlas tidak ada
   timestamp di deskripsi uploader → tergabung dalam chapter Al Lahab).
3. Trace batas surah yang hilang via Gemini (generateContent + inline audio)
   → sisipkan sebagai chapter baru → potong terpisah.
"""

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

try:
    import requests  # sudah ada di requirements.txt mini-YT
except ImportError:  # pragma: no cover
    requests = None

# ─── Lokasi ffmpeg ────────────────────────────────────────────────────────────

ENGINE_DIR = Path(__file__).resolve().parent.parent
BIN_DIR = ENGINE_DIR / "bin"


def resolve_ffmpeg():
    """ffmpeg bundled di _engine/bin lebih dulu, fallback ke PATH."""
    exe = BIN_DIR / "ffmpeg.exe"
    if exe.exists():
        return str(exe)
    found = shutil.which("ffmpeg")
    return found or "ffmpeg"


# ─── Sanitasi nama file (sama dengan downloader.sanitize_title) ───────────────

FORBIDDEN_RE = re.compile(r'[\\/*?:"<>|]')


def sanitize_filename(name):
    name = FORBIDDEN_RE.sub("-", str(name or ""))
    name = re.sub(r"\s{2,}", " ", name).strip().rstrip(". ")
    return name[:120].rstrip(". ") or "untitled"


# ─── Daftar surah Juz Amma (kanonik 78-114) + alias ejaan YouTube ─────────────
# Normalisasi: lowercase, buang apostrof/hyphen, alias disamakan saat match.

def _normalize(name):
    """Lowercase, buang apostrof/hyphen/karakter non-alfanumerik, rapikan spasi."""
    s = str(name or "").lower()
    s = re.sub(r"^surah\s+|^surat\s+", "", s)
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


JUZ_AMMA = [
    {"no": 78,  "title": "An Naba",      "aliases": ["an naba", "annaba", "naba", "an naba'"]},
    {"no": 79,  "title": "An Nazi'at",   "aliases": ["an naziat", "an nazi'at", "an-naziat", "annaziat", "naziat", "nazi'at"]},
    {"no": 80,  "title": "'Abasa",       "aliases": ["abasa", "abassa", "abasa'", "'abasa", "abas"]},
    {"no": 81,  "title": "At Takwir",    "aliases": ["at takwir", "attakwir", "takwir"]},
    {"no": 82,  "title": "Al Infitar",   "aliases": ["al infitar", "al-infitar", "infitar"]},
    {"no": 83,  "title": "Al Mutaffifin", "aliases": ["al mutafifin", "al mutaffifin", "al-mutaffifin", "mutaffifin", "mutafifin"]},
    {"no": 84,  "title": "Al Inshiqaq",  "aliases": ["al inshiqaq", "al insyiqaq", "al-inshiqaq", "inshiqaq", "insyiqaq"]},
    {"no": 85,  "title": "Al Buruj",     "aliases": ["al buruj", "al burooj", "al-buruj", "buruj", "burooj"]},
    {"no": 86,  "title": "At Tariq",     "aliases": ["at tariq", "attariq", "tariq"]},
    {"no": 87,  "title": "Al A'la",      "aliases": ["al a'la", "al ala", "ala", "al-a'la", "a'la"]},
    {"no": 88,  "title": "Al Ghashiyah", "aliases": ["al ghashiyah", "al ghasiyah", "al-ghashiyah", "ghashiyah", "ghasiyah"]},
    {"no": 89,  "title": "Al Fajr",      "aliases": ["al fajr", "al-fajr", "fajr"]},
    {"no": 90,  "title": "Al Balad",     "aliases": ["al balad", "al-balad", "balad"]},
    {"no": 91,  "title": "Ash Shams",    "aliases": ["ash shams", "as syams", "asy syams", "ash-shams", "syams", "shams"]},
    {"no": 92,  "title": "Al Layl",      "aliases": ["al lail", "al layl", "al-lail", "lail", "layl"]},
    {"no": 93,  "title": "Ad Duha",      "aliases": ["ad dhuha", "ad duha", "ad-duha", "duha", "dhuha"]},
    {"no": 94,  "title": "Ash Sharh",    "aliases": ["ash sharh", "al insyirah", "al inshirah", "ash-sharh", "insyirah", "inshirah"]},
    {"no": 95,  "title": "At Tin",       "aliases": ["at tin", "attin"]},
    {"no": 96,  "title": "Al 'Alaq",     "aliases": ["al alaq", "al-'alaq", "al 'alaq", "alaq"]},
    {"no": 97,  "title": "Al Qadr",      "aliases": ["al qadr", "al-qadr", "qadr"]},
    {"no": 98,  "title": "Al Bayyinah",  "aliases": ["al bayyinah", "al bayyinna", "al-bayyinah", "bayyinah", "bayyinna"]},
    {"no": 99,  "title": "Az Zalzalah",  "aliases": ["az zalzalah", "al zalzala", "az-zalzalah", "zalzalah", "zalzala"]},
    {"no": 100, "title": "Al 'Adiyat",   "aliases": ["al adiyat", "al 'adiyat", "al-adiyat", "adiyat"]},
    {"no": 101, "title": "Al Qari'ah",   "aliases": ["al qari'ah", "al qariah", "al-qari'ah", "qari'ah", "qariah"]},
    {"no": 102, "title": "At Takathur",  "aliases": ["at takathur", "at-takathur", "takathur"]},
    {"no": 103, "title": "Al 'Asr",      "aliases": ["al asr", "al 'asr", "al-asr", "asr"]},
    {"no": 104, "title": "Al Humazah",   "aliases": ["al humazah", "al-humazah", "humazah"]},
    {"no": 105, "title": "Al Fil",       "aliases": ["al fil", "al fill", "al-fil", "fil", "fill"]},
    {"no": 106, "title": "Quraysh",      "aliases": ["quraysh", "quraish", "al quraish", "al quraysh", "quraisy"]},
    {"no": 107, "title": "Al Ma'un",     "aliases": ["al maun", "al ma'un", "al-ma'un", "maun"]},
    {"no": 108, "title": "Al Kawthar",   "aliases": ["al kawthar", "al khautsar", "al-kauthar", "kawthar", "khautsar"]},
    {"no": 109, "title": "Al Kafirun",   "aliases": ["al kafirun", "al-kafirun", "kafirun"]},
    {"no": 110, "title": "An Nasr",      "aliases": ["an nasr", "al nashr", "an-nasr", "nasr", "nashr"]},
    {"no": 111, "title": "Al Masad",     "aliases": ["al lahab", "al masad", "al-lahab", "lahab", "masad"]},
    {"no": 112, "title": "Al Ikhlas",    "aliases": ["al ikhlas", "al-ikhlas", "ikhlas"]},
    {"no": 113, "title": "Al Falaq",     "aliases": ["al falaq", "al-falaq", "falaq"]},
    {"no": 114, "title": "An Nas",       "aliases": ["an nas", "an-nas", "annas", "nas"]},
]

_JUZ_BY_ALIAS = {}
for _s in JUZ_AMMA:
    for _a in _s["aliases"]:
        _JUZ_BY_ALIAS[_normalize(_a)] = _s


def match_surah(title):
    """Cocokkan judul chapter (mis. 'Surah Al Burooj') ke entri kanonik Juz Amma.
    Return dict {no, title} bila cocok, selain itu None."""
    if not title:
        return None
    key = _normalize(title)
    if not key:
        return None
    return _JUZ_BY_ALIAS.get(key)


# ─── Utilitas chapter ─────────────────────────────────────────────────────────

def chapters_from_info(info):
    """Normalisasi info['chapters'] yt-dlp → [{title,start,end}]."""
    chs = info.get("chapters") or []
    out = []
    for c in chs:
        s = float(c.get("start_time") or 0)
        e = float(c.get("end_time")) if c.get("end_time") is not None else None
        out.append({"title": str(c.get("title") or "Segment").strip(), "start": s, "end": e})
    return out


def detect_missing_surahs(chapters, video_duration=None):
    """Deteksi surah Juz Amma yang 'hilang' di antara chapter berurutan.

    Alur: chapter yang judulnya cocok surah diurutkan berdasarkan nomor urut
    kemunculannya (start time). Bila dua surah berurutan secara kanonik
    melompati nomor (mis. 111 → 113), surah yang dilompati (112) tidak punya
    marker sendiri → batas awalnya ada di dalam window chapter sebelumnya.

    Return list gap: {no, title, prev_title, prev_start, next_start}
    (window trace = [prev_start, next_start]).
    """
    matched = []
    for ch in chapters:
        m = match_surah(ch["title"])
        if m:
            matched.append({**m, "start": ch["start"], "end": ch["end"], "raw_title": ch["title"]})

    gaps = []
    for i in range(len(matched) - 1):
        a, b = matched[i], matched[i + 1]
        missing = b["no"] - a["no"] - 1
        if missing <= 0:
            continue
        for step in range(1, missing + 1):
            miss_no = a["no"] + step
            entry = next((s for s in JUZ_AMMA if s["no"] == miss_no), None)
            if entry:
                gaps.append({
                    "no": entry["no"],
                    "title": f"Surah {entry['title']}",
                    "prev_title": a["raw_title"],
                    "prev_start": a["start"],
                    "next_start": b["start"],
                })
    return gaps


# ─── Gemini trace batas surah ─────────────────────────────────────────────────

def find_env_file_keys():
    """Cari GEMINI_API_KEYS dari env atau file .env.

    Urutan lookup:
      1. Env var GEMINI_API_KEYS / GEMINI_API_KEY
      2. <repo-mini-yt>/.env dan _engine/.env
      3. <sibling>/clipforge/.env (opsi (b): pakai key ClipForge yang ada)
    Return list key (atau []).
    """
    def _parse_env(text):
        keys = []
        for line in (text or "").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEYS="):
                raw = line.split("=", 1)[1].strip().strip('"').strip("'")
                keys += [k.strip() for k in raw.split(",") if k.strip()]
            elif line.startswith("GEMINI_API_KEY="):
                raw = line.split("=", 1)[1].strip().strip('"').strip("'")
                if raw:
                    keys.append(raw)
        return keys

    raw = os.environ.get("GEMINI_API_KEYS") or os.environ.get("GEMINI_API_KEY") or ""
    if raw:
        return [k.strip() for k in raw.split(",") if k.strip()]

    repo_root = ENGINE_DIR.parent  # mini-YT-Downloader/
    candidates = [
        repo_root / ".env",
        ENGINE_DIR / ".env",
        repo_root.parent / "clipforge" / ".env",  # opsi (b)
        Path.cwd() / ".env",
    ]
    seen = set()
    keys = []
    for env_path in candidates:
        try:
            if env_path.exists():
                for k in _parse_env(env_path.read_text(encoding="utf-8", errors="ignore")):
                    if k not in seen:
                        seen.add(k)
                        keys.append(k)
        except Exception:
            continue
    return keys


def _extract_window(source, win_start, win_end, out_opus):
    """Ekstrak jendela audio jadi mono opus kecil untuk dikirim ke Gemini."""
    dur = max(0.5, win_end - win_start)
    cmd = [
        resolve_ffmpeg(), "-y",
        "-ss", f"{win_start:.3f}",
        "-i", source,
        "-t", f"{dur:.3f}",
        "-vn", "-ac", "1", "-ar", "24000", "-c:a", "libopus", "-b:a", "32k",
        out_opus,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(out_opus):
        raise RuntimeError(f"gagal ekstrak window audio: {proc.stderr[-300:] if proc.stderr else '?'}")
    return out_opus


def _gemini_generate(model, key, audio_b64, mime, prompt):
    """generateContent + inline audio (pola ClipForge transcribe.js)."""
    if requests is None:
        raise RuntimeError("requests tidak terpasang")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": mime, "data": audio_b64}},
                {"text": prompt},
            ],
        }],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    resp = requests.post(url, json=body, timeout=180)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts)


def trace_missing_boundary(source, win_start, win_end, missing_title, keys, models=None):
    """Trace keberadaan + batas surah yang 'hilang' dari urutan kanonik.

    Window = [prev_start, next_start] (chapter sebelum & sesudah surah yang
    dilompati di urutan kanonik). Prompt NETRAL (tanpa asumsi surah itu ada) —
    minta Gemini mendaftar semua surah + offset awal. Pengalaman lapangan:
    prompt yang "memaksa" surah hilang ada ("setelah X qari membaca Y")
    memicu halusinasi (Al Ikhlas dilaporkan 2s/54.5s padahal tak direkam).

    Return:
      {"status": "found", "start": <abs>, "title": ...}  → surah ada + batas
      {"status": "absent", "start": None}                  → surah tak direkam
      None                                                    → error / tanpa key
    """
    if not keys:
        return None

    models = models or ["gemini-3.7-flash", "gemini-2.5-flash"]

    tmp_opus = os.path.join(os.path.dirname(source) or ".", f"_trace_{int(time.time())}.opus")
    try:
        _extract_window(source, win_start, win_end, tmp_opus)
        import base64
        with open(tmp_opus, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return None
    finally:
        # dihapus setelah request selesai (di bawah)
        pass

    prompt = (
        "Kamu menerima potongan audio murottal Al-Qur'an (bacaan berurutan).\n"
        "Identifikasi SEMUA surah yang dibaca qari dalam audio ini, lengkap "
        "dengan offset awal (detik, float, relatif dari detik 0 audio ini, "
        "tepat saat surah tersebut MULAI dibaca / basmalahnya).\n"
        "Balas HANYA JSON array: "
        "[{\"surah\": \"<nama surah>\", \"start_offset_seconds\": <float>}]"
    )

    target_no = match_surah(missing_title)
    last_err = None
    try:
        for model in models:
            for key in keys:
                try:
                    text = _gemini_generate(model, key, b64, "audio/ogg", prompt)
                    import json
                    arr = json.loads(text.strip())
                    if not isinstance(arr, list):
                        raise ValueError("response bukan array")
                    # Cari surah target di antara yang teridentifikasi
                    for item in arr:
                        name = str(item.get("surah") or "")
                        m = match_surah(name)
                        # cocok: nomor kanonik sama ATAU nama mengandung missing_title
                        if (target_no and m and m.get("no") == target_no.get("no")) or (
                            missing_title and _normalize(name) and
                            _normalize(missing_title) in _normalize(name)
                        ):
                            offset = float(item.get("start_offset_seconds") or 0)
                            abs_start = win_start + offset
                            if abs_start - win_start < 2.0 or win_end - abs_start < 2.0:
                                raise ValueError(f"offset terlalu dekat tepi: {offset}")
                            return {"status": "found", "start": abs_start}, model
                    # Tidak ditemukan di daftar → surah memang tidak direkam
                    return {"status": "absent", "start": None}, model
                except Exception as e:
                    last_err = str(e)
                    continue
    finally:
        try:
            if os.path.exists(tmp_opus):
                os.remove(tmp_opus)
        except Exception:
            pass
    return None


# ─── Potong per segmen → MP3 ──────────────────────────────────────────────────

def build_cut_segments(chapters, skip_opening=True, resolved_gaps=None, video_duration=None):
    """Bangun daftar segmen potong dari chapter + sisipan gap.

    resolved_gaps: [{start, end, title}] hasil trace Gemini (sudah absolut).
    video_duration: bila ada, batas akhir segmen terakhir dipaksa >= durasi video
                    (hindari audio yang terpotong bila end chapter terakhir < durasi).
    Return [{title, start, end}], urut by start, tanpa chapter duplikat.
    """
    segs = []
    for ch in chapters:
        title = ch["title"].strip()
        if skip_opening and title.lower().startswith("opening"):
            continue
        if ch["end"] is None:
            continue  # end harus diketahui
        segs.append({"title": title, "start": float(ch["start"]), "end": float(ch["end"])})

    # Sisip gap hasil trace: potong chapter lama yang menaungi gap
    for g in resolved_gaps or []:
        segs.append({"title": g["title"], "start": float(g["start"]), "end": float(g["end"])})

    segs.sort(key=lambda s: s["start"])
    # Rapikan: potong overlap antar segmen berurutan (ujung > awal berikutnya)
    cleaned = []
    for s in segs:
        if cleaned and s["start"] < cleaned[-1]["end"]:
            cleaned[-1]["end"] = s["start"]
        if s["end"] - s["start"] >= 1.0:
            cleaned.append(s)
    # Explisit: segmen terakhir sebaiknya menutup sampai durasi video sebenarnya
    if video_duration and cleaned and cleaned[-1]["end"] < video_duration:
        cleaned[-1]["end"] = video_duration
    return cleaned


def cut_audio_segments(source, segments, out_dir, bitrate=320, artist="", on_progress=None):
    """Potong source (audio mentah) per segmen → MP3 di out_dir.

    ffmpeg pattern ClipForge: `-ss <start> -i src -t <dur> -vn -c:a libmp3lame`.
    Return list path file output.
    """
    os.makedirs(out_dir, exist_ok=True)
    ffmpeg = resolve_ffmpeg()
    outputs = []
    for i, seg in enumerate(segments, 1):
        dur = seg["end"] - seg["start"]
        if dur < 1.0:
            continue
        safe_title = sanitize_filename(seg["title"])
        out_path = os.path.join(out_dir, f"{i:02d} - {safe_title}.mp3")
        cmd = [
            ffmpeg, "-y",
            "-ss", f"{seg['start']:.3f}",
            "-i", source,
            "-t", f"{dur:.3f}",
            "-vn",
            "-c:a", "libmp3lame", "-b:a", f"{bitrate}k",
            "-id3v2_version", "3",
        ]
        if artist:
            cmd += ["-metadata", f"artist={artist}"]
        cmd += ["-metadata", f"title={seg['title']}"]
        cmd += ["-write_id3v1", "1", out_path]

        if on_progress:
            on_progress(i, len(segments), seg["title"], dur)
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"ffmpeg gagal segmen '{seg['title']}': {proc.stderr[-300:] if proc.stderr else '?'}"
            )
        outputs.append(out_path)
    return outputs
