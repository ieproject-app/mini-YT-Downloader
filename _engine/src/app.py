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

# Run preflight check before imports to ensure dependencies & ffmpeg
from preflight import ensure_dependencies, BIN_DIR, is_ffmpeg_available
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

console = Console(force_terminal=True, legacy_windows=False)
cfg = ConfigManager()

# ── Tautan onboarding Gemini API key ──
AISTUDIO_APIKEY_URL = "https://aistudio.google.com/apikey"
# TODO(blog): ganti URL di bawah dengan artikel tutorial lengkap setelah dipublikasikan
TUTORIAL_API_KEY_URL = "https://snipgeek.com/"


def prompt_install_gemini_key(title="Pasang Gemini API Key"):
    """Tawaran inline memasang Gemini API key (dipakai di onboarding & konteks).

    Return True bila key berhasil disimpan.
    """
    console.print(f"\n[bold magenta]🔑 {title}[/bold magenta]")
    console.print(f"Panduan lengkap: [underline]{TUTORIAL_API_KEY_URL}[/underline]")
    console.print(f"[dim]Key gratis: buka [underline]{AISTUDIO_APIKEY_URL}[/underline] → login Google → Create API key → Copy.[/dim]")
    if not Confirm.ask("Masukkan / paste API key sekarang?", default=False):
        return False
    keys_text = Prompt.ask("Paste Gemini API Key (beberapa key dipisah koma)")
    if not keys_text.strip():
        console.print("[yellow]Dibatalkan; key tidak diubah.[/yellow]")
        return False
    if save_gemini_keys_to_env(keys_text):
        console.print("[bold green]✓ Gemini API Key tersimpan di .env (lokal, tidak ikut git).[/bold green]")
        return True
    console.print("[bold red]✗ Gagal menyimpan key. Cek izin tulis folder project.[/bold red]")
    return False

_MUROTTAL_RE = re.compile(r"murottal|juz\s*30|juz\s*amma|juz30|tilawah|qari|recit|al-?qur'?an", re.I)


def looks_like_murottal(*texts):
    """Heuristik: judul/channel/deskripsi mengarah ke video murottal Juz."""
    return any(_MUROTTAL_RE.search(str(t) or "") for t in texts)

FORMAT_OPTIONS = [
    ("1", "1080p", "1080p Full HD (MP4 - Rekomendasi)", "video"),
    ("2", "720p", "720p HD (MP4 - Ringan & Cepat)", "video"),
    ("3", "2160p", "4K Ultra HD (2160p - MP4)", "video"),
    ("4", "best", "Best Video (Kualitas Maksimal Otomatis)", "video"),
    ("5", "480p", "480p SD (MP4)", "video"),
    ("6", "mp3_320", "MP3 320 kbps (Ultra HQ + Cover Art + ID3)", "audio"),
    ("7", "mp3_192", "MP3 192 kbps (Standard HQ + Cover Art)", "audio"),
    ("8", "m4a", "M4A / AAC (Original Audio Stream + Cover)", "audio"),
    ("9", "flac", "FLAC (Lossless Master Audio)", "audio"),
    ("10", "wav", "WAV (Uncompressed PCM Studio)", "audio")
]

RESOLUTION_LABELS = {code: f"[{cat.upper()}] {label}" for _, code, label, cat in FORMAT_OPTIONS}

def choose_folder_gui(current_folder):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        selected_folder = filedialog.askdirectory(
            initialdir=current_folder,
            title="Pilih Folder Utama Penyimpanan"
        )
        root.destroy()
        if selected_folder:
            return selected_folder
    except Exception as e:
        console.print(f"[yellow]Peringatan GUI Dialog:[/yellow] {e}")
    return current_folder

