# 🎙️ Zivana (formerly Sarvam VideoDubber)
### AI-Powered Multi-Language Video Dubbing & Real-Time Live Speech Translation Platform
*Built with Sarvam AI's Native Stack — Born at the Sarvam BuildIn' Hours Hackathon*

> *"Breaking language barriers in Indian video content and live speech — one dub at a time."*.  

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.42%2B-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Sarvam AI](https://img.shields.io/badge/Sarvam%20AI-Saaras%20%7C%20Translate%20%7C%20Bulbul-7C3AED.svg)](https://dashboard.sarvam.ai)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-5.0%2B-007808.svg?logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE).   

---

## 🧠 What is Zivana?

**Zivana** is a comprehensive, production-ready AI dubbing and real-time speech translation platform built entirely around **Sarvam AI’s native Indian language stack**. It empowers creators, educators, businesses, and broadcasters to transcribe, translate, and re-voice videos or continuous live microphone speech into **11 Indian languages** with natural speech cadence and synchronized timing.

Originally created during **Sarvam BuildIn' Hours** as **Sarvam VideoDubber** (a 6-hour hackathon project that replaced an older OpenAI Whisper + Edge-TTS pipeline with a 100% Sarvam-native stack), the project has since evolved into **Zivana** — featuring a real-time live dubbing teleprompter, Demucs AI background music preservation, timing auto-fit, enterprise authentication (Google OAuth & Email OTP), user processing dashboards, and custom subtitle burning.

---

## 🌟 Complete Feature Overview

### 1. 🎙️ Real-Time Live Dubbing & Subtitles (Live Teleprompter)
* **Continuous Microphone Streaming**: Captures 16 kHz 16-bit mono PCM audio directly from your microphone using `sounddevice` and streaming queues.
* **WebSocket Realtime STT (`saaras:v3-realtime`)**: Streams audio continuously to Sarvam's low-latency speech-to-text engine, emitting instant partial transcripts and final utterances.
* **Instant Utterance Translation (`sarvam-translate:v1`)**: Automatically translates final transcript segments into the target Indian language in near-real-time.
* **Streaming Voice Synthesis (`bulbul:v3`)**: Connects via streaming WebSockets to synthesize natural speech with minimal latency.
* **Live Audio Playback**: Direct, low-latency audio playback through system speakers (powered by macOS CoreAudio `afplay` / `sounddevice`).
* **Live Dual Teleprompter UI**: Built using Streamlit `@st.fragment(run_every="0.5s")`, rendering side-by-side cards for live source transcription and translated subtitles without page reloads.
* **Live Status Pill**: Visual status beacon indicating real-time activity (`Listening 🟢`, `Transcribing 🟡`, `Translating 🟣`, `Dubbing 🔊`).
* **Live Subtitle Stream & Session History**: Displays a rolling history of completed utterances with timestamps.
* **Session Export**: One-click download of the entire live session as a standard SubRip subtitle file (`.srt`) or a formatted text transcript (`.txt`).
* **Dedicated Live CLI**: Standalone terminal client (`python live_pipeline.py`) supporting real-time speech translation with an optional `--mute` flag for subtitles-only mode.

### 2. 📁 Multi-Format Video File Dubbing
* Drag-and-drop or upload video files in **MP4, MKV, MOV, AVI, or WEBM** format.
* **Intelligent Audio Chunking**: Automatically splits long video audio into 25-second segments (with global timestamp offsets) to bypass REST API duration constraints while maintaining perfect synchronization.
* Embedded in-browser video player with instant preview of the uploaded video.

### 3. ▶️ YouTube Video Ingestion & Resolution Selector
* **Direct URL Ingestion**: Paste any YouTube video, Shorts, or custom link (powered by `yt-dlp`).
* **Quality & Resolution Selection**: Choose from `360p`, `480p`, `720p`, `1080p`, or `Best` to balance processing speed, download bandwidth, and visual quality.
* **Live Metadata & Thumbnail Card**: Automatic extraction and display of video titles, duration, and thumbnail images.

### 4. ✂️ Smart Video Trimming
* Precise start timestamp (`-ss`) and end timestamp (`-to`) selectors for both local video files and YouTube clips.
* Dub only the relevant segment of long videos to conserve API quotas and cut processing time down to seconds.

### 5. ⏱️ Intelligent Audio Timing Auto-Fit
* **Natural Cadence Matching**: Automatically stretches or compresses the duration of Bulbul TTS audio segments to fit the exact duration slot of the original speech.
* **Multi-Stage FFmpeg `atempo` Filtering**: Clamped dynamically between 0.5x and 2.0x, with chained filters for extreme ratios to prevent desynchronization, speech overlaps, or awkward gaps.

### 6. 🎵 AI Background Music (BGM) Retention
* **Deep Learning Stem Separation**: Uses Meta's **Demucs** (`mdx_extra` two-stems model) to isolate original background music and ambient sound effects from dialogue.
* **BGM Volume Slider (0.0x – 2.0x)**: Accurately balances the retained musical score behind the newly dubbed voices so background audio never overpowers the dialog.

### 7. 📝 Subtitle Generation & Custom Burning
* **Automated SRT Generation**: Produces standards-compliant `.srt` subtitle files with millisecond-accurate timestamps (`HH:MM:SS,mmm`).
* **Custom Visual Subtitle Styling**:
  * **Font Size**: Adjustable from 10px to 72px.
  * **Font Family**: Select between Arial, Helvetica, and Courier.
  * **Text Color**: Hex color picker for high contrast text.
  * **Background Box**: Custom color picker with semi-transparent backing for legibility.
  * **Screen Placement**: Vertical positioning at `bottom`, `middle`, or `top`.
* **Robust Python Subtitle Burner**: Dual-mode rendering with a resilient OpenCV + Pillow + `pysubs2` fallback engine to guarantee subtitle burn-in even when system FFmpeg lacks `libass`.

### 8. 🖼️ Custom Watermark Overlay
* Burn custom PNG/JPEG logos into the top-right corner of dubbed videos for content protection and creator branding.

### 9. 🌍 Simultaneous Multi-Language Batch Dubbing
* Select one or multiple target Indian languages in a single run.
* The pipeline processes each language sequentially, rendering tabbed results with elapsed processing times, segment counts, and download links.
* **Side-by-Side Comparison**: Synchronized dual video players displaying the original video alongside the newly dubbed and subtitled video.

### 10. 💾 Multi-Asset Downloads & Exports
Every dubbing job generates and exposes direct download buttons for:
* 🎬 **Dubbed MP4 Video** (synchronized dubbed audio + original video).
* 📝 **Dubbed MP4 with Burned Subtitles** (styled burned-in subtitles).
* 🎵 **Standalone Audio Track (.wav)** (24 kHz high-quality audio for podcasts, audiobooks, and radio).
* 💾 **SubRip Subtitle File (.srt)**.
* 📄 **Dual Transcripts** (viewable and copyable source transcript and translated text).

### 11. 🔐 Enterprise Authentication System
* **Premium Glassmorphism UI**: High-end landing and login experience featuring animated floating purple gradient orbs, frosted glass cards, and custom brand logos.
* **Three Flexible Auth Methods**:
  1. **Google OAuth 2.0**: Native single-sign-on using Streamlit 1.42+ (`st.login("google")` / `st.user`) configured via `.streamlit/secrets.toml`.
  2. **Email OTP Verification**: Passwordless login generating 6-digit one-time passcodes dispatched via secure SMTP SSL (`smtp.gmail.com:465`).
  3. **Local Credentials (SQLite)**: Username and password registration with cryptographic SHA-256 password hashing.

### 12. 📊 User Dashboard & Persistent Job History
* **SQLite Database (`history.db`)**: Automatically records every completed dubbing job with video names, language pairs, execution timestamps, and output locations.
* **Persistent Output Storage (`output/`)**: Automatically stores exported video, audio, and subtitle assets permanently on disk.
* **Interactive History Explorer**: Expandable job cards with embedded video player, audio player, and quick re-download links.

### 13. 💻 Command-Line Interface (CLI) Suite
* `dub.py`: Full-featured CLI for batch dubbing local video files with configurable language, voice, and output path flags.
* `live_pipeline.py`: Interactive CLI for real-time microphone speech dubbing and live console subtitles.
* `sarvam_test.py`: Pre-flight sanity test that validates STT, translation, and TTS API connectivity with minimal synthetic audio.

---

## ⚡ Evolution: Hackathon to Zivana

| Feature / Component | Hackathon V1 (Sarvam VideoDubber) | Zivana (Current Version) |
|---|---|---|
| **STT Engine** | Saaras v3 (Batch REST) | **Saaras v3 (Batch) + Saaras v3-Realtime (WebSockets)** |
| **Translation Engine** | Sarvam-Translate v1 | **Sarvam-Translate v1 (Batch + Real-Time Streaming)** |
| **TTS Engine** | Bulbul v3 (24 kHz REST) | **Bulbul v3 (REST + WebSocket Low-Latency Streaming)** |
| **Live Mic Dubbing** | ❌ Not available | **✅ Real-Time Bidirectional Live Dubbing & Teleprompter** |
| **User Authentication** | ❌ None | **✅ Google OAuth 2.0, Email OTP, and SQLite SHA-256** |
| **Dashboard & History** | ❌ None (ephemeral) | **✅ SQLite Persistent History & Output Management** |
| **Timing Synchronization**| Simple audio delays | **✅ Intelligent `atempo` Auto-Fit Time Stretching** |
| **Background Music** | ❌ Stripped | **✅ Demucs AI Vocal Separation + BGM Volume Control** |
| **Subtitle Engine** | Basic SRT generation | **✅ Custom Styled Burn-in (Size/Color/Font/Position) + Python Fallback** |
| **Video Ingestion** | File upload only | **✅ File Upload + YouTube Downloader (Resolution Options) + Video Trimmer** |
| **Output Formats** | Single Dubbed MP4 | **✅ Dubbed MP4, Subtitled MP4, Audio-Only WAV, and SRT** |

---

## 🏗️ System Architecture

### Offline / Batch Video Dubbing Pipeline
```
                    [Input Video: Upload / YouTube URL]
                                     │
                     [Optional: Start/End Video Trim]
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │    FFmpeg Audio Extraction   │
                      │       16 kHz Mono WAV        │
                      └──────────────┬───────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
                 ▼ (Optional)                            ▼
   ┌───────────────────────────┐           ┌───────────────────────────┐
   │         Demucs AI         │           │      Audio Chunking       │
   │  Isolate Vocals & BGM     │           │      25s Max Slices       │
   └─────────────┬─────────────┘           └─────────────┬─────────────┘
                 │                                       │
                 │ BGM Track                             ▼
                 │                         ┌───────────────────────────┐
                 │                         │       Saaras v3 STT       │
                 │                         │   Timed Speech Segments   │
                 │                         └─────────────┬─────────────┘
                 │                                       │
                 │                                       ▼
                 │                         ┌───────────────────────────┐
                 │                         │    Sarvam-Translate v1    │
                 │                         │  Target Language Segments │
                 │                         └─────────────┬─────────────┘
                 │                                       │
                 │                                       ▼
                 │                         ┌───────────────────────────┐
                 │                         │       Bulbul v3 TTS       │
                 │                         │     24 kHz Audio Segs     │
                 │                         └─────────────┬─────────────┘
                 │                                       │
                 │                                       ▼
                 │                         ┌───────────────────────────┐
                 │                         │   Audio Timing Auto-Fit   │
                 │                         │ FFmpeg atempo Compression │
                 │                         └─────────────┬─────────────┘
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │  FFmpeg adelay / amix Mux    │
                      │  Dubbed Speech + Balanced BGM│
                      └──────────────┬───────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
                 ▼                                       ▼
   ┌───────────────────────────┐           ┌───────────────────────────┐
   │   SubRip SRT Generator    │           │  Custom Subtitle Burner   │
   │   Timestamped .srt File   │           │  OpenCV / PIL / FFmpeg    │
   └─────────────┬─────────────┘           └─────────────┬─────────────┘
                 │                                       │
                 ▼                                       ▼
       [Export: .srt & .wav]                   [Dubbed & Subtitled MP4]
```

---

### Real-Time Live Dubbing Architecture
```
 [Microphone Input] ──(16kHz PCM)──▶ [sounddevice Stream]
                                              │
                                              ▼
                        ┌──────────────────────────────────────────┐
                        │      AsyncSarvamAI Streaming Client      │
                        ├──────────────────────────────────────────┤
                        │ 1. Saaras v3-Realtime (WebSocket)        │
                        │    • Real-time partial transcription     │
                        │    • Final utterance segmentation        │
                        │                                          │
                        │ 2. Sarvam-Translate v1                   │
                        │    • Instant utterance translation       │
                        │                                          │
                        │ 3. Bulbul v3 Streaming (WebSocket)       │
                        │    • Low-latency streaming MP3 chunks    │
                        └─────────────────────┬────────────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     │                                                 │
                     ▼                                                 ▼
      ┌─────────────────────────────┐                   ┌─────────────────────────────┐
      │  Live UI Teleprompter       │                   │ Low-Latency Audio Worker    │
      │  • Streamlit @st.fragment   │                   │ • System Speaker Playback   │
      │  • Live Source/Target Cards │                   │ • macOS CoreAudio (afplay)  │
      │  • Rolling Utterance Stream │                   └─────────────────────────────┘
      │  • Live SRT / TXT Export    │
      └─────────────────────────────┘
```

---

## 🌍 Supported Languages

| BCP-47 Code | Language | Native Script | Flag / Emoji |
|---|---|---|---|
| `kn-IN` | **Kannada** | ಕನ್ನಡ | 🟠 |
| `hi-IN` | **Hindi** | हिंदी | 🟢 |
| `ta-IN` | **Tamil** | தமிழ் | 🔵 |
| `te-IN` | **Telugu** | తెలుగు | 🟣 |
| `ml-IN` | **Malayalam** | മലയാളം | 🟡 |
| `mr-IN` | **Marathi** | मराठी | 🔴 |
| `bn-IN` | **Bengali** | বাংলা | 🟤 |
| `gu-IN` | **Gujarati** | ગુજરાતી | ⚪ |
| `pa-IN` | **Punjabi** | ਪੰਜਾਬੀ | 🔶 |
| `od-IN` | **Odia** | ଓଡ଼ିଆ | 🔷 |
| `en-IN` | **English (Indian)**| English | 🏴 |

---

## 🎤 Bulbul v3 Voices

Select from 18 natural, expressive Indian voices:

| Voice | Gender | Characteristic |
|---|---|---|
| `shubh` | Male | Clear, formal, standard narrator (default) |
| `aditya` | Male | Warm, energetic, conversational |
| `rahul` | Male | Professional, documentary style |
| `rohan` | Male | Young, casual, upbeat |
| `amit` | Male | Authoritative, podcast host style |
| `dev` | Male | Deep, resonant voice |
| `karun` | Male | Calm, informative narrator |
| `hitesh` | Male | Expressive, relatable tone |
| `ritu` | Female | Crisp, friendly, broadcast quality |
| `priya` | Female | Gentle, expressive, storyteller |
| `neha` | Female | Modern, dynamic, conversational |
| `pooja` | Female | Warm, articulate, instructional |
| `simran` | Female | Clear, cheerful tone |
| `kavya` | Female | Melodic, soothing narration |
| `ishita` | Female | Professional newsreader tone |
| `shreya` | Female | Natural, energetic delivery |
| `anushka` | Female | Engaging, versatile speaker |
| `manisha` | Female | Refined, formal narrator |

---

## 🛠️ Tech Stack & Requirements

* **Core AI / SDK**: `sarvamai` (official Sarvam AI SDK), supporting `saaras:v3`, `saaras:v3-realtime`, `sarvam-translate:v1`, and `bulbul:v3`.
* **Frontend**: `streamlit >= 1.42.0` (with `@st.fragment` support for real-time teleprompter components).
* **Audio & Video Processing**: `ffmpeg`, `ffprobe`, `pydub`, `sounddevice`, `numpy`.
* **Vocal & Music Separation**: `demucs` (Meta's state-of-the-art hybrid transformer music source separation).
* **YouTube Ingestion**: `yt-dlp`.
* **Subtitle Engine**: `opencv-python`, `pillow`, `pysubs2`.
* **Authentication & Database**: `sqlite3`, `authlib`, `smtplib` (SSL), `hashlib`.

---

## 🚀 Getting Started

### 1. Prerequisites
* **Python 3.9+** (Python 3.10 or 3.11 recommended).
* **FFmpeg**:
  * macOS: `brew install ffmpeg`
  * Ubuntu/Debian: `sudo apt update && sudo apt install ffmpeg`
  * Windows: `winget install Gyan.FFmpeg`
* **Sarvam AI API Key**: Sign up at [dashboard.sarvam.ai](https://dashboard.sarvam.ai) to obtain your API key.

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/kuvaleshcd-hue/my-major-project-.git
cd my-major-project-

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create your `.env` file from the provided template:

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:

```ini
# Required: Sarvam AI API Key
SARVAM_API_KEY=your_actual_sarvam_api_key_here

# Optional: Email OTP Login credentials (requires Gmail App Password)
SMTP_EMAIL="your_email_address@gmail.com"
SMTP_PASSWORD="your_16_character_app_password"
```

*(Optional)* **Google OAuth Setup**:
To enable "Sign in with Google", configure `.streamlit/secrets.toml`:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml`:
```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "your_random_secret_string"

[auth.google]
client_id = "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

### 4. Verify API Connectivity

Run the pre-flight check to test STT, translation, and TTS:

```bash
python sarvam_test.py
```

---

## 💻 How to Run

### Run the Web Application (Streamlit)

```bash
streamlit run app.py
```

The web application will open automatically at `http://localhost:8501`.

1. **Sign In**: Use Google OAuth, Email OTP, or standard username/password.
2. **Choose a Mode**:
   * **📁 Upload Video**: Drop in any video, optionally trim timestamps, select target languages, and click Dub.
   * **▶️ YouTube URL**: Paste any YouTube link, pick resolution, optionally trim, and dub.
   * **🎙️ Live Dubbing & Subtitles**: Select source and target language, click *Start Live Dubbing*, and speak into your microphone.
   * **📊 Dashboard**: View your past dubbing history, play dubbed videos/audio, and re-download assets.

---

### Run via Command-Line Interface (CLI)

#### Batch Video Dubbing (`dub.py`)
```bash
# Dub to Kannada (default)
python dub.py your_video.mp4

# Dub to Hindi with a specific voice
python dub.py your_video.mp4 --lang hi-IN --speaker aditya

# Specify source language and custom output file
python dub.py your_video.mp4 --lang ta-IN --source en-IN --out output/tamil_dub.mp4

# Display help and all supported language codes
python dub.py --help
```

#### Real-Time Microphone Dubbing (`live_pipeline.py`)
```bash
# Live microphone dubbing from English to Kannada with real-time audio playback
python live_pipeline.py --source en-IN --lang kn-IN --speaker shubh

# Live subtitles only (mutes dubbed voice playback)
python live_pipeline.py --source en-IN --lang hi-IN --mute.  
```

---

## 📁 Project Structure

```
.
├── app.py                     # Streamlit web app (Upload, YouTube, Live Dubber & Dashboard tabs)
├── live_pipeline.py           # Real-time WebSocket streaming STT, Translation & TTS engine
├── pipeline.py                # Core batch dubbing pipeline (Demucs, Saaras, Bulbul, FFmpeg mux)
├── dub.py                     # Command-line interface for batch video dubbing
├── db.py                      # SQLite persistence (user accounts and video processing history)
├── login.py                   # Premium login/signup UI (Google OAuth, Email OTP, SQLite credentials)
├── sarvam_test.py             # Diagnostic API test script for STT, Translation & TTS
├── requirements.txt           # Python package dependencies
├── logo.png                   # Brand logo image
├── .env.example               # Environment variables template
├── .gitignore                 # Excludes .env, output assets, caches, databases
├── .streamlit/
│   ├── config.toml            # Streamlit theme & layout configuration
│   └── secrets.toml.example   # Google OAuth configuration template
└── README.md                  # Comprehensive project documentation
```

---

## 🔒 Security & Privacy

* **Strict Key Hygiene**: API keys and secrets are loaded strictly from environment variables (`.env`) or `.streamlit/secrets.toml` — never hardcoded or committed to git.
* **Secure Authentication**: User passwords stored in SQLite are hashed using SHA-256.
* **Clean Session Lifecycles**: Temporary audio chunks and intermediate frames created during processing are safely purged from disk upon task completion.

---

## 👨‍💻 Built By

**Kuvalesh C D**  
B.E. Computer Science & Engineering (Artificial Intelligence)  
Ghousia College of Engineering, VTU Bengaluru — CGPA: 7.9  

* 🐙 **GitHub**: [@kuvaleshcd-hue](https://github.com/kuvaleshcd-hue)
* 📧 **Email**: [kuvaleshcd@gmail.com](mailto:kuvaleshcd@gmail.com)
* 🌐 **Portfolio**: [kuvalesh.netlify.app](https://kuvalesh.netlify.app)
* 📱 **Phone**: +91 73383 74900

---

## 🏆 Hackathon & Origins

* **Event**: Sarvam BuildIn' Hours — Bangalore
* **Original Challenge**: Rebuild an existing open-source video dubber to run 100% natively on Sarvam AI’s models.
* **Result**: Successfully transformed into **Zivana** — the first complete, production-grade video dubbing and real-time live speech translation platform powered by Sarvam AI.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) — free to use, modify, and distribute.

---

<div align="center">
  <b>Built with ❤️ for Indian language speakers — because every language deserves great content.</b>
</div>
