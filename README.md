# ⚡ Mini YouTube Downloader (v1.0.0)

Aplikasi downloader YouTube & konverter audio mandiri, super ringan, dan ramah pemula untuk Windows.  
*Crafted with ❤️ by [SnipGeek](https://snipgeek.com/)*

---

## 🚀 Cara Menggunakan (Hanya 1 Langkah!)

Cukup **klik ganda (double-click)** pada file:
```text
⚡ run.bat
```

> **Catatan Pengguna Baru**:
> - Pastikan laptop sudah terinstall **Python 3.8+** (dengan centang *"Add Python to PATH"*).
> - Seluruh dependensi dan engine konverter audio (FFmpeg) akan dipasang otomatis saat pertama kali dibuka!

---

## 📁 Lokasi Hasil Unduhan

Hasil unduhan Anda akan otomatis dipisahkan secara rapi di dalam folder `downloads/`:
- 🎬 **Video (MP4 4K / 1080p / 720p)** ➔ Masuk ke `downloads/video/`
- 🎵 **Audio (MP3 320k / M4A / FLAC)** ➔ Masuk ke `downloads/audio/`
- 📃 **Playlist** ➔ Paste URL playlist, semua item tersimpan dalam subfolder sesuai nama playlist (contoh: `downloads/audio/Nama Playlist/01 - Lagu.mp3`). Khusus playlist berisi >20 item, muncul konfirmasi dulu. Item yang gagal otomatis dicoba ulang dengan 3 strategi: jalur normal ➔ client alternatif ➔ format cadangan (kualitas lebih rendah).

---

## ✨ Fitur Unggulan

1. **Download Playlist 📃**: Paste URL playlist, semua item otomatis diunduh ke subfolder sesuai nama playlist (MP3/M4A/FLAC/WAV/MP4).
2. **Kualitas Audio Maksimal (MP3 320 kbps)**: Dilengkapi Cover Art Thumbnail dan ID3 Metadata otomatis.
3. **Folder Management**: Menu 1-klik untuk langsung membuka folder file di Windows Explorer.
4. **Bypass Proteksi YouTube**: Ekstraksi metadata instan anti-lag & anti-bot check.

---

## 🔁 Versi & Rollback

Proyek ini menggunakan Git dengan tag versi sebagai titik aman:

- Lihat riwayat commit: `git log --oneline`
- Kembali ke versi stabil terakhir: `git checkout v1.0.0`
- Batalkan commit terakhir: `git revert HEAD`
- Lihat status file berubah: `git status`

---

## 🌐 Tentang Pengembang
Temukan berbagai tools produktivitas, template, dan artikel teknologi lainnya di:  
🔗 **[https://snipgeek.com/](https://snipgeek.com/)**
