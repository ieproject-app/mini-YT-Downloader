"""
paths.py — Resolusi lokasi runtime mini-YT (portable vs ter-install).

Dua mode:
- PORTABLE (repo dev / zip manual): perilaku lama — config di `_engine/`,
  `.env` di repo root, ffmpeg di `_engine/bin`, downloads di repo root.
  Dipakai saat repo dijalankan lewat run.bat (marker: run.bat ada & tidak
  ada installed.flag).
- INSTALLED (hasil install.ps1): data pengguna dipisah dari program —
  %LOCALAPPDATA%\\MiniYT\\data (config/.env/ffmpeg bin) agar folder program
  tidak pernah ditulisi, dan download default ke ~/Downloads/MiniYT.
  Marker: file `installed.flag` di dalam `_engine/` (ditulis installer).
"""

import os
from pathlib import Path

APP_DIR_NAME = "MiniYT"

_ENGINE_SRC = Path(__file__).resolve().parent
ENGINE_DIR = _ENGINE_SRC.parent          # .../_engine
REPO_ROOT = ENGINE_DIR.parent            # repo root (atau root app ter-install)


def is_installed() -> bool:
    """True bila berjalan dari salinan hasil installer (bukan repo dev)."""
    return (ENGINE_DIR / "installed.flag").exists()


def is_portable() -> bool:
    return not is_installed()


def data_dir() -> Path:
    """Direktori data yang boleh ditulisi (config/.env/bin/log)."""
    if is_installed():
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        d = Path(base) / APP_DIR_NAME / "data"
    else:
        d = ENGINE_DIR  # portable: perilaku lama (config di _engine/)
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return data_dir() / "config.json"


def env_file() -> Path:
    """File .env utama tempat key Gemini disimpan."""
    if is_installed():
        return data_dir() / ".env"
    return REPO_ROOT / ".env"  # portable: perilaku lama (repo root)


def bin_dir() -> Path:
    """Direktori ffmpeg/ffprobe (auto-download bila belum ada)."""
    if is_installed():
        d = data_dir() / "bin"
    else:
        d = ENGINE_DIR / "bin"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_downloads_dir() -> Path:
    if is_installed():
        d = Path.home() / "Downloads" / APP_DIR_NAME
    else:
        d = REPO_ROOT / "downloads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def requirements_file() -> Path:
    return REPO_ROOT / "requirements.txt"
