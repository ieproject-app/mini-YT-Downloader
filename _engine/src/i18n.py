"""
i18n.py — Dwibahasa (ID/EN) untuk mini-YT. Murni stdlib, tanpa dependensi.

Pemakaian:
    import i18n
    i18n.init(config_path)          # baca "language" dari config.json
    i18n.set_language("en")         # override runtime ("auto" -> deteksi locale)
    from i18n import t
    print(t("main.url_prompt"))
    print(t("status.total_saved", n=5))

Fallback: kunci tidak ada di bahasa aktif -> coba "id" -> "en" -> kembalikan
kunci itu sendiri (app tetap jalan walau ada kunci terlewat).
"""

import json
import locale
from pathlib import Path

_STRINGS = {
    # ─── EN ───────────────────────────────────────────────────────────────
    "en": {
        # Header & status bar
        "header.title": "MINI YOUTUBE DOWNLOADER (v1.3)",
        "header.subtitle": "Video & High-Quality Audio Downloader (MP3 320k, FLAC, M4A, 4K) • Cut per Surah/Chapter",
        "header.credit": "Crafted with care by SnipGeek - https://snipgeek.com/",
        "status.downloads_folder": "Downloads Folder:",
        "status.auto_split": "(auto-split: [cyan]video/[/cyan] & [cyan]audio/[/cyan])",
        "status.default_format": "Default Format:",
        "status.engine_ffmpeg": "FFmpeg Engine:",
        "status.cookies_browser": "Browser Cookies:",
        "status.total_downloads": "Total Downloads:",
        "status.total_saved": "[bold]{n} media saved[/bold]",
        "status.gemini_key": "Gemini API Key:",
        "status.ffmpeg_ready": "[bold green]Ready[/bold green]",
        "status.ffmpeg_missing": "[bold red]Not found[/bold red]",
        "status.cookies_off": "[dim]off[/dim]",
        "status.shortcuts": "[dim]Shortcuts: type [bold cyan]'S'[/bold cyan] (Settings) | [bold cyan]'O'[/bold cyan] (Open Folder) | [bold cyan]'K'[/bold cyan] (Gemini API Key) | [bold cyan]'W'[/bold cyan] (SnipGeek.com) | [bold cyan]'Q'[/bold cyan] (Quit)[/dim]\n",

        # Language
        "lang.question_title": "[bold cyan]🌐 Choose language / Pilih bahasa[/bold cyan]",
        "lang.opt_id": "[bold cyan][1][/bold cyan] Bahasa Indonesia",
        "lang.opt_en": "[bold cyan][2][/bold cyan] English",
        "lang.prompt": "Choose language / Pilih bahasa",
        "lang.set_done": "[bold green]Language set to English.[/bold green]",
        "settings.lang_menu_title": "[bold cyan]🌐 Language / Bahasa[/bold cyan]",

        # Main prompt & flow
        "main.url_prompt": "Enter YouTube URL (or type S/O/K/W/Q)",
        "main.bye": "\n[bold green]Thank you for using Mini YT Downloader by SnipGeek![/bold green]",
        "main.folder_opened": "[bold green]Folder opened in Windows Explorer![/bold green]",
        "main.opening_site": "[bold green]Opening https://snipgeek.com/ in your browser...[/bold green]",
        "main.k_opened": "[bold green]Opening https://aistudio.google.com/apikey in your browser...[/bold green]",
        "main.k_hint": "After copying your key: type [bold cyan]S[/bold cyan] → menu [bold cyan][6][/bold cyan] Gemini API Key to install it.",
        "main.bad_url.title": "\n[bold red]That URL is not a supported YouTube link.[/bold red]",
        "main.bad_url.examples": "[yellow]Paste a YouTube video/playlist link, e.g.:[/yellow]",
        "main.bad_url.ai_hint1": "\n[cyan]Looks like you opened Google AI Studio (for a Gemini API key).[/cyan]",
        "main.bad_url.ai_hint2": "Get a free key at: [underline]https://aistudio.google.com/apikey[/underline]",
        "main.bad_url.ai_hint3": "Then add it via: type [bold cyan]S[/bold cyan] → menu [bold cyan][6][/bold cyan] Gemini API Key.",
        "main.press_enter": "\nPress [Enter] to continue...",
        "main.channel_link.title": "\n[bold red]That link is a YouTube channel/homepage, not a video or playlist.[/bold red]",
        "main.channel_link.hint": "[yellow]Copy a video URL (youtube.com/watch?v=... or youtu.be/...) or a playlist URL (youtube.com/playlist?list=...).[/yellow]",
        "main.in_playlist.title": "\n[bold yellow]This URL is a video inside a playlist.[/bold yellow]",
        "main.in_playlist.opt1": "[bold cyan][1][/bold cyan] Download this video only",
        "main.in_playlist.opt2": "[bold cyan][2][/bold cyan] Download the entire playlist\n",
        "main.in_playlist.prompt": "Choose download scope",
        "main.starting_playlist": "\n[bold green]Starting download of {n} items ({res})...[/bold green]\n",
        "main.playlist_stopped": "\n[yellow]Playlist download stopped. Completed items are kept.[/yellow]",
        "main.playlist_failed": "\n[bold red]Failed to download playlist:[/bold red] {err}",
        "main.done_line": "[bold green]Done:[/bold green] {ok}/{n} items saved in [underline]{folder}[/underline]",
        "main.failed_line": "[bold red]Failed to download:[/bold red] {n} item(s)",
        "main.failed_more": "  [dim]... and {n} more[/dim]",
        "main.none_downloaded": "[bold red]Nothing was downloaded.[/bold red]",
        "main.starting_download": "\n[bold green]Starting download & conversion...[/bold green]",
        "main.saved_ok": "\n[bold green]Saved:[/bold green] [underline]{file}[/underline]",
        "main.total_saved": "[dim]Total media saved: {n}[/dim]\n",
        "main.download_failed": "\n[bold red]Download/conversion failed:[/bold red] {err}\n",
        "main.next1": "[bold cyan][1][/bold cyan] Download Another Media",
        "main.next2": "[bold cyan][2][/bold cyan] Open Folder of Newly Downloaded File",
        "main.next3": "[bold cyan][3][/bold cyan] Open Main downloads/ Folder",
        "main.next4": "[bold cyan][4][/bold cyan] Settings / Change Folder",
        "main.next5": "[bold cyan][5][/bold cyan] Visit SnipGeek.com",
        "main.next0": "[bold cyan][0][/bold cyan] Quit\n",
        "main.next_prompt": "Choose next action",

        # Metadata fetch & info card
        "main.fetching_playlist": "[bold cyan]Fetching playlist...", 
        "main.fetching_info": "[bold cyan]Fetching YouTube media info...", 
        "main.metadata_failed": "\n[bold red]Failed to fetch URL metadata:[/bold red] {err}",
        "main.playlist_failed_fetch": "\n[bold red]Failed to fetch playlist:[/bold red] {err}",
        "main.playlist_empty": "\n[bold red]Playlist is empty or unreadable.[/bold red]",
        "info.playlist_table": "[bold yellow]Playlist Information[/bold yellow]",
        "info.col_field": "Field",
        "info.col_value": "Value",
        "info.playlist_title": "Playlist Title",
        "info.playlist_items": "Item Count",
        "info.preview": "Preview {idx}",
        "info.more_items": "... and {n} more items",
        "info.media_table": "[bold yellow]Media Information[/bold yellow]",
        "info.lbl_title": "Title",
        "info.lbl_channel": "Channel/Artist",
        "info.lbl_duration": "Duration",
        "info.lbl_views": "Views",
        "info.confirm_big_playlist": "Playlist contains [bold]{n}[/bold] items. Download all?",

        # Split (per-surah) flow
        "split.has_chapters": "[bold cyan]✂️ This video has {n} chapters[/bold cyan] [dim](can be cut into {n} MP3 files)[/dim]",
        "split.split_prompt": "Cut this video into per-surah/chapter MP3 files (skip Opening)?",
        "split.murottal_detected": "[bold cyan]🔍 This video looks like a chapter-less murottal.[/bold cyan] [dim]Surahs can be auto-detected from the audio via Gemini.[/dim]",
        "split.needs_key": "[yellow]⚠ This feature requires a Gemini API key (free tier).[/yellow]",
        "split.key_installed_ask": "Key installed! Auto-detect all surahs now?",
        "split.auto_detect_prompt": "Auto-detect all surahs via Gemini, then cut into per-surah MP3 files?",
        "split.downloading_source": "[bold cyan]Downloading source audio (bestaudio, no conversion)...",
        "split.source_failed": "\n[bold red]Failed to download source audio:[/bold red] {err}",
        "split.source_line": "[dim]Source audio: [underline]{name}[/underline][/dim]",
        "split.analyzing": "[bold cyan]Analyzing audio ({dur}) via Gemini (word-level transcription)...[/bold cyan]",
        "split.transcription_weak": "[yellow]Transcription insufficient — falling back to per-chunk audio sweep...[/yellow]",
        "split.detect_failed": "[bold red]Surah detection failed (fewer than 2 surahs identified).[/bold red]",
        "split.detected_count": "[green]✓ {n} surahs detected:[/green] {names}{more}",
        "split.gaps": "[yellow]⚠ {n} surah(s) unverified in canonical order → verifying via Gemini...[/yellow]",
        "split.gap_check": "  ↻ {title} [dim](checking window {t1}–{t2})[/dim]",
        "split.gap_no_key": "    [red]✗ Gemini key not found; skipping verification (install via S → [6] if needed).[/red]",
        "split.gap_found": "    [green]✓ {title} found, starts at {t} (model {model})[/green]",
        "split.gap_absent": "    [yellow]• {title} is NOT in the recording (confirmed by Gemini {model}); no separate file.[/yellow]",
        "split.gap_failed": "    [red]✗ Verification failed ({model}); skipping verification.[/red]",
        "split.cutting": "\n[bold green]Cutting {n} segments → MP3 {bitrate}kbps...[/bold green]",
        "split.no_segments": "[bold red]No valid segments to cut.[/bold red]",
        "split.cut_failed": "\n[bold red]Failed to cut segments:[/bold red] {err}",
        "split.done": "\n[bold green]Done:[/bold green] {n} MP3 files saved in [underline]{folder}[/underline]",

        # Onboarding / Gemini key
        "onboard.tip": "[bold cyan]💡 Tip:[/bold cyan] the [bold]✂️ Cut per Surah (Juz murottal)[/bold] feature needs a Gemini API key (free, optional).",
        "onboard.title": "Onboarding: Gemini API Key (optional)",
        "key.guide_line": "Full guide: [underline]{url}[/underline]",
        "key.free_line": "[dim]Free key: open [underline]{url}[/underline] → sign in with Google → Create API key → Copy.[/dim]",
        "key.ask_paste": "Enter / paste an API key now?",
        "key.paste_prompt": "Paste your Gemini API Key (multiple keys separated by commas)",
        "key.cancelled": "[yellow]Cancelled; key unchanged.[/yellow]",
        "key.saved": "[bold green]✓ Gemini API Key saved to .env (local, never committed to git).[/bold green]",
        "key.ready": "[dim]The per-surah murottal cut feature is now ready.[/dim]",
        "key.save_failed": "[bold red]✗ Failed to save the key. Check write permissions of the project folder.[/bold red]",
        "key.verify_needed": "Verification needs a Gemini API Key",
        "key.status_active": "[bold green]{n} key(s) active[/bold green]",
        "key.status_missing": "[dim]not set (optional — for the per-surah cut feature)[/dim]",

        # Settings menu
        "settings.title": "[bold yellow]SETTINGS & FOLDER[/bold yellow]",
        "settings.folder_main": "Main Folder : [underline]{dir}[/underline]",
        "settings.default_format": "Default Format: [bold]{label}[/bold]\n",
        "settings.m1": "[bold cyan][1][/bold cyan] Change Main Download Folder (Explorer Dialog)",
        "settings.m2": "[bold cyan][2][/bold cyan] Open downloads/ Folder in Explorer Now",
        "settings.m3": "[bold cyan][3][/bold cyan] Change Default Format / Resolution",
        "settings.m4": "[bold cyan][4][/bold cyan] Visit SnipGeek.com (Tech Tools & Guides)",
        "settings.m5": "[bold cyan][5][/bold cyan] Browser Cookies (for videos that fail: bot-check / truncated stream)",
        "settings.m6": "[bold cyan][6][/bold cyan] Gemini API Key (optional — for the murottal per-surah cut feature)",
        "settings.m7": "[bold cyan][7][/bold cyan] Language / Bahasa",
        "settings.m0": "[bold cyan][0][/bold cyan] Back to Main Page\n",
        "settings.prompt": "Choose menu",
        "settings.folder_changed": "[bold green]Folder changed to:[/bold green] {dir}",
        "settings.format_set": "[bold green]Default format set to:[/bold green] {label}",
        "settings.key_note": "[dim]Keys are stored locally in a .env file (never uploaded / committed to git)."
                             " Get a free key: https://aistudio.google.com/apikey[/dim]\n",
        "settings.cookies.current": "\nCurrent cookies: [bold cyan]{current}[/bold cyan]",
        "settings.cookies.prompt1": "Pick the browser where you are LOGGED IN to YouTube — its cookies will be used automatically by yt-dlp.",
        "settings.cookies.prompt2": "Useful for videos failing with bot-check or 'bytes read' errors.",
        "settings.cookies.note": "[dim]Note: close that browser first so its cookie database can be read.[/dim]\n",
        "settings.cookies.disable": "[bold cyan][0][/bold cyan] Disable cookies",
        "settings.cookies.choose": "Pick a browser",
        "settings.cookies.enabled": "[bold green]Browser cookies '{browser}' enabled![/bold green] Retry the video that failed earlier.",
        "settings.cookies.disabled": "[bold green]Cookies disabled (normal mode).[/bold green]",
        "settings.gemini.sub1": "[bold cyan][1][/bold cyan] Install / replace API key (paste)",
        "settings.gemini.sub2": "[bold cyan][2][/bold cyan] Open the free key page ({url})",
        "settings.gemini.sub3": "[bold cyan][3][/bold cyan] Open the blog tutorial ({url})",
        "settings.gemini.cancel": "[bold cyan][0][/bold cyan] Cancel",
        "settings.gemini.choose": "Choose",
        "settings.gemini.paste_prompt": "Paste your Gemini API Key (one or more, comma-separated). Leave empty to cancel",

        # Format menu
        "format.menu_title": "[bold yellow]FORMAT & QUALITY OPTIONS[/bold yellow]",
        "format.col_no": "No",
        "format.col_cat": "Category",
        "format.col_quality": "Quality & Format",
        "format.use_last": "\n[bold green][Enter][/bold green] Use Last Choice: [bold cyan]{label}[/bold cyan]",
        "format.cancel": "[bold red][B][/bold red] Cancel Download\n",
        "format.prompt": "Pick a format number (or press Enter to use the default)",

        # Milestone
        "milestone.title": "[bold green]A note from SnipGeek[/bold green]",
        "milestone.body": "[bold yellow]Congrats! You have smoothly downloaded {n} pieces of media![/bold yellow]\n\n"
                          "This app is developed for free by the [bold cyan]SnipGeek[/bold cyan] team.\n"
                          "Visit [underline bold cyan]https://snipgeek.com/[/underline bold cyan] to find more tools, templates, and tech articles!",
        "milestone.open_prompt": "Open https://snipgeek.com/ in your browser now?",
        "milestone.opened": "[bold green]Opening SnipGeek in your browser... Thank you for the support![/bold green]\n",

        # Format labels
        "fmt.1080p": "1080p Full HD (MP4 - Recommended)",
        "fmt.720p": "720p HD (MP4 - Light & Fast)",
        "fmt.2160p": "4K Ultra HD (2160p - MP4)",
        "fmt.best": "Best Video (Max Quality Auto)",
        "fmt.480p": "480p SD (MP4)",
        "fmt.mp3_320": "MP3 320 kbps (Ultra HQ + Cover Art + ID3)",
        "fmt.mp3_192": "MP3 192 kbps (Standard HQ + Cover Art)",
        "fmt.m4a": "M4A / AAC (Original Audio Stream + Cover)",
        "fmt.flac": "FLAC (Lossless Master Audio)",
        "fmt.wav": "WAV (Uncompressed PCM Studio)",

        # Misc
        "common.na": "N/A",
        "common.gui_warning": "[yellow]GUI dialog warning:[/yellow] {err}",
        "common.choose_folder_title": "Choose Main Storage Folder",
        "common.kb_interrupt": "\n\n[yellow]Operation cancelled by the user.[/yellow]",

        # downloader.py
        "dl.downloading": "[bold yellow]Downloading...",
        "dl.processing": "[bold green]Processing & Converting...",
        "dl.retry_alternate": "connection dropped, retrying via alternate route...",
        "dl.retry_fallback": "still failing, trying a lower-quality fallback format...",
        "dl.retry_line": "[yellow]↻[/yellow] {msg}",
        "dl.item_ok": "[bold green]  ✓ {i:02d}/{total}[/bold green] {title}",
        "dl.item_fail": "[bold red]  ✗ {i:02d}/{total}[/bold red] {title} [dim]— {err}[/dim]",
        "dl.retry_item": "[yellow]  ↻ {i:02d}/{total}[/yellow] {title} [dim]— {msg}[/dim]",

        # preflight.py
        "pf.ffmpeg_missing": "\n[!] FFmpeg not detected on the system or internal folder.",
        "pf.ffmpeg_downloading": "[*] Starting portable FFmpeg auto-download (~90MB)... Please wait...",
        "pf.ffmpeg_progress": "\r -> Downloading FFmpeg: {pct}% [{read}MB / {total}MB]",
        "pf.ffmpeg_extracting": "\n[*] Extracting FFmpeg binaries to the internal folder...",
        "pf.ffmpeg_done": "[✓] FFmpeg installed successfully (portable)!",
        "pf.ffmpeg_failed": "\n[X] Failed to download/extract FFmpeg: {err}",
        "pf.python_old": "[X] Python version too old: {ver}. Python >= 3.9 required",
        "pf.pip_installing": "[*] Installing required Python packages ({pkgs})...",
        "pf.pip_done": "[✓] Python dependencies installed successfully!",
        "pf.ffmpeg_not_found": "[X] FFmpeg is required but was not found.",
    },

    # ─── ID ───────────────────────────────────────────────────────────────
    "id": {
        "header.title": "MINI YOUTUBE DOWNLOADER (v1.3)",
        "header.subtitle": "Video & High-Quality Audio Downloader (MP3 320k, FLAC, M4A, 4K) • Potong per Surah/Chapter",
        "header.credit": "Crafted with care by SnipGeek - https://snipgeek.com/",
        "status.downloads_folder": "Folder Downloads:",
        "status.auto_split": "(auto-split: [cyan]video/[/cyan] & [cyan]audio/[/cyan])",
        "status.default_format": "Format Default:",
        "status.engine_ffmpeg": "Engine FFmpeg:",
        "status.cookies_browser": "Cookies Browser:",
        "status.total_downloads": "Total Unduhan:",
        "status.total_saved": "[bold]{n} media tersimpan[/bold]",
        "status.gemini_key": "Gemini API Key:",
        "status.ffmpeg_ready": "[bold green]Siap[/bold green]",
        "status.ffmpeg_missing": "[bold red]Tidak ada[/bold red]",
        "status.cookies_off": "[dim]nonaktif[/dim]",
        "status.shortcuts": "[dim]Shortcut: Ketik [bold cyan]'S'[/bold cyan] (Settings/Folder) | [bold cyan]'O'[/bold cyan] (Buka Folder) | [bold cyan]'K'[/bold cyan] (Gemini API Key) | [bold cyan]'W'[/bold cyan] (SnipGeek.com) | [bold cyan]'Q'[/bold cyan] (Keluar)[/dim]\n",

        "lang.question_title": "[bold cyan]🌐 Pilih bahasa / Choose language[/bold cyan]",
        "lang.opt_id": "[bold cyan][1][/bold cyan] Bahasa Indonesia",
        "lang.opt_en": "[bold cyan][2][/bold cyan] English",
        "lang.prompt": "Pilih bahasa / Choose language",
        "lang.set_done": "[bold green]Bahasa diatur ke Bahasa Indonesia.[/bold green]",
        "settings.lang_menu_title": "[bold cyan]🌐 Language / Bahasa[/bold cyan]",

        "main.url_prompt": "Masukkan URL YouTube (atau ketik S/O/K/W/Q)",
        "main.bye": "\n[bold green]Terima kasih telah menggunakan Mini YT Downloader by SnipGeek![/bold green]",
        "main.folder_opened": "[bold green]Folder dibuka di Windows Explorer![/bold green]",
        "main.opening_site": "[bold green]Membuka https://snipgeek.com/ di browser...[/bold green]",
        "main.k_opened": "[bold green]Membuka https://aistudio.google.com/apikey di browser...[/bold green]",
        "main.k_hint": "Setelah key disalin: ketik [bold cyan]S[/bold cyan] → menu [bold cyan][6][/bold cyan] Gemini API Key untuk memasangnya.",
        "main.bad_url.title": "\n[bold red]URL bukan link YouTube yang didukung.[/bold red]",
        "main.bad_url.examples": "[yellow]Paste link video/playlist YouTube, mis:[/yellow]",
        "main.bad_url.ai_hint1": "\n[cyan]Sepertinya Anda membuka Google AI Studio (untuk Gemini API key).[/cyan]",
        "main.bad_url.ai_hint2": "Ambil key gratis di: [underline]https://aistudio.google.com/apikey[/underline]",
        "main.bad_url.ai_hint3": "Lalu masukkan lewat: ketik [bold cyan]S[/bold cyan] → menu [bold cyan][6][/bold cyan] Gemini API Key.",
        "main.press_enter": "\nTekan [Enter] untuk melanjutkan...",
        "main.channel_link.title": "\n[bold red]Link tersebut adalah channel/beranda YouTube, bukan video atau playlist.[/bold red]",
        "main.channel_link.hint": "[yellow]Salin URL video (youtube.com/watch?v=... atau youtu.be/...) atau URL playlist (youtube.com/playlist?list=...).[/yellow]",
        "main.in_playlist.title": "\n[bold yellow]URL ini adalah video yang berada di dalam playlist.[/bold yellow]",
        "main.in_playlist.opt1": "[bold cyan][1][/bold cyan] Download video ini saja",
        "main.in_playlist.opt2": "[bold cyan][2][/bold cyan] Download seluruh playlist\n",
        "main.in_playlist.prompt": "Pilih cakupan unduhan",
        "main.starting_playlist": "\n[bold green]Memulai unduh {n} item ({res})...[/bold green]\n",
        "main.playlist_stopped": "\n[yellow]Unduhan playlist dihentikan. Item yang sudah selesai tetap tersimpan.[/yellow]",
        "main.playlist_failed": "\n[bold red]Gagal mengunduh playlist:[/bold red] {err}",
        "main.done_line": "[bold green]Selesai:[/bold green] {ok}/{n} item tersimpan di [underline]{folder}[/underline]",
        "main.failed_line": "[bold red]Gagal diunduh:[/bold red] {n} item",
        "main.failed_more": "  [dim]... dan {n} lainnya[/dim]",
        "main.none_downloaded": "[bold red]Tidak ada item yang berhasil diunduh.[/bold red]",
        "main.starting_download": "\n[bold green]Memulai proses unduh & konversi...[/bold green]",
        "main.saved_ok": "\n[bold green]Berhasil Disimpan:[/bold green] [underline]{file}[/underline]",
        "main.total_saved": "[dim]Total media tersimpan: {n}[/dim]\n",
        "main.download_failed": "\n[bold red]Gagal mengunduh/mengonversi media:[/bold red] {err}\n",
        "main.next1": "[bold cyan][1][/bold cyan] Download Media Lain",
        "main.next2": "[bold cyan][2][/bold cyan] Buka Folder File yang Baru Diunduh",
        "main.next3": "[bold cyan][3][/bold cyan] Buka Folder Utama downloads/",
        "main.next4": "[bold cyan][4][/bold cyan] Pengaturan / Ganti Folder",
        "main.next5": "[bold cyan][5][/bold cyan] Kunjungi SnipGeek.com",
        "main.next0": "[bold cyan][0][/bold cyan] Keluar\n",
        "main.next_prompt": "Pilih aksi selanjutnya",

        "main.fetching_playlist": "[bold cyan]Mengambil daftar playlist...",
        "main.fetching_info": "[bold cyan]Mengambil info media YouTube...",
        "main.metadata_failed": "\n[bold red]Gagal mengambil metadata URL:[/bold red] {err}",
        "main.playlist_failed_fetch": "\n[bold red]Gagal mengambil playlist:[/bold red] {err}",
        "main.playlist_empty": "\n[bold red]Playlist kosong atau tidak dapat dibaca.[/bold red]",
        "info.playlist_table": "[bold yellow]Informasi Playlist[/bold yellow]",
        "info.col_field": "Field",
        "info.col_value": "Value",
        "info.playlist_title": "Judul Playlist",
        "info.playlist_items": "Jumlah Item",
        "info.preview": "Pratinjau {idx}",
        "info.more_items": "... dan {n} item lainnya",
        "info.media_table": "[bold yellow]Informasi Media[/bold yellow]",
        "info.lbl_title": "Judul",
        "info.lbl_channel": "Channel/Artis",
        "info.lbl_duration": "Durasi",
        "info.lbl_views": "Views",
        "info.confirm_big_playlist": "Playlist berisi [bold]{n}[/bold] item. Lanjutkan unduh semua?",

        "split.has_chapters": "[bold cyan]✂️ Video ini punya {n} chapter[/bold cyan] [dim](bisa dipotong jadi {n} file MP3 per bagian)[/dim]",
        "split.split_prompt": "Potong video jadi file MP3 per surah/chapter (skip Opening)?",
        "split.murottal_detected": "[bold cyan]🔍 Video ini terdeteksi sebagai murottal tanpa chapter.[/bold cyan] [dim]Surah bisa dideteksi otomatis dari audio via Gemini.[/dim]",
        "split.needs_key": "[yellow]⚠ Fitur ini butuh Gemini API key (gratis, free tier).[/yellow]",
        "split.key_installed_ask": "Key terpasang! Deteksi otomatis semua surah sekarang?",
        "split.auto_detect_prompt": "Deteksi otomatis semua surah via Gemini, lalu potong jadi MP3 per surah?",
        "split.downloading_source": "[bold cyan]Mengunduh audio sumber (bestaudio, tanpa konversi)...",
        "split.source_failed": "\n[bold red]Gagal mengunduh audio sumber:[/bold red] {err}",
        "split.source_line": "[dim]Audio sumber: [underline]{name}[/underline][/dim]",
        "split.analyzing": "[bold cyan]Menganalisis audio ({dur}) via Gemini (transkripsi kata-per-kata)...[/bold cyan]",
        "split.transcription_weak": "[yellow]Transkripsi kurang memadai — fallback ke sweep audio per-chunk...[/yellow]",
        "split.detect_failed": "[bold red]Deteksi surah gagal (kurang dari 2 surah teridentifikasi).[/bold red]",
        "split.detected_count": "[green]✓ {n} surah terdeteksi:[/green] {names}{more}",
        "split.gaps": "[yellow]⚠ {n} surah belum terverifikasi di urutan kanonik → verifikasi via Gemini...[/yellow]",
        "split.gap_check": "  ↻ {title} [dim](cek window {t1}–{t2})[/dim]",
        "split.gap_no_key": "    [red]✗ Gemini key tidak ditemukan; lanjut tanpa verifikasi (bila perlu pasang via menu S → [6]).[/red]",
        "split.gap_found": "    [green]✓ {title} ditemukan, mulai {t} (model {model})[/green]",
        "split.gap_absent": "    [yellow]• {title} TIDAK ada dalam rekaman (dikonfirmasi Gemini {model}); tidak dibuat file terpisah.[/yellow]",
        "split.gap_failed": "    [red]✗ Gagal verifikasi ({model}); lanjut tanpa verifikasi.[/red]",
        "split.cutting": "\n[bold green]Memotong {n} segmen → MP3 {bitrate}kbps...[/bold green]",
        "split.no_segments": "[bold red]Tidak ada segmen valid untuk dipotong.[/bold red]",
        "split.cut_failed": "\n[bold red]Gagal memotong segmen:[/bold red] {err}",
        "split.done": "\n[bold green]Selesai:[/bold green] {n} file MP3 tersimpan di [underline]{folder}[/underline]",

        "onboard.tip": "[bold cyan]💡 Tips:[/bold cyan] fitur [bold]✂️ Potong per Surah (murottal Juz)[/bold] butuh Gemini API key (gratis, opsional).",
        "onboard.title": "Onboarding: Gemini API Key (opsional)",
        "key.guide_line": "Panduan lengkap: [underline]{url}[/underline]",
        "key.free_line": "[dim]Key gratis: buka [underline]{url}[/underline] → login Google → Create API key → Copy.[/dim]",
        "key.ask_paste": "Masukkan / paste API key sekarang?",
        "key.paste_prompt": "Paste Gemini API Key (beberapa key dipisah koma)",
        "key.cancelled": "[yellow]Dibatalkan; key tidak diubah.[/yellow]",
        "key.saved": "[bold green]✓ Gemini API Key tersimpan di .env (lokal, tidak ikut git).[/bold green]",
        "key.ready": "[dim]Kini fitur potong per surah murottal siap dipakai.[/dim]",
        "key.save_failed": "[bold red]✗ Gagal menyimpan key. Cek izin tulis folder project.[/bold red]",
        "key.verify_needed": "Verifikasi butuh Gemini API Key",
        "key.status_active": "[bold green]{n} key aktif[/bold green]",
        "key.status_missing": "[dim]belum diatur (opsional — untuk fitur potong per surah)[/dim]",

        "settings.title": "[bold yellow]PENGATURAN & FOLDER[/bold yellow]",
        "settings.folder_main": "Folder Utama : [underline]{dir}[/underline]",
        "settings.default_format": "Default Format: [bold]{label}[/bold]\n",
        "settings.m1": "[bold cyan][1][/bold cyan] Ganti Folder Utama Unduhan (Explorer Dialog)",
        "settings.m2": "[bold cyan][2][/bold cyan] Buka Folder downloads/ di Explorer Sekarang",
        "settings.m3": "[bold cyan][3][/bold cyan] Ubah Default Format / Resolusi",
        "settings.m4": "[bold cyan][4][/bold cyan] Kunjungi SnipGeek.com (Tech Tools & Guides)",
        "settings.m5": "[bold cyan][5][/bold cyan] Cookies Browser (untuk video yang gagal: bot-check / stream terpotong)",
        "settings.m6": "[bold cyan][6][/bold cyan] Gemini API Key (opsional — untuk fitur potong per surah murottal)",
        "settings.m7": "[bold cyan][7][/bold cyan] Bahasa / Language",
        "settings.m0": "[bold cyan][0][/bold cyan] Kembali ke Halaman Utama\n",
        "settings.prompt": "Pilih menu",
        "settings.folder_changed": "[bold green]Folder diubah ke:[/bold green] {dir}",
        "settings.format_set": "[bold green]Default format diatur ke:[/bold green] {label}",
        "settings.key_note": "[dim]Key disimpan lokal di file .env (tidak pernah di-upload / ikut git)."
                             " Dapatkan key gratis: https://aistudio.google.com/apikey[/dim]\n",
        "settings.cookies.current": "\nCookies saat ini: [bold cyan]{current}[/bold cyan]",
        "settings.cookies.prompt1": "Pilih browser tempat Anda LOGIN ke YouTube — cookies-nya akan dipakai otomatis oleh yt-dlp.",
        "settings.cookies.prompt2": "Cocok untuk video yang gagal dengan error bot-check atau 'bytes read'.",
        "settings.cookies.note": "[dim]Catatan: browser sebaiknya ditutup dulu agar database cookies bisa dibaca.[/dim]\n",
        "settings.cookies.disable": "[bold cyan][0][/bold cyan] Nonaktifkan cookies",
        "settings.cookies.choose": "Pilih browser",
        "settings.cookies.enabled": "[bold green]Cookies browser '{browser}' diaktifkan![/bold green] Coba unduh ulang video yang tadi gagal.",
        "settings.cookies.disabled": "[bold green]Cookies dimatikan (mode normal).[/bold green]",
        "settings.gemini.sub1": "[bold cyan][1][/bold cyan] Pasang / ganti API key (paste)",
        "settings.gemini.sub2": "[bold cyan][2][/bold cyan] Buka halaman ambil key gratis ({url})",
        "settings.gemini.sub3": "[bold cyan][3][/bold cyan] Buka tutorial di blog ({url})",
        "settings.gemini.cancel": "[bold cyan][0][/bold cyan] Batal",
        "settings.gemini.choose": "Pilih",
        "settings.gemini.paste_prompt": "Paste Gemini API Key Anda (1 atau beberapa, dipisah koma). Kosongkan untuk batal",

        "format.menu_title": "[bold yellow]PILIHAN FORMAT & KUALITAS[/bold yellow]",
        "format.col_no": "No",
        "format.col_cat": "Kategori",
        "format.col_quality": "Kualitas & Format",
        "format.use_last": "\n[bold green][Enter][/bold green] Gunakan Pilihan Terakhir: [bold cyan]{label}[/bold cyan]",
        "format.cancel": "[bold red][B][/bold red] Batalkan Unduhan\n",
        "format.prompt": "Pilih nomor format (atau tekan Enter untuk langsung pakai default)",

        "milestone.title": "[bold green]Catatan dari SnipGeek[/bold green]",
        "milestone.body": "[bold yellow]Selamat! Anda telah berhasil mengunduh {n} media dengan lancar![/bold yellow]\n\n"
                          "Aplikasi ini dikembangkan secara gratis oleh tim [bold cyan]SnipGeek[/bold cyan].\n"
                          "Kunjungi [underline bold cyan]https://snipgeek.com/[/underline bold cyan] untuk menemukan berbagai tools, template, dan artikel teknologi lainnya!",
        "milestone.open_prompt": "Buka https://snipgeek.com/ di browser Anda sekarang?",
        "milestone.opened": "[bold green]Membuka SnipGeek di browser Anda... Terima kasih atas dukungannya![/bold green]\n",

        "fmt.1080p": "1080p Full HD (MP4 - Rekomendasi)",
        "fmt.720p": "720p HD (MP4 - Ringan & Cepat)",
        "fmt.2160p": "4K Ultra HD (2160p - MP4)",
        "fmt.best": "Best Video (Kualitas Maksimal Otomatis)",
        "fmt.480p": "480p SD (MP4)",
        "fmt.mp3_320": "MP3 320 kbps (Ultra HQ + Cover Art + ID3)",
        "fmt.mp3_192": "MP3 192 kbps (Standard HQ + Cover Art)",
        "fmt.m4a": "M4A / AAC (Original Audio Stream + Cover)",
        "fmt.flac": "FLAC (Lossless Master Audio)",
        "fmt.wav": "WAV (Uncompressed PCM Studio)",

        "common.na": "N/A",
        "common.gui_warning": "[yellow]Peringatan GUI Dialog:[/yellow] {err}",
        "common.choose_folder_title": "Pilih Folder Utama Penyimpanan",
        "common.kb_interrupt": "\n\n[yellow]Operasi dibatalkan oleh pengguna.[/yellow]",

        "dl.downloading": "[bold yellow]Downloading...",
        "dl.processing": "[bold green]Processing & Converting...",
        "dl.retry_alternate": "koneksi terputus, mencoba ulang via jalur alternatif...",
        "dl.retry_fallback": "masih gagal, mencoba format cadangan (kualitas lebih rendah)...",
        "dl.retry_line": "[yellow]↻[/yellow] {msg}",
        "dl.item_ok": "[bold green]  ✓ {i:02d}/{total}[/bold green] {title}",
        "dl.item_fail": "[bold red]  ✗ {i:02d}/{total}[/bold red] {title} [dim]— {err}[/dim]",
        "dl.retry_item": "[yellow]  ↻ {i:02d}/{total}[/yellow] {title} [dim]— {msg}[/dim]",

        "pf.ffmpeg_missing": "\n[!] FFmpeg tidak terdeteksi di sistem atau folder internal.",
        "pf.ffmpeg_downloading": "[*] Memulai auto-download FFmpeg portable (~90MB)... Mohon tunggu...",
        "pf.ffmpeg_progress": "\r -> Mengunduh FFmpeg: {pct}% [{read}MB / {total}MB]",
        "pf.ffmpeg_extracting": "\n[*] Mengekstrak FFmpeg binary ke folder internal...",
        "pf.ffmpeg_done": "[✓] FFmpeg berhasil dipasang secara portabel!",
        "pf.ffmpeg_failed": "\n[X] Gagal mendownload/mengekstrak FFmpeg: {err}",
        "pf.python_old": "[X] Versi Python terlalu lama: {ver}. Butuh Python >= 3.9",
        "pf.pip_installing": "[*] Menginstall paket Python yang dibutuhkan ({pkgs})...",
        "pf.pip_done": "[✓] Paket dependensi berhasil dipasang!",
        "pf.ffmpeg_not_found": "[X] FFmpeg dibutuhkan tetapi tidak ditemukan.",
    },
}

_lang = "id"


def _detect_lang():
    """Deteksi bahasa dari locale sistem; default 'en' bila bukan 'id*'."""
    try:
        loc = (locale.getdefaultlocale() or ("", ""))[0] or ""
    except Exception:
        loc = ""
    return "id" if str(loc).lower().startswith("id") else "en"


def init(config_path):
    """Baca 'language' dari config.json (dipanggil sebelum preflight import)."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        set_language(data.get("language", "auto"))
    except Exception:
        set_language("auto")


def set_language(lang):
    """'id' | 'en' | 'auto' (auto = deteksi locale sistem)."""
    global _lang
    if lang == "auto":
        lang = _detect_lang()
    _lang = "id" if lang == "id" else "en"


def get_language():
    return _lang


def t(key, **kw):
    """Ambil string terjemahan dengan fallback id -> en -> key itu sendiri."""
    s = _STRINGS.get(_lang, {}).get(key)
    if s is None:
        s = _STRINGS["id"].get(key) or _STRINGS["en"].get(key) or key
    if kw:
        try:
            return s.format(**kw)
        except Exception:
            return s
    return s
