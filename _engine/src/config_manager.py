import os
import json
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENGINE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ROOT_DOWNLOAD_DIR = str(BASE_DIR / "downloads")

class ConfigManager:
    def __init__(self, config_file="config.json"):
        self.config_path = ENGINE_DIR / config_file
        self.defaults = {
            "root_download_dir": DEFAULT_ROOT_DOWNLOAD_DIR,
            "last_resolution": "1080p",
            "last_format_mode": "video",
            "audio_format": "mp3",
            "download_count": 0,
            "remember_choice": True,
            "cookies_browser": ""
        }
        self.config = self.load()

    def load(self):
        if not self.config_path.exists():
            self.save(self.defaults)
            return self.defaults.copy()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in self.defaults.items():
                    if k not in data:
                        data[k] = v
                # Normalize root download dir
                if "Users" in data.get("root_download_dir", "") and "mini-YT-Downloader" not in data.get("root_download_dir", ""):
                    data["root_download_dir"] = DEFAULT_ROOT_DOWNLOAD_DIR
                    self.save(data)
                return data
        except Exception:
            return self.defaults.copy()

    def save(self, data=None):
        if data:
            self.config = data
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Error saving config: {e}]")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def increment_download_count(self):
        count = self.get("download_count", 0) + 1
        self.set("download_count", count)
        return count

    def get_root_download_dir(self):
        d = self.config.get("root_download_dir", DEFAULT_ROOT_DOWNLOAD_DIR)
        Path(d).mkdir(parents=True, exist_ok=True)
        return d

    def set_root_download_dir(self, new_dir):
        self.set("root_download_dir", str(new_dir))

    def get_target_dir(self, is_audio=False, subfolder=None):
        """Route to downloads/audio or downloads/video, optionally inside a named subfolder (e.g. playlist name)"""
        root = Path(self.get_root_download_dir())
        sub = root / ("audio" if is_audio else "video")
        if subfolder:
            clean = str(subfolder).strip()
            if clean in (".", ".."):
                clean = ""
            if clean:
                sub = sub / clean
        sub.mkdir(parents=True, exist_ok=True)
        return str(sub)

    def open_download_folder(self, target_folder=None):
        """Open download folder in Windows Explorer"""
        folder = target_folder or self.get_root_download_dir()
        try:
            os.startfile(folder)
        except Exception:
            subprocess.Popen(f'explorer "{folder}"', shell=True)
