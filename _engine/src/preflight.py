import os
import sys
import shutil
import subprocess
import zipfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import paths
import i18n
from i18n import t

BIN_DIR = paths.bin_dir()
FFMPEG_EXE = BIN_DIR / "ffmpeg.exe"
FFPROBE_EXE = BIN_DIR / "ffprobe.exe"

FFMPEG_WINDOWS_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

def is_ffmpeg_available():
    # 1. Check internal bin dir
    if FFMPEG_EXE.exists():
        return str(BIN_DIR)
    # 2. Check system PATH
    if shutil.which("ffmpeg"):
        return "system"
    return None

def download_and_extract_ffmpeg():
    print(t("pf.ffmpeg_missing"))
    print(t("pf.ffmpeg_downloading"))
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = BIN_DIR / "ffmpeg_temp.zip"

    try:
        def reporthook(blocknum, blocksize, totalsize):
            read = blocknum * blocksize
            if totalsize > 0:
                percent = min(100, read * 100 // totalsize)
                sys.stdout.write(t("pf.ffmpeg_progress",
                                   pct=percent, read=read // (1024 * 1024),
                                   total=totalsize // (1024 * 1024)))
                sys.stdout.flush()

        urllib.request.urlretrieve(FFMPEG_WINDOWS_URL, zip_path, reporthook)
        print(t("pf.ffmpeg_extracting"))

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.filename.endswith("ffmpeg.exe"):
                    file_info.filename = "ffmpeg.exe"
                    zip_ref.extract(file_info, BIN_DIR)
                elif file_info.filename.endswith("ffprobe.exe"):
                    file_info.filename = "ffprobe.exe"
                    zip_ref.extract(file_info, BIN_DIR)

        if zip_path.exists():
            os.remove(zip_path)

        print(t("pf.ffmpeg_done"))
        return str(BIN_DIR)
    except Exception as e:
        print(t("pf.ffmpeg_failed", err=e))
        return None

def ensure_dependencies():
    if sys.version_info < (3, 9):
        print(t("pf.python_old", ver=sys.version))
        sys.exit(1)

    required = ["yt_dlp", "rich", "requests"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(t("pf.pip_installing", pkgs=", ".join(missing)))
        req_file = paths.requirements_file()
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
        print(t("pf.pip_done"))

    ffmpeg_status = is_ffmpeg_available()
    if not ffmpeg_status:
        ffmpeg_status = download_and_extract_ffmpeg()

    if ffmpeg_status and ffmpeg_status != "system":
        os.environ["PATH"] = str(BIN_DIR) + os.pathsep + os.environ.get("PATH", "")

    return True

if __name__ == "__main__":
    ensure_dependencies()
