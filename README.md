# 🎙️ Sarvam VideoDubber
### AI-Powered Multi-Language Video Dubbing — Built at Sarvam BuildIn' Hours Hackathon

> *"Breaking language barriers in Indian video content — one dub at a time."*

---

## 🧠 What is this?

**Sarvam VideoDubber** is an AI-powered video dubbing web application that automatically transcribes, translates, and re-voices any video into Indian languages — entirely using Sarvam AI's native speech and language stack.

Upload a video in any language. Get back a fully dubbed version in Kannada, Hindi, Tamil, Telugu, Malayalam, or 6 more Indian languages — with synchronized audio, in under 3 minutes.

This project started as **VideoDubber**, an open-source multilingual dubbing pipeline built earlier using Whisper (OpenAI) + Helsinki-NLP translation + Edge-TTS (Microsoft). During **Sarvam BuildIn' Hours**, the entire AI core was rebuilt — replacing every non-Indian component with Sarvam AI's own models — making it the first fully Sarvam-native video dubbing pipeline.

---

## 🎯 Problem Statement

India has 22 official languages and over 1.4 billion people — yet most AI-generated video content is locked in English or Hindi. Regional language speakers, especially Kannada, Tamil, Telugu, and Malayalam users, are consistently underserved by mainstream AI dubbing tools.

Creators, educators, and businesses need a way to reach regional audiences without re-recording content from scratch. Sarvam VideoDubber solves this by automating the entire dubbing pipeline using India's own AI infrastructure.

---

## ⚡ What Was Built at the Hackathon

| Component | Before (Old Stack) | After (Sarvam-Native) |
|---|---|---|
| 🎤 Speech-to-Text | OpenAI Whisper | **Saaras v3** |
| 🌐 Translation | Helsinki-NLP / NLLB | **Sarvam-Translate v1** |
| 🔊 Text-to-Speech | Microsoft Edge-TTS | **Bulbul v3** |
| 🎬 Video Mux | FFmpeg | FFmpeg (unchanged) |
| 🖥️ Interface | CLI only | **Streamlit Web App** |

Every AI component in the pipeline was swapped to Sarvam's own models in a single 6-hour build session.

---

## 🛠️ Tools & Technologies Used

### Sarvam AI APIs
| API | Model | Role |
|---|---|---|
| Speech-to-Text | `saaras:v3` | Transcribes spoken audio from video with chunk-level timestamps |
| Translation | `sarvam-translate:v1` | Translates transcribed text to target Indian language |
| Text-to-Speech | `bulbul:v3` | Synthesises natural-sounding dubbed audio in target language |

### Python Libraries
| Library | Purpose |
|---|---|
| `sarvamai` | Official Sarvam AI Python SDK |
| `streamlit` | Web application UI |
| `python-dotenv` | Secure API key loading from `.env` |
| `pydub` | Audio processing utilities |

### System Tools
| Tool | Purpose |
|---|---|
| `ffmpeg` | Audio extraction from video, audio track assembly, final video mux |
| `ffprobe` | Video/audio duration detection |

### Development Environment
- **Language:** Python 3.13
- **Package Manager:** Anaconda
- **IDE:** Visual Studio Code
- **OS:** macOS (Apple Silicon M-chip)

---

## 🏗️ Pipeline Architecture

```
[Input Video]
      │
      ▼
┌─────────────────────────────────┐
│  Step 1 — FFmpeg Audio Extract  │
│  • Mono, 16kHz WAV              │
│  • Strips video, keeps audio    │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Step 2 — Saaras v3 (STT)       │
│  • Splits audio into 25s chunks │
│  • Transcribes each chunk       │
│  • Returns text + timestamps    │
│  • Merges with global offsets   │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Step 3 — Sarvam-Translate v1   │
│  • Translates each segment      │
│  • Preserves timestamps         │
│  • Supports 11 Indian languages │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Step 4 — Bulbul v3 (TTS)       │
│  • Synthesises each segment     │
│  • 30+ natural Indian voices    │
│  • 24kHz high-quality WAV       │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Step 5 — FFmpeg Mux            │
│  • Positions each audio segment │
│    at its original timestamp    │
│  • Stitches to original video   │
│  • Outputs final dubbed MP4     │
└────────────────┬────────────────┘
                 │
                 ▼
      [Dubbed Output Video]
```

---

## 🌍 Supported Languages

