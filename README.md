# ⚡ Mini YouTube Downloader (v1.5.0)

A standalone, super-lightweight YouTube downloader & audio converter for Windows — friendly for beginners.
*Crafted with ❤️ by [SnipGeek](https://snipgeek.com/)*

🌐 **Bahasa Indonesia: [README.id.md](README.id.md)**

---

## 🚀 Install (Online, One Command)

Open **PowerShell** and run:

```powershell
irm https://raw.githubusercontent.com/ieproject-app/mini-YT-Downloader/main/install.ps1 | iex
```

The installer will:
1. Check/install Python prerequisites
2. Download the app to `%LOCALAPPDATA%\MiniYT\app`
3. Create an isolated Python environment + install dependencies
4. Register the **`miniyt`** command (available in any terminal)
5. FFmpeg (~160MB) downloads automatically on first launch of the app

Then just type anywhere:

```text
miniyt
```

> Prefer the classic way? Download the repo and double-click **`run.bat`**
> (portable mode — all data stays inside the repo folder).

## 🔄 Updates

The app checks GitHub (max once per 24 hours) for a new version. When an
update exists it shows **what's new** (changelog) and offers a one-keypress
update — the app closes, the updater runs in the background, and you start
`miniyt` again.

- Manual check anytime: `miniyt update`, or Settings → **[8] Check for Updates**
- Disable auto-check: set `"check_updates": false` in the app's `config.json`
- All releases & changelogs: [Releases page](https://github.com/ieproject-app/mini-YT-Downloader/releases)

> **New user notes**:
> - Python **3.9+** must be installed with *"Add Python to PATH"* checked.
> - FFmpeg (~90MB) is downloaded automatically on first run.

---

## 🔑 Gemini API Key (Optional)

The **✂️ Cut per Surah/Chapter (Juz murottal)** feature uses
[Google Gemini](https://deepmind.google/technologies/gemini/) to detect surah
boundaries — both for verifying "missing timestamp" surahs in chaptered
videos, and for **fully detecting surahs from the audio** in chapter-less
murottal videos.

**Without an API key the app still works 100% normally** — all
video/audio/playlist downloads behave as usual. The key is **only** used when
you choose the per-surah cut option.

### Getting a free API key
1. Open **https://aistudio.google.com/apikey** and sign in with your Google account.
2. Click **"Create API key"** → pick a project (or keep the default) → the key appears.
3. Click **Copy** (it looks like `AIzaSy...`).

### Adding the key to the app
**Via the menu (easiest):**
1. Run `miniyt` (or `run.bat`).
2. On first launch the app offers to set the key. You can also press **`K`**
   at the main screen — it opens the free key page **and** prompts you to
   paste the key right after (a complete bridge).
   Or type `S` (Settings) → **[6] Gemini API Key** for the same menu.
3. The status bar shows *"1 key(s) active"* once set.

**Manual (optional):** copy `.env.example` to `.env` next to the app and fill in:
```dotenv
GEMINI_API_KEYS=AIzaSy...
```
You can add several keys separated by commas — the app rotates them
round-robin to stay within free-tier quotas.

### 🔒 Privacy & security
- Keys are stored **locally** in a `.env` file — **never uploaded**, never
  committed to GitHub (git-ignored), and only ever sent directly to the Google
  Gemini API.
- Never share your key with anyone.
- Google free-tier quotas are daily and per-key. If you see *quota exceeded*,
  add another key or wait for the next day.

---

## 📁 Where Files Are Saved

Downloads are neatly separated inside the downloads folder:
- 🎬 **Video (MP4 4K / 1080p / 720p)** → `video/`
- 🎵 **Audio (MP3 320k / M4A / FLAC)** → `audio/`
- 📃 **Playlist** → paste a playlist URL and every item goes into a subfolder
  named after the playlist (e.g. `audio/My Playlist/01 - Song.mp3`). Playlists
  with >20 items ask for confirmation first. Failed items are retried
  automatically with 3 strategies: normal route → alternate client →
  fallback format (lower quality).

Default locations:
- Installed mode: `%USERPROFILE%\Downloads\MiniYT`
- Portable mode: `<repo>\downloads`

---

## ✨ Features

1. **Playlist Download 📃**: paste a playlist URL — every item downloads into its own subfolder (MP3/M4A/FLAC/WAV/MP4).
2. **Max Audio Quality (MP3 320 kbps)**: automatic Cover Art & ID3 metadata.
3. **Folder Management**: one-click menu to open folders in Windows Explorer.
4. **YouTube Protection Bypass**: instant metadata extraction, anti-lag & anti-bot.
5. **Cut per Chapter/Surah ✂️**: murottal Juz videos (with OR without chapters) can be split into **one MP3 per surah**. Requires a Gemini API key (free tier — see above). Two routes:
   - **Chaptered**: chapters come from metadata; surahs "missing a timestamp" are verified via Gemini; Opening is skipped; tidy output `NN - Surah X.mp3`.
   - **Chapter-less**: word-level transcription (`gemini-3.5-transcribe`) maps recitation words to precise surah boundaries (all 37 Juz Amma surahs verified in testing); falls back to a per-chunk audio sweep. The raw source file is deleted automatically after cutting.
6. **Bilingual UI 🌐**: English & Bahasa Indonesia — asked once at first run, changeable anytime in Settings.

---

## ⚖️ Legal & Fair Use

- This tool is **not affiliated with YouTube or Google**. YouTube is a
  trademark of Google LLC.
- Download content **only for personal use** or where you have the rights to
  do so. Re-uploading or monetizing other people's content without permission
  may violate copyright law and YouTube's Terms of Service.
- You are responsible for how you use this tool.

> 🔄 **Update the app**: simply re-run the install command above — it
> re-downloads the latest version and keeps your settings.

---

## 🔁 Versions & Rollback

The project uses Git tags as safe rollback points:

- See commit history: `git log --oneline`
- Roll back to the last stable version: `git checkout v1.4.1`
- Undo the last commit: `git revert HEAD`
- See changed files: `git status`

---

## 🌐 About the Developer
Find productivity tools, templates, and tech articles at:
🔗 **[https://snipgeek.com/](https://snipgeek.com/)**
