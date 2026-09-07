"""
updater.py — Cek update via GitHub Releases + self-update (Windows installer).

- Sumber kebenaran: GitHub Releases (tag_name = versi, body = changelog).
- Cek dibatasi maks 1x per 24 jam (disimpan di config `last_update_check`).
- Self-update: jalankan installer resmi secara detached (background), lalu
  aplikasi keluar; user menjalankan `miniyt` lagi setelah 1-2 menit.
"""

import os
import subprocess
import time

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

GITHUB_REPO = "ieproject-app/mini-YT-Downloader"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=30"
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
INSTALLER_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/install.ps1"
CHECK_INTERVAL = 24 * 3600  # detik

_CREATE_NO_WINDOW = 0x08000000  # Windows: proses background tanpa jendela


def _parse_ver(version):
    """'v1.4.2' -> (1, 4, 2). Bagian non-numerik diabaikan."""
    parts = []
    for p in str(version or "").strip().lstrip("vV").split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    return tuple(parts) or (0,)


def is_newer(latest, current):
    try:
        return _parse_ver(latest) > _parse_ver(current)
    except Exception:
        return False


def fetch_latest_release(timeout=10):
    """Ambil release terbaru dari GitHub. Return dict atau None bila gagal."""
    if requests is None:
        return None
    try:
        resp = requests.get(
            RELEASES_API,
            timeout=timeout,
            headers={"Accept": "application/vnd.github+json"},
        )
        if resp.status_code != 200:
            return None
        releases = resp.json()
        if not isinstance(releases, list):
            return None
        # Pilih versi semver TERTINGGI (bukan 'latest' GitHub yang berdasar
        # tanggal pembuatan release — salah bila rilis lama di-backfill).
        best = None
        for data in releases:
            if not isinstance(data, dict):
                continue
            tag = (data.get("tag_name") or "").strip()
            if not tag:
                continue
            ver = _parse_ver(tag.lstrip("vV"))
            if best is None or ver > best[0]:
                best = (ver, tag, data)
        if best is None:
            return None
        _, tag, data = best
        return {
            "tag": tag,
            "version": tag.lstrip("vV"),
            "notes": (data.get("body") or "").strip(),
            "url": data.get("html_url") or RELEASES_URL,
        }
    except Exception:
        return None


def should_check(cfg, force=False):
    """Cek bila dipaksa, atau bila belum pernah cek dalam 24 jam terakhir."""
    if force:
        return True
    if not cfg.get("check_updates", True):
        return False
    last = float(cfg.get("last_update_check", 0) or 0)
    return (time.time() - last) >= CHECK_INTERVAL


def mark_checked(cfg):
    cfg.set("last_update_check", time.time())


def spawn_installer_update():
    """Jalankan installer resmi terbaru secara detached (Windows).

    App harus keluar setelah memanggil ini (file lama digantikan installer).
    Strategi: tulis updater.ps1 ke data dir (hindari nested-quoting cmd),
    lalu spawn powershell -File secara detached.
    """
    if os.name != "nt":
        return False
    data_dir = paths.data_dir()
    updater_ps1 = data_dir / "updater.ps1"
    updater_ps1.write_text(
        "$env:MINIYT_SKIP_LAUNCH = '1'\n"
        f"$src = '{INSTALLER_URL}'\n"
        "$tmp = Join-Path $env:TEMP 'miniyt-install.ps1'\n"
        "Invoke-WebRequest -Uri $src -OutFile $tmp -UseBasicParsing\n"
        "& $tmp\n",
        encoding="utf-8",
    )
    subprocess.Popen(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(updater_ps1),
        ],
        creationflags=_CREATE_NO_WINDOW,
        close_fds=True,
    )
    return True