| Language Code | Language | Script |
|---|---|---|
| `kn-IN` | Kannada | ಕನ್ನಡ |
| `hi-IN` | Hindi | हिंदी |
| `ta-IN` | Tamil | தமிழ் |
| `te-IN` | Telugu | తెలుగు |
| `ml-IN` | Malayalam | മലയാളം |
| `mr-IN` | Marathi | मराठी |
| `bn-IN` | Bengali | বাংলা |
| `gu-IN` | Gujarati | ગુજરાતી |
| `pa-IN` | Punjabi | ਪੰਜਾਬੀ |
| `od-IN` | Odia | ଓଡ଼ିଆ |
| `en-IN` | English (Indian) | English |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+ (Anaconda recommended)
- FFmpeg installed (`brew install ffmpeg` on Mac)
- Sarvam AI API key from [dashboard.sarvam.ai](https://dashboard.sarvam.ai)

### Installation

```bash
# 1. Enter project folder
cd sarvam-videodubber

# 2. Install dependencies
pip install -r requirements.txt --break-system-packages

# 3. Set up API key
cp .env.example .env
# Edit .env → SARVAM_API_KEY=your_actual_key_here

# 4. Verify API connectivity
python sarvam_test.py
```

### Run the Web App

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

### Run via CLI

```bash
# Dub to Kannada (default)
python dub.py your_video.mp4

# Dub to Hindi
python dub.py your_video.mp4 --lang hi-IN

# Specify source language and speaker voice
python dub.py your_video.mp4 --lang ta-IN --source en-IN --speaker ritu

# Full options
python dub.py --help
```

---

## 📁 Project Structure

```
sarvam-videodubber/
├── app.py              # Streamlit web app (upload + multi-language UI)
├── pipeline.py         # Core dubbing pipeline (all 5 steps)
├── dub.py              # CLI entry point
├── sarvam_test.py      # API sanity check (run this first)
├── requirements.txt    # Python dependencies
├── .env.example        # API key template
├── .gitignore          # Excludes .env, videos, audio files
└── README.md           # This file
```

---

## 🎤 Bulbul v3 Speaker Voices

| Voice | Type |
|---|---|
| `shubh` | Male (default) |
| `aditya` | Male |
| `rahul` | Male |
| `rohan` | Male |
| `ritu` | Female |
| `priya` | Female |
| `neha` | Female |
| `pooja` | Female |
| `simran` | Female |
| `kavya` | Female |
| `anushka` | Female |
| `manisha` | Female |

---

## 🔒 Security

- API key is stored only in `.env` — never committed to version control
- `.gitignore` excludes `.env`, all video and audio files
- No user data is stored — all processing happens in temporary directories deleted after each run

---

## 💬 Judge Q&A — Ready Answers

| Question | Answer |
|---|---|
| What existed before today? | Open-source VideoDubber pipeline (Whisper + Edge-TTS + FFmpeg), deployed on Streamlit Cloud, supporting 16 languages |
| What did you build today? | Full swap of STT → Saaras v3, Translation → Sarvam-Translate v1, TTS → Bulbul v3. Plus a complete Streamlit web app with multi-language support |
| Why Kannada first? | Personal and regional gap — most AI tools skip Kannada. Connects to VAANI, my Kannada voice assistant project |
| Can it extend to more languages? | Yes — pipeline is language-agnostic. Swap `target_language_code`, done |
| Why Sarvam over other APIs? | Indian-first stack, better accuracy on Indian accents and code-mixed speech, DPDP-compliant, built for Bharat |

---

## 👨‍💻 Built By

**Kuvalesh C D**
B.E. Computer Science & Engineering (AI)
Ghousia College of Engineering, VTU Bengaluru — CGPA 7.9

- 🐙 GitHub: [kuvaleshcd-hue](https://github.com/kuvaleshcd-hue)
- 📧 Email: kuvaleshcd@gmail.com
- 🌐 Portfolio: [kuvalesh.netlify.app](https://kuvalesh.netlify.app)
- 📱 Phone: +91 73383 74900

---

## 🏆 Hackathon

**Event:** Sarvam BuildIn' Hours — Bangalore
**Date:** August 6, 2026
**Challenge:** Rebuild an existing project using Sarvam AI's native stack
**Result:** First fully Sarvam-native video dubbing pipeline — 11 Indian languages, web UI, CLI, side-by-side preview

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

*Built with ❤️ for Indian language speakers — because every language deserves great content.*