def format_duration(seconds):
    if not seconds:
        return "N/A"
    mins, secs = divmod(int(seconds), 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def render_header():
    header_text = "[bold cyan]MINI YOUTUBE DOWNLOADER (v1.2)[/bold cyan]\n[dim white]Video & High-Quality Audio Downloader (MP3 320k, FLAC, M4A, 4K) • Potong per Surah/Chapter[/dim white]\n\n[bold yellow]Crafted with care by SnipGeek - https://snipgeek.com/[/bold yellow]"
    console.print(Panel(header_text, border_style="cyan", box=box.ASCII, expand=False))

BROWSER_CHOICES = ["chrome", "edge", "firefox", "brave", "vivaldi", "opera", "safari", ""]

def render_status_bar():
    curr_dir = cfg.get_root_download_dir()
    curr_res = cfg.get("last_resolution", "1080p")
    label_res = RESOLUTION_LABELS.get(curr_res, curr_res)
    total_dl = cfg.get("download_count", 0)
    ffmpeg_stat = "[bold green]Siap[/bold green]" if is_ffmpeg_available() else "[bold red]Tidak ada[/bold red]"
    cb = (cfg.get("cookies_browser", "") or "").strip()
    cookies_stat = f"[bold green]{cb}[/bold green]" if cb else "[dim]nonaktif[/dim]"

    t = Table(show_header=False, box=box.ASCII, expand=False)
    t.add_row("[bold magenta]Folder Downloads:[/bold magenta]", f"[underline]{curr_dir}[/underline] (auto-split: [cyan]video/[/cyan] & [cyan]audio/[/cyan])")
    t.add_row("[bold green]Format Default:[/bold green]", f"[bold]{label_res}[/bold]")
    t.add_row("[bold blue]Engine FFmpeg:[/bold blue]", ffmpeg_stat)
    t.add_row("[bold cyan]Cookies Browser:[/bold cyan]", cookies_stat)
    t.add_row("[bold yellow]Total Unduhan:[/bold yellow]", f"[bold]{total_dl} media tersimpan[/bold]")
    t.add_row("[bold white]Gemini API Key:[/bold white]", gemini_key_status())
    console.print(t)

    console.print("[dim]Shortcut: Ketik [bold cyan]'S'[/bold cyan] (Settings/Folder) | [bold cyan]'O'[/bold cyan] (Buka Folder) | [bold cyan]'K'[/bold cyan] (Gemini API Key) | [bold cyan]'W'[/bold cyan] (SnipGeek.com) | [bold cyan]'Q'[/bold cyan] (Keluar)[/dim]\n")

def settings_menu(downloader):
    while True:
        render_header()
        console.print(Panel("[bold yellow]PENGATURAN & FOLDER[/bold yellow]", border_style="yellow", box=box.ASCII))
        console.print(f"Folder Utama : [underline]{cfg.get_root_download_dir()}[/underline]")
        console.print(f"Default Format: [bold]{RESOLUTION_LABELS.get(cfg.get('last_resolution', '1080p'))}[/bold]\n")

        console.print("[bold cyan][1][/bold cyan] Ganti Folder Utama Unduhan (Explorer Dialog)")
        console.print("[bold cyan][2][/bold cyan] Buka Folder downloads/ di Explorer Sekarang")
        console.print("[bold cyan][3][/bold cyan] Ubah Default Format / Resolusi")
        console.print("[bold cyan][4][/bold cyan] Kunjungi SnipGeek.com (Tech Tools & Guides)")
        console.print("[bold cyan][5][/bold cyan] Cookies Browser (untuk video yang gagal: bot-check / stream terpotong)")
        console.print("[bold cyan][6][/bold cyan] Gemini API Key (opsional — untuk fitur potong per surah murottal)")
        console.print("[bold cyan][0][/bold cyan] Kembali ke Halaman Utama\n")

        console.print(f"Status Gemini: {gemini_key_status()}")
        console.print("[dim]Key disimpan lokal di file .env (tidak pernah di-upload / ikut git)."
                      " Dapatkan key gratis: https://aistudio.google.com/apikey[/dim]\n")

        opt = Prompt.ask("Pilih menu", choices=["1", "2", "3", "4", "5", "6", "0"], default="0")

        if opt == "0":
            break
        elif opt == "1":
            old_dir = cfg.get_root_download_dir()
            new_dir = choose_folder_gui(old_dir)
            if new_dir and new_dir != old_dir:
                cfg.set_root_download_dir(new_dir)
                console.print(f"[bold green]Folder diubah ke:[/bold green] {new_dir}")
                time.sleep(1)
        elif opt == "2":
            cfg.open_download_folder()
            console.print("[bold green]Folder dibuka di Windows Explorer![/bold green]")
            time.sleep(1)
        elif opt == "3":
            render_format_menu()
            chosen_res = Prompt.ask("Pilih nomor format default baru", choices=[str(i) for i in range(1, len(FORMAT_OPTIONS)+1)], default="1")
            for num, code, label, _ in FORMAT_OPTIONS:
                if num == chosen_res:
                    cfg.set("last_resolution", code)
                    console.print(f"[bold green]Default format diatur ke:[/bold green] {label}")
                    time.sleep(1)
                    break
        elif opt == "4":
            webbrowser.open("https://snipgeek.com/")
            console.print("[bold green]Membuka https://snipgeek.com/ di browser Anda...[/bold green]")
            time.sleep(1)
        elif opt == "5":
            current = cfg.get("cookies_browser", "") or "(nonaktif)"
            console.print(f"\nCookies saat ini: [bold cyan]{current}[/bold cyan]")
            console.print("Pilih browser tempat Anda LOGIN ke YouTube — cookies-nya akan dipakai otomatis oleh yt-dlp.")
            console.print("Cocok untuk video yang gagal dengan error bot-check atau 'bytes read'.")
            console.print("[dim]Catatan: browser sebaiknya ditutup dulu agar database cookies bisa dibaca.[/dim]\n")
            for i, b in enumerate(BROWSER_CHOICES[:-1], 1):
                console.print(f"[bold cyan][{i}][/bold cyan] {b}")
            console.print("[bold cyan][0][/bold cyan] Nonaktifkan cookies")
            pilihan = Prompt.ask("Pilih browser", choices=[str(i) for i in range(len(BROWSER_CHOICES))], default="0")
            chosen = BROWSER_CHOICES[int(pilihan)]
            cfg.set("cookies_browser", chosen)
            if chosen:
                console.print(f"[bold green]Cookies browser '{chosen}' diaktifkan![/bold green] Coba unduh ulang video yang tadi gagal.")
            else:
                console.print("[bold green]Cookies dimatikan (mode normal).[/bold green]")
            time.sleep(1)
        elif opt == "6":
            console.print(f"\nStatus Gemini: {gemini_key_status()}")
            console.print(f"[bold cyan][1][/bold cyan] Pasang / ganti API key (paste)")
            console.print(f"[bold cyan][2][/bold cyan] Buka halaman ambil key gratis ({AISTUDIO_APIKEY_URL})")
            console.print(f"[bold cyan][3][/bold cyan] Buka tutorial di blog ({TUTORIAL_API_KEY_URL})")
            console.print("[bold cyan][0][/bold cyan] Batal")
            sub = Prompt.ask("Pilih", choices=["1", "2", "3", "0"], default="0")
            if sub == "1":
                keys_text = Prompt.ask(
                    "Paste Gemini API Key Anda (1 atau beberapa, dipisah koma). Kosongkan untuk batal")
                if not keys_text.strip():
                    console.print("[bold yellow]Dibatalkan; key tidak diubah.[/bold yellow]")
                elif save_gemini_keys_to_env(keys_text):
                    console.print("[bold green]✓ Gemini API Key disimpan di .env (lokal, tidak ikut git).[/bold green]")
                    console.print("[dim]Kini fitur potong per surah murottal siap dipakai.[/dim]")
                else:
                    console.print("[bold red]✗ Gagal menyimpan key. Cek izin tulis folder project.[/bold red]")
            elif sub == "2":
                webbrowser.open(AISTUDIO_APIKEY_URL)
            elif sub == "3":
                webbrowser.open(TUTORIAL_API_KEY_URL)
            time.sleep(1)


def render_format_menu():
    table = Table(title="[bold yellow]PILIHAN FORMAT & KUALITAS[/bold yellow]", box=box.ASCII, expand=False)
    table.add_column("No", style="bold cyan", justify="center")
    table.add_column("Kategori", style="bold magenta")
    table.add_column("Kualitas & Format", style="white")

    for num, code, label, cat in FORMAT_OPTIONS:
        table.add_row(num, cat.upper(), label)
    console.print(table)

def select_format_interactive(last_res):
    render_format_menu()
    last_label = RESOLUTION_LABELS.get(last_res, last_res)
    console.print(f"\n[bold green][Enter][/bold green] Gunakan Pilihan Terakhir: [bold cyan]{last_label}[/bold cyan]")
    console.print("[bold red][B][/bold red] Batalkan Unduhan\n")

    choice = Prompt.ask("Pilih nomor format (atau tekan Enter untuk langsung pakai default)", default="")

    if choice.lower() == "b":
        return None
    if choice == "":
        return last_res

    for num, code, _, _ in FORMAT_OPTIONS:
        if num == choice:
            return code
    return last_res

def check_snipgeek_milestone(current_count):
    if current_count == 5 or (current_count > 5 and current_count % 10 == 0):
        console.print()
        appreciation = Panel(
            "[bold yellow]Selamat! Anda telah berhasil mengunduh 5 media dengan lancar![/bold yellow]\n\n"
            "Aplikasi ini dikembangkan secara gratis oleh tim [bold cyan]SnipGeek[/bold cyan].\n"
            "Kunjungi [underline bold cyan]https://snipgeek.com/[/underline bold cyan] untuk menemukan berbagai tools, template, dan artikel teknologi lainnya!",
            title="[bold green]Catatan dari SnipGeek[/bold green]",
            border_style="yellow",
            box=box.ASCII
        )
        console.print(appreciation)
        open_web = Confirm.ask("Buka https://snipgeek.com/ di browser Anda sekarang?", default=True)
        if open_web:
            webbrowser.open("https://snipgeek.com/")
            console.print("[bold green]Membuka SnipGeek di browser Anda... Terima kasih atas dukungannya![/bold green]\n")
            time.sleep(1)

def main():
    downloader = YTDownloader(config_manager=cfg, ffmpeg_dir=str(BIN_DIR) if (BIN_DIR / 'ffmpeg.exe').exists() else None)

    # Onboarding Gemini key — tawarkan sekali saja selama belum ada key tersimpan
    if not find_env_file_keys() and not cfg.get("gemini_key_prompted", False):
        console.print("[bold cyan]💡 Tips:[/bold cyan] fitur [bold]✂️ Potong per Surah (murottal Juz)[/bold] "
                      "butuh Gemini API key (gratis, opsional).")
        prompt_install_gemini_key("Onboarding: Gemini API Key (opsional)")
        cfg.set("gemini_key_prompted", True)

    while True:
        render_header()
        render_status_bar()

        input_url = Prompt.ask("Masukkan URL YouTube (atau ketik S/O/W/Q)").strip()

        if not input_url:
            continue

        cmd = input_url.lower()
        if cmd == 'q':
            console.print("\n[bold green]Terima kasih telah menggunakan Mini YT Downloader by SnipGeek![/bold green]")
            break
        elif cmd == 's':
            settings_menu(downloader)
            continue
        elif cmd == 'o':
            cfg.open_download_folder()
            console.print("[bold green]Folder dibuka di Windows Explorer![/bold green]")
            time.sleep(1)
            continue
        elif cmd == 'w':
            webbrowser.open("https://snipgeek.com/")
            console.print("[bold green]Membuka https://snipgeek.com/ di browser...[/bold green]")
            time.sleep(1)
            continue
        elif cmd == 'k':
            webbrowser.open("https://aistudio.google.com/apikey")
            console.print("[bold green]Membuka https://aistudio.google.com/apikey di browser...[/bold green]")
            console.print("Setelah key disalin: ketik [bold cyan]S[/bold cyan] → menu [bold cyan][6][/bold cyan] Gemini API Key untuk memasangnya.")
            time.sleep(1)
            continue
        else:
            input_url = normalize_media_url(input_url)

        # ---------- Validasi host: hanya YouTube yang didukung ----------
        if not is_supported_youtube_url(input_url):
            console.print("\n[bold red]URL bukan link YouTube yang didukung.[/bold red]")
            console.print("[yellow]Paste link video/playlist YouTube, mis:[/yellow]")
            console.print("  [dim]https://www.youtube.com/watch?v=XXXXXXXXXXX[/dim]")
            console.print("  [dim]https://youtu.be/XXXXXXXXXXX[/dim]")
            low = input_url.lower()
            if "aistudio.google.com" in low or "accounts.google.com" in low or "ai.google.dev" in low:
                console.print("\n[cyan]Sepertinya Anda membuka Google AI Studio (untuk Gemini API key).[/cyan]")
                console.print("Ambil key gratis di: [underline]https://aistudio.google.com/apikey[/underline]")
                console.print("Lalu masukkan lewat: ketik [bold cyan]S[/bold cyan] → menu [bold cyan][6][/bold cyan] Gemini API Key.")
            Prompt.ask("\nTekan [Enter] untuk melanjutkan...")
            continue

        # ---------- Deteksi Playlist ----------
        if is_channel_url(input_url):
            console.print("\n[bold red]Link tersebut adalah channel/beranda YouTube, bukan video atau playlist.[/bold red]")
            console.print("[yellow]Salin URL video (youtube.com/watch?v=... atau youtu.be/...) atau URL playlist (youtube.com/playlist?list=...).[/yellow]")
            Prompt.ask("\nTekan [Enter] untuk melanjutkan...")
            continue

        detected = detect_playlist(input_url)
        want_playlist = False
        playlist_url = None

        if detected["kind"] == "playlist_only":
            want_playlist = True
            playlist_url = detected["playlist_url"]
        elif detected["kind"] == "both":
            console.print("\n[bold yellow]URL ini adalah video yang berada di dalam playlist.[/bold yellow]")
            console.print("[bold cyan][1][/bold cyan] Download video ini saja")
            console.print("[bold cyan][2][/bold cyan] Download seluruh playlist\n")
            scope = Prompt.ask("Pilih cakupan unduhan", choices=["1", "2"], default="1")
            if scope == "2":
                want_playlist = True
                playlist_url = detected["playlist_url"]
            else:
                input_url = detected["video_url"]

        target_saved_folder = None

        if want_playlist:
            with console.status("[bold cyan]Mengambil daftar playlist...", spinner="dots"):
                try:
                    pl_title, entries = downloader.get_playlist_info(playlist_url)
                except Exception as e:
                    console.print(f"\n[bold red]Gagal mengambil playlist:[/bold red] {e}")
                    Prompt.ask("\nTekan [Enter] untuk melanjutkan...")
                    continue

            if not entries:
                console.print("\n[bold red]Playlist kosong atau tidak dapat dibaca.[/bold red]")
                Prompt.ask("\nTekan [Enter] untuk melanjutkan...")
                continue

            n_items = len(entries)
            pl_table = Table(title="[bold yellow]Informasi Playlist[/bold yellow]", box=box.ASCII, expand=False)
            pl_table.add_column("Field", style="bold cyan")
            pl_table.add_column("Value", style="white")
            pl_table.add_row("Judul Playlist", pl_title)
            pl_table.add_row("Jumlah Item", str(n_items))
            for idx, entry in enumerate(entries[:5], 1):
                pl_table.add_row(f"Pratinjau {idx:02d}", str(entry.get('title') or entry.get('id') or '-')[:70])
            if n_items > 5:
                pl_table.add_row("...", f"dan {n_items - 5} item lainnya")
            console.print()
            console.print(pl_table)
            console.print()

            last_res = cfg.get("last_resolution", "1080p")
            res_choice = select_format_interactive(last_res)

            if not res_choice:
                continue

            cfg.set("last_resolution", res_choice)

            if n_items > 20:
                if not Confirm.ask(f"Playlist berisi [bold]{n_items}[/bold] item. Lanjutkan unduh semua?", default=True):
                    continue

            console.print(f"\n[bold green]Memulai unduh {n_items} item ({res_choice})...[/bold green]\n")
            success_files, failed = [], []
            try:
                success_files, failed, target_saved_folder = downloader.download_playlist(
                    playlist_url, res_choice, entries, playlist_title=pl_title
                )
            except KeyboardInterrupt:
                console.print("\n[yellow]Unduhan playlist dihentikan. Item yang sudah selesai tetap tersimpan.[/yellow]")
            except Exception as e:
                console.print(f"\n[bold red]Gagal mengunduh playlist:[/bold red] {e}")

            for _ in success_files:
                cfg.increment_download_count()

            console.print()
            if success_files:
                console.print(f"[bold green]Selesai:[/bold green] {len(success_files)}/{n_items} item tersimpan di [underline]{target_saved_folder}[/underline]")
            if failed:
                console.print(f"[bold red]Gagal diunduh:[/bold red] {len(failed)} item")
                for f_title, f_err in failed[:10]:
                    console.print(f"  [dim]- {f_title} ({f_err})[/dim]")
                if len(failed) > 10:
                    console.print(f"  [dim]... dan {len(failed) - 10} lainnya[/dim]")
            if not success_files and not failed:
                console.print("[bold red]Tidak ada item yang berhasil diunduh.[/bold red]")

            if success_files:
                check_snipgeek_milestone(cfg.get("download_count", 0))

        else:
            # Fetch Video Info
            with console.status("[bold cyan]Mengambil info media YouTube...", spinner="dots"):
                try:
                    info, clean_url = downloader.get_video_info(input_url)
                except Exception as e:
                    console.print(f"\n[bold red]Gagal mengambil metadata URL:[/bold red] {e}")
                    Prompt.ask("\nTekan [Enter] untuk melanjutkan...")
                    continue

            # Display Media Info Card
            title = info.get('title', 'Unknown Title')
            channel = info.get('uploader') or info.get('channel', 'Unknown Channel')
            duration = format_duration(info.get('duration'))
            views = f"{info.get('view_count', 0):,}" if info.get('view_count') else "N/A"

            info_table = Table(title="[bold yellow]Informasi Media[/bold yellow]", box=box.ASCII, expand=False)
            info_table.add_column("Field", style="bold cyan")
            info_table.add_column("Value", style="white")
            info_table.add_row("Judul", title)
            info_table.add_row("Channel/Artis", channel)
            info_table.add_row("Durasi", duration)
            info_table.add_row("Views", views)
            console.print()
            console.print(info_table)
            console.print()

            # ── ✂️ Opsi: potong per chapter/surah jadi MP3 ────────────────────
            chapters = chapters_from_info(info)
            do_split = False
            auto_detect_surah = False
            if chapters and len(chapters) > 1:
                n_ch = len(chapters)
                console.print(f"[bold cyan]✂️ Video ini punya {n_ch} chapter[/bold cyan] "
                              f"[dim](bisa dipotong jadi {n_ch} file MP3 per bagian)[/dim]")
                do_split = Confirm.ask(
                    f"Potong video jadi file MP3 per surah/chapter (skip Opening)?",
                    default=False)
            elif not chapters and cfg.get("gemini_trace", True) and looks_like_murottal(title, channel):
                # Video tanpa chapter (mis. murottal Juz 30 tanpa timestamp di
                # deskripsi) → deteksi semua surah via Gemini dari audio.
                # Bila key belum terpasang → tawaran inline pasang key dulu.
                console.print("[bold cyan]🔍 Video ini terdeteksi sebagai murottal tanpa chapter.[/bold cyan] "
                              "[dim]Surah bisa dideteksi otomatis dari audio via Gemini.[/dim]")
                if not find_env_file_keys():
                    console.print("[yellow]⚠ Fitur ini butuh Gemini API key (gratis, free tier).[/yellow]")
                    if prompt_install_gemini_key("Gemini API Key dibutuhkan"):
                        do_split = Confirm.ask(
                            "Key terpasang! Deteksi otomatis semua surah sekarang?",
                            default=False)
                        auto_detect_surah = do_split
                else:
                    do_split = Confirm.ask(
                        "Deteksi otomatis semua surah via Gemini, lalu potong jadi MP3 per surah?",
                        default=False)
                    auto_detect_surah = do_split

            if do_split:
                # Alur potong: unduh audio mentah sekali → (bila perlu) deteksi
                # surah dari audio → deteksi gap → potong tiap segmen → MP3.
                bitrate = int(cfg.get("cut_bitrate", 320) or 320)
                skip_opening = bool(cfg.get("skip_opening", True))
                sub = downloader.sanitize_title(title)

                with console.status("[bold cyan]Mengunduh audio sumber (bestaudio, tanpa konversi)...", spinner="dots"):
                    try:
                        src_file, _, src_dir = downloader.download_audio_raw(
                            clean_url, title=title, video_id=info.get('id'), subfolder=sub)
                    except Exception as e:
                        console.print(f"\n[bold red]Gagal mengunduh audio sumber:[/bold red] {e}")
                        continue
                target_saved_folder = src_dir
                console.print(f"[dim]Audio sumber: [underline]{os.path.basename(src_file)}[/underline][/dim]")

                # Mode auto-detect: video tanpa chapter → transkripsi word-level
                # (presisi) lalu petakan ke surah; fallback: sweep audio per-chunk.
                if auto_detect_surah:
                    dur = int(info.get("duration") or 0)
                    keys = find_env_file_keys()
                    console.print(f"[bold cyan]Menganalisis audio ({format_duration(dur)}) via Gemini (transkripsi kata-per-kata)...[/bold cyan]")
                    timeline = transcribe_surah_timeline(src_file, keys, dur)
                    if len(timeline) < 2:
                        console.print("[yellow]Transkripsi kurang memadai — fallback ke sweep audio per-chunk...[/yellow]")
                        timeline = sweep_surah_starts(src_file, keys, dur)
                    if len(timeline) < 2:
                        console.print("[bold red]Deteksi surah gagal (kurang dari 2 surah teridentifikasi).[/bold red]")
                        try:
                            os.remove(src_file)
                        except Exception:
                            pass
                        continue
                    # Susun chapters sintetis dari timeline (end = start surah berikutnya)
                    chapters = []
                    for i, t in enumerate(timeline):
                        end = timeline[i + 1]["start"] if i + 1 < len(timeline) else dur
                        chapters.append({"title": t["title"], "start": t["start"], "end": end})
                    skip_opening = False  # tidak ada chapter Opening sintetis
                    names = ", ".join(c["title"] for c in chapters[:5])
                    console.print(f"[green]✓ {len(chapters)} surah terdeteksi:[/green] {names}{'…' if len(chapters) > 5 else ''}")

                # Deteksi surah Juz Amma yang tidak punya timestamp (gap)
                resolved_gaps = []
                if cfg.get("gemini_trace", True):
                    gaps = detect_missing_surahs(chapters)
                    if gaps:
                        console.print(f"[yellow]⚠ {len(gaps)} surah belum terverifikasi di urutan kanonik → verifikasi via Gemini...[/yellow]")
                        keys = find_env_file_keys()
                        if not keys:
                            # Tawaran inline: pasang key di tempat agar verifikasi tetap jalan
                            if prompt_install_gemini_key("Verifikasi butuh Gemini API Key"):
                                keys = find_env_file_keys()
                        for gap in gaps:
                            console.print(f"  ↻ {gap['title']} [dim](cek window {format_duration(int(gap['prev_start']))}–{format_duration(int(gap['next_start']))})[/dim]")
                            if not keys:
                                console.print("    [red]✗ Gemini key tidak ditemukan; lanjut tanpa verifikasi (bila perlu pasang via menu S → [6]).[/red]")
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
                                console.print(f"    [green]✓ {gap['title']} ditemukan, mulai {format_duration(int(abs_start))} (model {model})[/green]")
                            elif result and result.get("status") == "absent":
                                console.print(f"    [yellow]• {gap['title']} TIDAK ada dalam rekaman (dikonfirmasi Gemini {model}); tidak dibuat file terpisah.[/yellow]")
                            else:
                                console.print(f"    [red]✗ Gagal verifikasi ({model if model else 'error'}); lanjut tanpa verifikasi.[/red]")

                segments = build_cut_segments(chapters, skip_opening=skip_opening, resolved_gaps=resolved_gaps, video_duration=info.get('duration'))
                if not segments:
                    console.print("[bold red]Tidak ada segmen valid untuk dipotong.[/bold red]")
                    continue

                console.print(f"\n[bold green]Memotong {len(segments)} segmen → MP3 {bitrate}kbps...[/bold green]")

                def _split_progress(i, total, seg_title, dur):
                    console.print(f"  [cyan][{i:02d}/{total}][/cyan] {seg_title} [dim]({format_duration(int(dur))})[/dim]")

                try:
                    outputs = cut_audio_segments(
                        src_file, segments, src_dir,
                        bitrate=bitrate, artist=channel or "",
                        on_progress=_split_progress,
                    )
                except Exception as e:
                    console.print(f"\n[bold red]Gagal memotong segmen:[/bold red] {e}")
                    continue

                # Bersihkan file sumber mentah (user hanya mau file per-surah)
                try:
                    os.remove(src_file)
                except Exception:
                    pass

                new_count = 0
                for _ in outputs:
                    new_count = cfg.increment_download_count()
                console.print(f"\n[bold green]Selesai:[/bold green] {len(outputs)} file MP3 tersimpan di [underline]{src_dir}[/underline]")
                console.print(f"[dim]Total media tersimpan: {new_count}[/dim]\n")
                check_snipgeek_milestone(new_count)
            else:
                last_res = cfg.get("last_resolution", "1080p")
                res_choice = select_format_interactive(last_res)

                if not res_choice:
                    continue

                cfg.set("last_resolution", res_choice)

                console.print(f"\n[bold green]Memulai proses unduh & konversi...[/bold green]")
                try:
                    out_file, target_saved_folder = downloader.download_with_fallback(
                        clean_url,
                        format_type=res_choice,
                        title=info.get('title', ''),
                        video_id=info.get('id'),
                    )
                    new_count = cfg.increment_download_count()
                    console.print(f"\n[bold green]Berhasil Disimpan:[/bold green] [underline]{out_file}[/underline]")
                    console.print(f"[dim]Total media tersimpan: {new_count}[/dim]\n")

                    check_snipgeek_milestone(new_count)

                except Exception as e:
                    console.print(f"\n[bold red]Gagal mengunduh/mengonversi media:[/bold red] {e}\n")

        console.print("[bold cyan][1][/bold cyan] Download Media Lain")
        console.print("[bold cyan][2][/bold cyan] Buka Folder File yang Baru Diunduh")
        console.print("[bold cyan][3][/bold cyan] Buka Folder Utama downloads/")
        console.print("[bold cyan][4][/bold cyan] Pengaturan / Ganti Folder")
        console.print("[bold cyan][5][/bold cyan] Kunjungi SnipGeek.com")
        console.print("[bold cyan][0][/bold cyan] Keluar\n")

        next_action = Prompt.ask("Pilih aksi selanjutnya", choices=["1", "2", "3", "4", "5", "0"], default="1")

        if next_action == "0":
            console.print("\n[bold green]Terima kasih telah menggunakan Mini YT Downloader by SnipGeek![/bold green]")
            break
        elif next_action == "2":
            cfg.open_download_folder(target_saved_folder)
        elif next_action == "3":
            cfg.open_download_folder()
        elif next_action == "4":
            settings_menu(downloader)
        elif next_action == "5":
            webbrowser.open("https://snipgeek.com/")
            console.print("[bold green]Membuka https://snipgeek.com/...[/bold green]")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Operasi dibatalkan oleh pengguna.[/yellow]")
        sys.exit(0)
