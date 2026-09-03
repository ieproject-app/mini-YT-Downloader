import os
import sys
import shutil
import subprocess
import zipfile
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENGINE_DIR = Path(__file__).resolve().parent.parent
BIN_DIR = ENGINE_DIR / "bin"
FFMPEG_EXE = BIN_DIR / "ffmpeg.exe"
FFPROBE_EXE = BIN_DIR / "ffprobe.exe"

FFMPEG_WINDOWS_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

def is_ffmpeg_available():
    # 1. Check internal _engine/bin/
    if FFMPEG_EXE.exists():
        return str(BIN_DIR)
    # 2. Check system PATH
    if shutil.which("ffmpeg"):
        return "system"
    return None

def download_and_extract_ffmpeg():
    print("\n[!] FFmpeg tidak terdeteksi di sistem atau folder internal.")
    print("[*] Memulai auto-download FFmpeg portable (~90MB)... Mohon tunggu...")
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = BIN_DIR / "ffmpeg_temp.zip"
    
    try:
        def reporthook(blocknum, blocksize, totalsize):
            read = blocknum * blocksize
            if totalsize > 0:
                percent = min(100, read * 100 // totalsize)
                sys.stdout.write(f"\r -> Mengunduh FFmpeg: {percent}% [{read//(1024*1024)}MB / {totalsize//(1024*1024)}MB]")
                sys.stdout.flush()

        urllib.request.urlretrieve(FFMPEG_WINDOWS_URL, zip_path, reporthook)
        print("\n[*] Mengekstrak FFmpeg binary ke folder internal...")
        
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
            
        print("[✓] FFmpeg berhasil dipasang secara portabel!")
        return str(BIN_DIR)
    except Exception as e:
        print(f"\n[X] Gagal mendownload/mengekstrak FFmpeg: {e}")
        return None

def ensure_dependencies():
    if sys.version_info < (3, 8):
        print(f"[X] Versi Python terlalu lama: {sys.version}. Butuh Python >= 3.8")
        sys.exit(1)

    required = ["yt_dlp", "rich", "InquirerPy"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"[*] Menginstall paket Python yang dibutuhkan ({', '.join(missing)})...")
        req_file = BASE_DIR / "requirements.txt"
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
        print("[✓] Paket dependensi berhasil dipasang!")

    ffmpeg_status = is_ffmpeg_available()
    if not ffmpeg_status:
        ffmpeg_status = download_and_extract_ffmpeg()

    if ffmpeg_status and ffmpeg_status != "system":
        os.environ["PATH"] = str(BIN_DIR) + os.pathsep + os.environ.get("PATH", "")

    return True

if __name__ == "__main__":
    ensure_dependencies()
