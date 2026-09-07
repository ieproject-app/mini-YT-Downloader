import os
import sys

# Force UTF-8 stream output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import time
import webbrowser
from pathlib import Path

import re

# Add engine src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# i18n must be initialized BEFORE preflight (preflight prints localized text)
import paths
import i18n
i18n.init(paths.config_path())

# Run preflight check before imports to ensure dependencies & ffmpeg
from preflight import ensure_dependencies, is_ffmpeg_available
ensure_dependencies()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.prompt import Prompt, Confirm

from config_manager import ConfigManager
from downloader import YTDownloader, sanitize_youtube_url, detect_playlist, is_channel_url, normalize_media_url, is_supported_youtube_url
from splitter import (
    build_cut_segments,
    chapters_from_info,
    cut_audio_segments,
    detect_missing_surahs,
    find_env_file_keys,
    gemini_key_status,
    save_gemini_keys_to_env,
    sweep_surah_starts,
    trace_missing_boundary,
    transcribe_surah_timeline,
)
from i18n import t

console = Console(force_terminal=True, legacy_windows=False)
cfg = ConfigManager()
i18n.set_language(cfg.get("language", "auto"))

APP_VERSION = "1.3.0"

# ── Tautan onboarding Gemini API key ──
AISTUDIO_APIKEY_URL = "https://aistudio.google.com/apikey"
# TODO(blog): ganti URL di bawah dengan artikel tutorial lengkap setelah dipublikasikan
TUTORIAL_API_KEY_URL = "https://snipgeek.com/"


def prompt_install_gemini_key(title=None):
    """Tawaran inline memasang Gemini API key (dipakai di onboarding & konteks).

    Return True bila key berhasil disimpan.
    """
    console.print(f"\n[bold magenta]🔑 {title or t('settings.m6')}[/bold magenta]")
    console.print(t("key.guide_line", url=TUTORIAL_API_KEY_URL))
    console.print(t("key.free_line", url=AISTUDIO_APIKEY_URL))
    if not Confirm.ask(t("key.ask_paste"), default=False):
        return False
    keys_text = Prompt.ask(t("key.paste_prompt"))
    if not keys_text.strip():
        console.print(t("key.cancelled"))
        return False
    if save_gemini_keys_to_env(keys_text):
        console.print(t("key.saved"))
        return True
    console.print(t("key.save_failed"))
    return False

_MUROTTAL_RE = re.compile(r"murottal|juz\s*30|juz\s*amma|juz30|tilawah|qari|recit|al-?qur'?an", re.IGNORECASE)


def looks_like_murottal(*texts):
    """Heuristik: judul/channel/deskripsi mengarah ke video murottal Juz."""
    return any(_MUROTTAL_RE.search(str(x) or "") for x in texts)


def format_options():
    """Daftar format dengan label sesuai bahasa aktif (dibangun saat dipanggil)."""
    return [
        ("1", "1080p", t("fmt.1080p"), "video"),
        ("2", "720p", t("fmt.720p"), "video"),
        ("3", "2160p", t("fmt.2160p"), "video"),
        ("4", "best", t("fmt.best"), "video"),
        ("5", "480p", t("fmt.480p"), "video"),
        ("6", "mp3_320", t("fmt.mp3_320"), "audio"),
        ("7", "mp3_192", t("fmt.mp3_192"), "audio"),
        ("8", "m4a", t("fmt.m4a"), "audio"),
        ("9", "flac", t("fmt.flac"), "audio"),
        ("10", "wav", t("fmt.wav"), "audio"),
    ]


def resolution_labels():
    return {code: f"[{cat.upper()}] {label}" for _, code, label, cat in format_options()}


def choose_folder_gui(current_folder):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        selected_folder = filedialog.askdirectory(
            initialdir=current_folder,
            title=t("common.choose_folder_title")
        )
        root.destroy()
        if selected_folder:
            return selected_folder
    except Exception as e:
        console.print(t("common.gui_warning", err=e))
    return current_folder

