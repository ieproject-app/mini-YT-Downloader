# ⚡ Mini YouTube Downloader (v1.2.0)

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

## 🔑 Gemini API Key (Opsional)

Fitur **✂️ Potong per Surah/Chapter (murottal Juz Amma)** memakai AI
[Google Gemini](https://deepmind.google/technologies/gemini/) untuk
mendeteksi batas surah — baik verifikasi surah yang "hilang timestamp" pada
video ber-chapter, maupun deteksi **penuh dari audio** untuk video murottal
tanpa chapter.

**Tanpa API key, aplikasi tetap 100% normal** — semua fitur unduh
video/audio/playlist jalan seperti biasa. Key **hanya** dipakai saat Anda
memilih opsi potong per surah.

### Cara mendapatkan API key (gratis, free tier)
1. Buka **https://aistudio.google.com/apikey** dan login dengan akun Google Anda.
2. Klik **“Create API key”** → pilih project (atau biarkan default) → key akan muncul.
3. Klik **Copy** untuk menyalin key (formatnya mirip `AIzaSy...`).

### Cara memasukkan key ke aplikasi
**Lewat menu (paling mudah):**
1. Jalankan `run.bat` — saat pertama kali dibuka, aplikasi menawarkan memasang key.
2. Atau ketik `S` (Settings) → pilih menu **[6] Gemini API Key** → pilih [1] Paste key, [2] buka halaman key, atau [3] buka tutorial blog.
3. Status berubah menjadi *"1 key aktif"* di baris status.

> 📖 **Panduan bergambar langkah demi langkah** tersedia di blog SnipGeek:
> [https://snipgeek.com/](https://snipgeek.com/) *(tautan artikel tutorial API key)*

**Manual (opsional):** salin file `.env.example` menjadi `.env` di folder yang
sama, lalu isi:
```dotenv
GEMINI_API_KEYS=AIzaSy...
```
Anda boleh mengisi lebih dari satu key (dipisah koma) — aplikasi memakai
round-robin untuk menghindari batas kuota free tier.

### ⚠️ Privasi & keamanan
- Key disimpan **lokal** di file `.env` di folder project — **tidak pernah
  di-upload**, tidak dikirim ke server lain (selain request langsung ke API
  Google Gemini), dan **tidak ikut ter-commit ke GitHub** (sudah diabaikan
  `.gitignore`).
- Jangan pernah membagikan key Anda ke orang lain.
- Kuota free tier Google bersifat harian & per-key. Bila muncul pesan
  *quota exceeded*, tambahkan key baru atau tunggu keesokan harinya.

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
5. **Potong per Chapter/Surah ✂️ (v1.1.0 + auto-detect)**: Video murottal Juz (ber-chapter ATAU tanpa chapter) bisa langsung dipotong jadi **file MP3 per surah**. Butuh **Gemini API key** (opsional, free tier — lihat [🔑 Gemini API Key](#-gemini-api-key-opsional)). Ada 2 jalur:
   - **Ber-chapter**: deteksi chapter dari metadata, verifikasi surah yang "hilang timestamp" via Gemini, skip Opening, output rapi `downloads/audio/<Judul>/NN - Surah X.mp3`.
   - **Tanpa chapter** (bila judul/channel mengarah ke murottal Juz): transkripsi word-level via Gemini (`gemini-3.5-transcribe`) lalu petakan kata→batas surah secara presisi, fallback ke sweep audio per-chunk. File sumber mentah otomatis dihapus setelah dipotong.

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
