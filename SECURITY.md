# Security Policy / Kebijakan Keamanan

## Reporting a vulnerability / Melaporkan kerentanan

If you discover a security issue, please open a
[GitHub issue](https://github.com/ieproject-app/mini-YT-Downloader/issues) or
contact the maintainer via [https://labs.snipgeek.com/](https://labs.snipgeek.com/).
Do **not** post API keys or personal data in public issues.

Jika Anda menemukan masalah keamanan, silakan buka
[GitHub issue](https://github.com/ieproject-app/mini-YT-Downloader/issues) atau
hubungi maintainer via [https://labs.snipgeek.com/](https://labs.snipgeek.com/).
Jangan pernah memposting API key atau data pribadi di issue publik.

## What this app does with your data / Apa yang app lakukan dengan data Anda

- **No analytics, no telemetry.** The app collects nothing and phones home to
  nothing. Aplikasi tidak mengumpulkan data apa pun dan tidak mengirim telemetri.
- **YouTube access** happens through `yt-dlp` directly from your machine, only
  when you request a download. Akses YouTube dilakukan langsung oleh `yt-dlp`
  dari mesin Anda, hanya saat Anda meminta unduhan.
- **Gemini API** is called **only** if you configure your own API key, and only
  for the per-surah cut feature (audio snippets of the video you are cutting
  are sent to Google's Gemini API for analysis). Key dan hasilnya tersimpan
  lokal; tanpa key, fitur ini tidak aktif sama sekali.
- **API keys** are stored in a local `.env` file that is git-ignored and never
  uploaded. Key API disimpan lokal di `.env` yang di-ignore git dan tidak
  pernah di-upload.

## Safe usage / Tips penggunaan aman

- Never share your `.env` file or paste API keys into public issues, chats, or
  screenshots. Jangan pernah membagikan file `.env` atau menempelkan API key
  di issue publik, chat, atau screenshot.
- Download and re-use content only where you have the right to do so.
  Unduh dan gunakan ulang konten hanya jika Anda memiliki hak untuk melakukannya.