def format_duration(seconds):
    if not seconds:
        return t("common.na")
    mins, secs = divmod(int(seconds), 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def render_header():
    header_text = (f"[bold cyan]{t('header.title')}[/bold cyan]\n"
                   f"[dim white]{t('header.subtitle')}[/dim white]\n\n"
                   f"[bold yellow]{t('header.credit')}[/bold yellow]")
    console.print(Panel(header_text, border_style="cyan", box=box.ASCII, expand=False))

BROWSER_CHOICES = ["chrome", "edge", "firefox", "brave", "vivaldi", "opera", "safari", ""]

def render_status_bar():
    curr_dir = cfg.get_root_download_dir()
    curr_res = cfg.get("last_resolution", "1080p")
    label_res = resolution_labels().get(curr_res, curr_res)
    total_dl = cfg.get("download_count", 0)
    ffmpeg_stat = t("status.ffmpeg_ready") if is_ffmpeg_available() else t("status.ffmpeg_missing")
    cb = (cfg.get("cookies_browser", "") or "").strip()
    cookies_stat = f"[bold green]{cb}[/bold green]" if cb else t("status.cookies_off")

    table = Table(show_header=False, box=box.ASCII, expand=False)
    table.add_row(f"[bold magenta]{t('status.downloads_folder')}[/bold magenta]", f"[underline]{curr_dir}[/underline] {t('status.auto_split')}")
    table.add_row(f"[bold green]{t('status.default_format')}[/bold green]", f"[bold]{label_res}[/bold]")
    table.add_row(f"[bold blue]{t('status.engine_ffmpeg')}[/bold blue]", ffmpeg_stat)
    table.add_row(f"[bold cyan]{t('status.cookies_browser')}[/bold cyan]", cookies_stat)
    table.add_row(f"[bold yellow]{t('status.total_downloads')}[/bold yellow]", t("status.total_saved", n=total_dl))
    table.add_row(f"[bold white]{t('status.gemini_key')}[/bold white]", gemini_key_status())
    console.print(table)

    console.print(t("status.shortcuts"))

def settings_menu(downloader):
    while True:
        render_header()
        console.print(Panel(t("settings.title"), border_style="yellow", box=box.ASCII))
        console.print(t("settings.folder_main", dir=cfg.get_root_download_dir()))
        console.print(t("settings.default_format", label=resolution_labels().get(cfg.get('last_resolution', '1080p'))))

        console.print(t("settings.m1"))
        console.print(t("settings.m2"))
        console.print(t("settings.m3"))
        console.print(t("settings.m4"))
        console.print(t("settings.m5"))
        console.print(t("settings.m6"))
        console.print(t("settings.m7"))
        console.print(t("settings.m0"))

        console.print(f"{t('status.gemini_key')} {gemini_key_status()}")
        console.print(t("settings.key_note"))

        opt = Prompt.ask(t("settings.prompt"), choices=["1", "2", "3", "4", "5", "6", "7", "0"], default="0")

        if opt == "0":
            break
        elif opt == "1":
            old_dir = cfg.get_root_download_dir()
            new_dir = choose_folder_gui(old_dir)
            if new_dir and new_dir != old_dir:
                cfg.set_root_download_dir(new_dir)
                console.print(t("settings.folder_changed", dir=new_dir))
                time.sleep(1)
        elif opt == "2":
            cfg.open_download_folder()
            console.print(t("main.folder_opened"))
            time.sleep(1)
        elif opt == "3":
            render_format_menu()
            fmt_opts = format_options()
            chosen_res = Prompt.ask(t("format.prompt"), choices=[str(i) for i in range(1, len(fmt_opts)+1)], default="1")
            for num, code, label, _ in fmt_opts:
                if num == chosen_res:
                    cfg.set("last_resolution", code)
                    console.print(t("settings.format_set", label=label))
                    time.sleep(1)
                    break
        elif opt == "4":
            webbrowser.open("https://snipgeek.com/")
            console.print(t("main.opening_site"))
            time.sleep(1)
        elif opt == "5":
            current = cfg.get("cookies_browser", "") or t("status.cookies_off").replace("[dim]", "").replace("[/dim]", "")
            console.print(t("settings.cookies.current", current=current))
            console.print(t("settings.cookies.prompt1"))
            console.print(t("settings.cookies.prompt2"))
            console.print(t("settings.cookies.note"))
            for i, b in enumerate(BROWSER_CHOICES[:-1], 1):
                console.print(f"[bold cyan][{i}][/bold cyan] {b}")
            console.print(t("settings.cookies.disable"))
            pilihan = Prompt.ask(t("settings.cookies.choose"), choices=[str(i) for i in range(len(BROWSER_CHOICES))], default="0")
            chosen = BROWSER_CHOICES[int(pilihan)]
            cfg.set("cookies_browser", chosen)
            if chosen:
                console.print(t("settings.cookies.enabled", browser=chosen))
            else:
                console.print(t("settings.cookies.disabled"))
            time.sleep(1)
        elif opt == "6":
            console.print(f"\n{t('status.gemini_key')} {gemini_key_status()}")
            console.print(t("settings.gemini.sub1"))
            console.print(t("settings.gemini.sub2", url=AISTUDIO_APIKEY_URL))
            console.print(t("settings.gemini.sub3", url=TUTORIAL_API_KEY_URL))
            console.print(t("settings.gemini.cancel"))
            sub = Prompt.ask(t("settings.gemini.choose"), choices=["1", "2", "3", "0"], default="0")
            if sub == "1":
                keys_text = Prompt.ask(t("settings.gemini.paste_prompt"))
                if not keys_text.strip():
                    console.print(t("key.cancelled"))
                elif save_gemini_keys_to_env(keys_text):
                    console.print(t("key.saved"))
                    console.print(t("key.ready"))
                else:
                    console.print(t("key.save_failed"))
            elif sub == "2":
                webbrowser.open(AISTUDIO_APIKEY_URL)
            elif sub == "3":
                webbrowser.open(TUTORIAL_API_KEY_URL)
            time.sleep(1)
        elif opt == "7":
            ask_language(allow_reask=True)


def render_format_menu():
    table = Table(title=t("format.menu_title"), box=box.ASCII, expand=False)
    table.add_column(t("format.col_no"), style="bold cyan", justify="center")
    table.add_column(t("format.col_cat"), style="bold magenta")
    table.add_column(t("format.col_quality"), style="white")

    for num, code, label, cat in format_options():
        table.add_row(num, cat.upper(), label)
    console.print(table)

def select_format_interactive(last_res):
    render_format_menu()
    last_label = resolution_labels().get(last_res, last_res)
    console.print(t("format.use_last", label=last_label))
    console.print(t("format.cancel"))

    choice = Prompt.ask(t("format.prompt"), default="")

    if choice.lower() == "b":
        return None
    if choice == "":
        return last_res

    for num, code, _, _ in format_options():
        if num == choice:
            return code
    return last_res

def ask_language(allow_reask=False):
    """Pertanyaan pilih bahasa (first-run) — return bahasa terpilih."""
    console.print(t("lang.question_title"))
    console.print(t("lang.opt_id"))
    console.print(t("lang.opt_en"))
    default = "1" if i18n.get_language() == "id" else "2"
    choice = Prompt.ask(t("lang.prompt"), choices=["1", "2"], default=default)
    lang = "id" if choice == "1" else "en"
    i18n.set_language(lang)
    cfg.set("language", lang)
    console.print(t("lang.set_done", lang="Bahasa Indonesia" if lang == "id" else "English"))
    return lang

def check_snipgeek_milestone(current_count):
    if current_count == 5 or (current_count > 5 and current_count % 10 == 0):
        console.print()
        appreciation = Panel(
            t("milestone.body", n=current_count),
            title=t("milestone.title"),
            border_style="yellow",
            box=box.ASCII
        )
        console.print(appreciation)
        open_web = Confirm.ask(t("milestone.open_prompt"), default=True)
        if open_web:
            webbrowser.open("https://snipgeek.com/")
            console.print(t("milestone.opened"))
            time.sleep(1)

def main():
    downloader = YTDownloader(config_manager=cfg, ffmpeg_dir=str(paths.bin_dir()) if (paths.bin_dir() / 'ffmpeg.exe').exists() else None)

    # First-run: pilih bahasa (sekali saja)
    if cfg.get("language", "auto") == "auto" and not cfg.get("language_prompted", False):
        ask_language()
        cfg.set("language_prompted", True)

    # Onboarding Gemini key — tawarkan sekali saja selama belum ada key tersimpan
    if not find_env_file_keys() and not cfg.get("gemini_key_prompted", False):
        console.print(t("onboard.tip"))
        prompt_install_gemini_key(t("onboard.title"))
        cfg.set("gemini_key_prompted", True)

    while True:
        render_header()
        render_status_bar()

        input_url = Prompt.ask(t("main.url_prompt")).strip()

        if not input_url:
            continue

        cmd = input_url.lower()
        if cmd == 'q':
            console.print(t("main.bye"))
            break
        elif cmd == 's':
            settings_menu(downloader)
            continue
        elif cmd == 'o':
            cfg.open_download_folder()
            console.print(t("main.folder_opened"))
            time.sleep(1)
            continue
        elif cmd == 'w':
            webbrowser.open("https://snipgeek.com/")
            console.print(t("main.opening_site"))
            time.sleep(1)
            continue
        elif cmd == 'k':
            webbrowser.open(AISTUDIO_APIKEY_URL)
            console.print(t("main.k_opened"))
            console.print(t("main.k_hint"))
            time.sleep(1)
            continue
        else:
            input_url = normalize_media_url(input_url)

        # ---------- Validasi host: hanya YouTube yang didukung ----------
        if not is_supported_youtube_url(input_url):
            console.print(t("main.bad_url.title"))
            console.print(t("main.bad_url.examples"))
            console.print("  [dim]https://www.youtube.com/watch?v=XXXXXXXXXXX[/dim]")
            console.print("  [dim]https://youtu.be/XXXXXXXXXXX[/dim]")
            low = input_url.lower()
            if "aistudio.google.com" in low or "accounts.google.com" in low or "ai.google.dev" in low:
                console.print(t("main.bad_url.ai_hint1"))
                console.print(t("main.bad_url.ai_hint2"))
                console.print(t("main.bad_url.ai_hint3"))
            Prompt.ask(t("main.press_enter"))
            continue

        # ---------- Deteksi Playlist ----------
        if is_channel_url(input_url):
            console.print(t("main.channel_link.title"))
            console.print(t("main.channel_link.hint"))
            Prompt.ask(t("main.press_enter"))
            continue

        detected = detect_playlist(input_url)
        want_playlist = False
        playlist_url = None

        if detected["kind"] == "playlist_only":
            want_playlist = True
            playlist_url = detected["playlist_url"]
        elif detected["kind"] == "both":
            console.print(t("main.in_playlist.title"))
            console.print(t("main.in_playlist.opt1"))
            console.print(t("main.in_playlist.opt2"))
            scope = Prompt.ask(t("main.in_playlist.prompt"), choices=["1", "2"], default="1")
            if scope == "2":
                want_playlist = True
                playlist_url = detected["playlist_url"]
            else:
                input_url = detected["video_url"]

        target_saved_folder = None

        if want_playlist:
            with console.status(t("main.fetching_playlist"), spinner="dots"):
                try:
                    pl_title, entries = downloader.get_playlist_info(playlist_url)
                except Exception as e:
                    console.print(t("main.playlist_failed_fetch", err=e))
                    Prompt.ask(t("main.press_enter"))
                    continue

            if not entries:
                console.print(t("main.playlist_empty"))
                Prompt.ask(t("main.press_enter"))
                continue

            n_items = len(entries)
            pl_table = Table(title=t("info.playlist_table"), box=box.ASCII, expand=False)
            pl_table.add_column(t("info.col_field"), style="bold cyan")
            pl_table.add_column(t("info.col_value"), style="white")
            pl_table.add_row(t("info.playlist_title"), pl_title)
            pl_table.add_row(t("info.playlist_items"), str(n_items))
            for idx, entry in enumerate(entries[:5], 1):
                pl_table.add_row(t("info.preview", idx=idx), str(entry.get('title') or entry.get('id') or '-')[:70])
            if n_items > 5:
                pl_table.add_row("...", t("info.more_items", n=n_items - 5))
            console.print()
            console.print(pl_table)
            console.print()

            last_res = cfg.get("last_resolution", "1080p")
            res_choice = select_format_interactive(last_res)

            if not res_choice:
                continue

            cfg.set("last_resolution", res_choice)

            if n_items > 20:
                if not Confirm.ask(t("info.confirm_big_playlist", n=n_items), default=True):
                    continue

            console.print(t("main.starting_playlist", n=n_items, res=res_choice))
            success_files, failed = [], []
            try:
                success_files, failed, target_saved_folder = downloader.download_playlist(
                    playlist_url, res_choice, entries, playlist_title=pl_title
                )
            except KeyboardInterrupt:
                console.print(t("main.playlist_stopped"))
            except Exception as e:
                console.print(t("main.playlist_failed", err=e))

            for _ in success_files:
                cfg.increment_download_count()

            console.print()
            if success_files:
                console.print(t("main.done_line", ok=len(success_files), n=n_items, folder=target_saved_folder))
            if failed:
                console.print(t("main.failed_line", n=len(failed)))
                for f_title, f_err in failed[:10]:
                    console.print(f"  [dim]- {f_title} ({f_err})[/dim]")
                if len(failed) > 10:
                    console.print(t("main.failed_more", n=len(failed) - 10))
            if not success_files and not failed:
                console.print(t("main.none_downloaded"))

            if success_files:
                check_snipgeek_milestone(cfg.get("download_count", 0))

        else:
            # Fetch Video Info
            with console.status(t("main.fetching_info"), spinner="dots"):
                try:
                    info, clean_url = downloader.get_video_info(input_url)
                except Exception as e:
                    console.print(t("main.metadata_failed", err=e))
                    Prompt.ask(t("main.press_enter"))
                    continue

            # Display Media Info Card
            title = info.get('title', 'Unknown Title')
            channel = info.get('uploader') or info.get('channel', 'Unknown Channel')
            duration = format_duration(info.get('duration'))
            views = f"{info.get('view_count', 0):,}" if info.get('view_count') else t("common.na")

            info_table = Table(title=t("info.media_table"), box=box.ASCII, expand=False)
            info_table.add_column(t("info.col_field"), style="bold cyan")
            info_table.add_column(t("info.col_value"), style="white")
            info_table.add_row(t("info.lbl_title"), title)
            info_table.add_row(t("info.lbl_channel"), channel)
            info_table.add_row(t("info.lbl_duration"), duration)
            info_table.add_row(t("info.lbl_views"), views)
            console.print()
            console.print(info_table)
            console.print()

            # ── ✂️ Opsi: potong per chapter/surah jadi MP3 ────────────────────
            chapters = chapters_from_info(info)
            do_split = False
            auto_detect_surah = False
            if chapters and len(chapters) > 1:
                n_ch = len(chapters)
                console.print(t("split.has_chapters", n=n_ch))
                do_split = Confirm.ask(t("split.split_prompt"), default=False)
            elif not chapters and cfg.get("gemini_trace", True) and looks_like_murottal(title, channel):
                # Video tanpa chapter (mis. murottal Juz 30 tanpa timestamp di
                # deskripsi) → deteksi semua surah via Gemini dari audio.
                # Bila key belum terpasang → tawaran inline pasang key dulu.
                console.print(t("split.murottal_detected"))
                if not find_env_file_keys():
                    console.print(t("split.needs_key"))
                    if prompt_install_gemini_key(t("key.verify_needed")):
                        do_split = Confirm.ask(t("split.key_installed_ask"), default=False)
                        auto_detect_surah = do_split
                else:
                    do_split = Confirm.ask(t("split.auto_detect_prompt"), default=False)
                    auto_detect_surah = do_split

            if do_split:
                # Alur potong: unduh audio mentah sekali → (bila perlu) deteksi
                # surah dari audio → deteksi gap → potong tiap segmen → MP3.
                bitrate = int(cfg.get("cut_bitrate", 320) or 320)
                skip_opening = bool(cfg.get("skip_opening", True))
                sub = downloader.sanitize_title(title)

                with console.status(t("split.downloading_source"), spinner="dots"):
                    try:
                        src_file, _, src_dir = downloader.download_audio_raw(
                            clean_url, title=title, video_id=info.get('id'), subfolder=sub)
                    except Exception as e:
                        console.print(t("split.source_failed", err=e))
                        continue
                target_saved_folder = src_dir
                console.print(t("split.source_line", name=os.path.basename(src_file)))

                # Mode auto-detect: video tanpa chapter → transkripsi word-level
                # (presisi) lalu petakan ke surah; fallback: sweep audio per-chunk.
                if auto_detect_surah:
                    dur = int(info.get("duration") or 0)
                    keys = find_env_file_keys()
                    console.print(t("split.analyzing", dur=format_duration(dur)))
                    timeline = transcribe_surah_timeline(src_file, keys, dur)
                    if len(timeline) < 2:
                        console.print(t("split.transcription_weak"))
                        timeline = sweep_surah_starts(src_file, keys, dur)
                    if len(timeline) < 2:
                        console.print(t("split.detect_failed"))
                        try:
                            os.remove(src_file)
                        except Exception:
                            pass
                        continue
                    # Susun chapters sintetis dari timeline (end = start surah berikutnya)
                    chapters = []
                    for i, tm in enumerate(timeline):
                        end = timeline[i + 1]["start"] if i + 1 < len(timeline) else dur
                        chapters.append({"title": tm["title"], "start": tm["start"], "end": end})
                    skip_opening = False  # tidak ada chapter Opening sintetis
                    names = ", ".join(c["title"] for c in chapters[:5])
                    console.print(t("split.detected_count", n=len(chapters), names=names,
                                    more='…' if len(chapters) > 5 else ''))

                # Deteksi surah Juz Amma yang tidak punya timestamp (gap)
                resolved_gaps = []
                if cfg.get("gemini_trace", True):
                    gaps = detect_missing_surahs(chapters)
                    if gaps:
                        console.print(t("split.gaps", n=len(gaps)))
                        keys = find_env_file_keys()
                        if not keys:
                            # Tawaran inline: pasang key di tempat agar verifikasi tetap jalan
                            if prompt_install_gemini_key(t("key.verify_needed")):
                                keys = find_env_file_keys()
                        for gap in gaps:
                            console.print(t("split.gap_check", title=gap['title'],
                                            t1=format_duration(int(gap['prev_start'])),
                                            t2=format_duration(int(gap['next_start']))))
                            if not keys:
                                console.print(t("split.gap_no_key"))
                                continue
                            result, model = trace_missing_boundary(
                                src_file, gap['prev_start'], gap['next_start'], gap['title'], keys)
                            if result and result.get("status") == "found":
                                abs_start = result["start"]
                                resolved_gaps.append({
                                    "title": gap['title'],
                                    "start": abs_start,
                                    "end": gap['next_start'],
                                })
                                console.print(t("split.gap_found", title=gap['title'],
                                                t=format_duration(int(abs_start)), model=model))
                            elif result and result.get("status") == "absent":
                                console.print(t("split.gap_absent", title=gap['title'], model=model))
                            else:
                                console.print(t("split.gap_failed", model=model if model else '?'))

                segments = build_cut_segments(chapters, skip_opening=skip_opening, resolved_gaps=resolved_gaps, video_duration=info.get('duration'))
                if not segments:
                    console.print(t("split.no_segments"))
                    continue

                console.print(t("split.cutting", n=len(segments), bitrate=bitrate))

                def _split_progress(i, total, seg_title, dur):
                    console.print(f"  [cyan][{i:02d}/{total}][/cyan] {seg_title} [dim]({format_duration(int(dur))})[/dim]")

                try:
                    outputs = cut_audio_segments(
                        src_file, segments, src_dir,
                        bitrate=bitrate, artist=channel or "",
                        on_progress=_split_progress,
                    )
                except Exception as e:
                    console.print(t("split.cut_failed", err=e))
                    continue

                # Bersihkan file sumber mentah (user hanya mau file per-surah)
                try:
                    os.remove(src_file)
                except Exception:
                    pass

                new_count = 0
                for _ in outputs:
                    new_count = cfg.increment_download_count()
                console.print(t("split.done", n=len(outputs), folder=src_dir))
                console.print(t("main.total_saved", n=new_count))
                check_snipgeek_milestone(new_count)
            else:
                last_res = cfg.get("last_resolution", "1080p")
                res_choice = select_format_interactive(last_res)

                if not res_choice:
                    continue

                cfg.set("last_resolution", res_choice)

                console.print(t("main.starting_download"))
                try:
                    out_file, target_saved_folder = downloader.download_with_fallback(
                        clean_url,
                        format_type=res_choice,
                        title=info.get('title', ''),
                        video_id=info.get('id'),
                    )
                    new_count = cfg.increment_download_count()
                    console.print(t("main.saved_ok", file=out_file))
                    console.print(t("main.total_saved", n=new_count))

                    check_snipgeek_milestone(new_count)

                except Exception as e:
                    console.print(t("main.download_failed", err=e))

        console.print(t("main.next1"))
        console.print(t("main.next2"))
        console.print(t("main.next3"))
        console.print(t("main.next4"))
        console.print(t("main.next5"))
        console.print(t("main.next0"))

        next_action = Prompt.ask(t("main.next_prompt"), choices=["1", "2", "3", "4", "5", "0"], default="1")

        if next_action == "0":
            console.print(t("main.bye"))
            break
        elif next_action == "2":
            cfg.open_download_folder(target_saved_folder)
        elif next_action == "3":
            cfg.open_download_folder()
        elif next_action == "4":
            settings_menu(downloader)
        elif next_action == "5":
            webbrowser.open("https://snipgeek.com/")
            console.print(t("main.opening_site"))
            time.sleep(1)

if __name__ == "__main__":
    try:
        if "--version" in sys.argv:
            print(f"MiniYT v{APP_VERSION}")
            sys.exit(0)
        main()
    except KeyboardInterrupt:
        console.print(t("common.kb_interrupt"))
        sys.exit(0)
