import os
import re
import time
import urllib.parse
import yt_dlp
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn, DownloadColumn

_console = Console(force_terminal=True, legacy_windows=False)

# yt-dlp embeds raw ANSI color codes in error strings; strip them for clean display
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

def sanitize_youtube_url(url: str) -> str:
    """Strip playlist and tracking noise from YouTube URLs to speed up extraction and prevent bot triggers"""
    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
        if "youtube.com" in parsed.netloc:
            qs = urllib.parse.parse_qs(parsed.query)
            if "v" in qs:
                return f"https://www.youtube.com/watch?v={qs['v'][0]}"
        elif "youtu.be" in parsed.netloc:
            video_id = parsed.path.lstrip("/").split("/")[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
    except Exception:
        pass
    return url

def detect_playlist(url: str) -> dict:
    """Classify a YouTube URL by playlist presence.

    Returns:
        {'kind': 'playlist_only', 'playlist_url': ...}  - pure /playlist?list=... URL
        {'kind': 'both', 'video_url': ..., 'playlist_url': ...} - watch URL that also carries list=
        {'kind': 'video_only', 'video_url': ...}        - plain video, legacy behavior
    """
    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        list_id = qs.get("list", [None])[0]
        is_watch = "youtube.com" in parsed.netloc and parsed.path == "/watch"
        is_short = "youtu.be" in parsed.netloc
        is_playlist_page = "youtube.com" in parsed.netloc and parsed.path == "/playlist"

        if is_playlist_page and list_id:
            return {"kind": "playlist_only",
                    "playlist_url": f"https://www.youtube.com/playlist?list={list_id}"}
        if (is_watch or is_short) and list_id:
            video_url = sanitize_youtube_url(url)
            return {"kind": "both", "video_url": video_url,
                    "playlist_url": f"https://www.youtube.com/playlist?list={list_id}"}
    except Exception:
        pass
    return {"kind": "video_only", "video_url": sanitize_youtube_url(url)}

def is_channel_url(url: str) -> bool:
    """Detect channel/homepage URLs that are neither a video nor a playlist.

    These must be rejected early: yt-dlp resolves every video on a channel
    (potentially hundreds), which looks like an endless spinner.
    """
    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
        if "youtube.com" not in parsed.netloc and "youtu.be" not in parsed.netloc:
            return False
        path = parsed.path
        if path in ("", "/"):
            return True  # bare homepage
        return path.startswith(("/@", "/channel/", "/c/", "/user/"))
    except Exception:
        return False

class YTDownloader:
    def __init__(self, config_manager, ffmpeg_dir=None):
        self.cfg = config_manager
        self.ffmpeg_dir = ffmpeg_dir

    def sanitize_title(self, title):
        """Sanitize a title into a safe, Windows-friendly filesystem name.

        - Replace forbidden Windows chars (\\ / * ? : \" < > |) with '-' instead of removing,
          so dates like '7/4/2004' stay readable as '7-4-2004'.
        - Collapse duplicate whitespace, strip trailing dots/spaces (Windows forbids them).
        - Cap length to 120 chars to stay well under Windows MAX_PATH (260).
        - Note: '%' is NOT escaped here; it is escaped centrally in download()
          just before building the yt-dlp output template.
        """
        if not title:
            return "untitled"
        title = re.sub(r'[\\/*?:"<>|]', "-", title)
        title = re.sub(r"\s{2,}", " ", title).strip()
        title = title.rstrip(". ")
        title = title[:120].rstrip(". ")
        return title or "untitled"

    def cookies_browser_setting(self):
        """Browser name whose cookies yt-dlp should reuse (empty = disabled). Read live from config."""
        return (self.cfg.get("cookies_browser", "") or "").strip().lower()

    @staticmethod
    def _format_selectors(format_type, format_fallback=False):
        """Return (format_selector, merge_format) for yt-dlp.

        format_fallback=True swaps the normal selector for a progressive
        single-file ladder: stream formats are fragile (DASH merges, separate
        CDN nodes), while progressive files are the most robust fallback.
        """
        is_audio = format_type.startswith('mp3') or format_type in ['m4a', 'flac', 'wav']
        if is_audio:
            return ('best/bestaudio' if format_fallback else 'bestaudio/best'), None

        merge = 'mp4'
        if format_type == 'best':
            return ('best/bestvideo+bestaudio/best' if format_fallback
                    else 'bestvideo+bestaudio/best'), merge
        if format_type.endswith('p'):
            height = format_type.replace('p', '')
            if format_fallback:
                return f'best[height<={height}]/best[height<={height}]/best', merge
            return f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best', merge
        return ('best/bestvideo+bestaudio/best' if format_fallback
                else 'bestvideo+bestaudio/best'), merge

    def _get_base_opts(self, fallback_client=False):
        opts = {
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'force_ipv4': True,
            # Resilience: retry transient drops ("bytes read / more expected")
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 30,
            # Chunked download so a dropped connection only harms one chunk, not the whole stream
            'http_chunk_size': 10 * 1024 * 1024,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Enable yt-dlp's JS challenge solving (PO Token generation) via node.
            # Without this, YouTube truncates streams (~64KB) and hides formats.
            'js_runtimes': {'node': {}},
        }
        if fallback_client:
            # Rescue strategy: tv_embedded + PO Token (js_runtimes above) is
            # currently the only combo YouTube serves untruncated streams
            # through when ios/android/web streams get SABR-truncated.
            opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['tv_embedded']
                }
            }
        else:
            opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['ios', 'android', 'web']
                }
            }
        if self.cookies_browser_setting():
            opts['cookiesfrombrowser'] = (self.cookies_browser_setting(), None, None, None)
        if self.ffmpeg_dir:
            opts['ffmpeg_location'] = self.ffmpeg_dir
        return opts

    def get_video_info(self, url):
        """Extract video metadata cleanly and fast"""
        clean_url = sanitize_youtube_url(url)
        ydl_opts = self._get_base_opts()
        ydl_opts.update({
            'extract_flat': False,
        })
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            return info, clean_url

    def get_playlist_info(self, playlist_url):
        """Fast flat extraction of a playlist: title + entries (id/title only)."""
        ydl_opts = self._get_base_opts()
        ydl_opts.update({
            'extract_flat': 'in_playlist',
            'noplaylist': False,
        })
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
        title = info.get('title') or 'Playlist'
        entries = [e for e in (info.get('entries') or []) if e and e.get('id')]
        return title, entries

    def _clear_partial_files(self, target_dir, name_prefix):
        """Remove stale yt-dlp temp files (.part/.ytdl) so a retry starts a clean download."""
        try:
            for f in os.listdir(target_dir):
                if f.startswith(name_prefix) and (f.endswith('.part') or f.endswith('.ytdl') or '.part-' in f):
                    os.remove(os.path.join(target_dir, f))
        except Exception:
            pass

    def download_playlist(self, playlist_url, format_type, entries, playlist_title=None):
        """Download every playlist entry one-by-one via self.download().

        All files go into a subfolder named after the playlist (when playlist_title given).
        Numbered titles (01 - Song ...) keep files sorted in Explorer.
        A transiently failed entry is retried once before being reported; the batch never aborts.
        Returns (success_files, failed_list, target_dir).
        """
        is_audio = format_type.startswith('mp3') or format_type in ['m4a', 'flac', 'wav']
        subfolder = self.sanitize_title(playlist_title) if playlist_title else None
        target_dir = self.cfg.get_target_dir(is_audio=is_audio, subfolder=subfolder)
        total = len(entries)
        success_files, failed_list = [], []

        # Retry ladder: normal → alternate client → progressive fallback format.
        # Each tuple is (kwargs, message shown when THIS strategy fails).
        strategies = [
            ({}, "koneksi terputus, mencoba ulang via jalur alternatif..."),
            ({'fallback_client': True}, "masih gagal, mencoba format cadangan (kualitas lebih rendah)..."),
            ({'format_fallback': True}, None),
        ]

        for i, entry in enumerate(entries, 1):
            entry_id = entry.get('id')
            entry_title = entry.get('title') or entry_id
            numbered_title = f"{i:02d} - {entry_title}"
            video_url = f"https://www.youtube.com/watch?v={entry_id}"

            out_file = None
            last_err = None
            for strat, fail_msg in strategies:
                try:
                    out_file, _, _ = self.download(
                        video_url, format_type=format_type,
                        title=numbered_title, video_id=entry_id,
                        subfolder=subfolder, **strat,
                    )
                    break
                except Exception as e:
                    last_err = ANSI_RE.sub('', str(e))
                    if fail_msg:
                        self._clear_partial_files(target_dir, f"{self.sanitize_title(numbered_title)} [")
                        _console.print(f"[yellow]  ↻ {i:02d}/{total}[/yellow] {entry_title} [dim]— {fail_msg}[/dim]")
                        time.sleep(3)

            if out_file:
                success_files.append(out_file)
                _console.print(f"[bold green]  ✓ {i:02d}/{total}[/bold green] {entry_title}")
            else:
                failed_list.append((entry_title, last_err))
                _console.print(f"[bold red]  ✗ {i:02d}/{total}[/bold red] {entry_title} [dim]— {last_err}[/dim]")

        return success_files, failed_list, target_dir

    def download_with_fallback(self, url, format_type="1080p", title=None, video_id=None, subfolder=None):
        """Single-download version of the retry ladder used by download_playlist.

        Ladder: normal → alternate client → progressive fallback format.
        Returns (out_file, target_dir); raises the last error when all fail.
        """
        strategies = [
            ({}, "mencoba ulang via jalur alternatif..."),
            ({'fallback_client': True}, "mencoba format cadangan (kualitas lebih rendah)..."),
            ({'format_fallback': True}, None),
        ]
        last_err = None
        for strat, fail_msg in strategies:
            try:
                out_file, _, target_dir = self.download(
                    url, format_type=format_type,
                    title=title, video_id=video_id, subfolder=subfolder, **strat,
                )
                return out_file, target_dir
            except Exception as e:
                last_err = e
                if fail_msg:
                    _console.print(f"[yellow]↻[/yellow] {fail_msg}")
                    time.sleep(3)
        raise last_err

    def download(self, url, format_type="1080p", title=None, video_id=None, subfolder=None,
                 fallback_client=False, format_fallback=False):
        """
        format_type options:
        Video: '2160p', '1440p', '1080p', '720p', '480p', 'best'
        Audio: 'mp3_320', 'mp3_192', 'm4a', 'flac', 'wav'
        """
        clean_url = sanitize_youtube_url(url)
        is_audio = format_type.startswith('mp3') or format_type in ['m4a', 'flac', 'wav']

        # Auto-route to downloads/audio or downloads/video (inside subfolder, e.g. playlist name)
        target_dir = self.cfg.get_target_dir(is_audio=is_audio, subfolder=subfolder)

        # Escape '%' for the yt-dlp output template: folder part and literal title
        # separately, then join with the tokens yt-dlp fills in itself.
        dir_for_tmpl = target_dir.replace("%", "%%")
        if title is not None:
            # Use a pre-sanitized literal title so yt-dlp's template never sees
            # forbidden Windows chars; only %(ext)s is left for yt-dlp to fill.
            clean_title = self.sanitize_title(title)
            id_token = video_id if video_id else '%(id)s'
            outtmpl = os.path.join(dir_for_tmpl, f"{clean_title.replace('%', '%%')} [{id_token}].%(ext)s")
        else:
            outtmpl = os.path.join(dir_for_tmpl, '%(title)s [%(id)s].%(ext)s')

        # Rich Progress Bar Setup
        progress = Progress(
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=40, style="grey37", complete_style="bold green"),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
        )

        task_id = None

        def ytdl_progress_hook(d):
            nonlocal task_id
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                if task_id is None:
                    task_id = progress.add_task("[bold yellow]Downloading...", total=total)
                else:
                    progress.update(task_id, completed=downloaded, total=total)
            elif d['status'] == 'finished':
                if task_id is not None:
                    progress.update(task_id, description="[bold green]Processing & Converting...")

        ydl_opts = self._get_base_opts(fallback_client=fallback_client)
        ydl_opts.update({
            'outtmpl': outtmpl,
            'progress_hooks': [ytdl_progress_hook],
        })

        ydl_opts['format'], merge_format = self._format_selectors(format_type, format_fallback)
        if merge_format:
            ydl_opts['merge_output_format'] = merge_format

        if is_audio:
            # WAV tidak mendukung embed cover art/thumbnail (memicu error yt-dlp).
            # Khusus untuk WAV: matikan writethumbnail & EmbedThumbnail.
            supports_thumbnail = format_type != 'wav'
            if supports_thumbnail:
                ydl_opts['writethumbnail'] = True

            postprocessors = []

            if format_type == 'mp3_320':
                postprocessors.append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                })
            elif format_type == 'mp3_192':
                postprocessors.append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                })
            elif format_type == 'm4a':
                postprocessors.append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                    'preferredquality': 'best',
                })
            elif format_type == 'flac':
                postprocessors.append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'flac',
                })
            elif format_type == 'wav':
                postprocessors.append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                })

            # Embed metadata (tag) — aman untuk semua format audio
            postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})

            # Embed thumbnail/cover art hanya pada format yang mendukungnya
            if supports_thumbnail:
                postprocessors.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})

            ydl_opts['postprocessors'] = postprocessors

        with progress:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                
                if is_audio:
                    base_no_ext = os.path.splitext(downloaded_file)[0]
                    if format_type.startswith('mp3'):
                        downloaded_file = base_no_ext + ".mp3"
                    elif format_type == 'm4a':
                        downloaded_file = base_no_ext + ".m4a"
                    elif format_type == 'flac':
                        downloaded_file = base_no_ext + ".flac"
                    elif format_type == 'wav':
                        downloaded_file = base_no_ext + ".wav"
                        
                return downloaded_file, info, target_dir
