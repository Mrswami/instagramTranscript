# 🎙️ Instagram Reel & Post Transcriber (`Instagramtranscript`)

> **Live Web Application**: [https://instagramtranscript.web.app](https://instagramtranscript.web.app)  
> **GitHub Repository**: [https://github.com/Mrswami/instagramTranscript.git](https://github.com/Mrswami/instagramTranscript.git)

An end-to-end Python Media Pipeline, REST API, Streamlit Web Application, and CLI tool that extracts high-quality 192kbps MP3 audio from any Instagram Reel or Post link and distills it into copyable text transcripts, SRT subtitles, WebVTT captions, and structured JSON data using OpenAI's Whisper AI engine.

![CI Pipeline](https://github.com/Mrswami/instagramTranscript/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-ff4b4b?logo=streamlit&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0+-000000?logo=flask&logoColor=white)
![Whisper](https://img.shields.io/badge/OpenAI-Whisper_AI-green?logo=openai&logoColor=white)
![Firebase](https://img.shields.io/badge/Firebase_Hosting-Live-ffca28?logo=firebase&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-purple)


---

## 🌐 Live Web Application

Access the live, high-performance web client instantly:  
👉 **[https://instagramtranscript.web.app](https://instagramtranscript.web.app)**

The web client features a dark-mode glassmorphism design built for desktop and mobile devices. It connects directly to local or cloud-hosted Python REST backend instances to extract media and process speech-to-text transcriptions in real time.

---

## ✨ Key Features

- 🔗 **Instagram Video Audio Extraction**: Seamlessly extracts audio streams from short or long (3+ minutes) Instagram Reel or Post URLs.
- 🎧 **High-Quality MP3 Encoding**: Converts video tracks into standardized 192kbps 44.1kHz MP3 files using FFmpeg.
- 🧠 **AI Speech-to-Text Engine**: Leverages local OpenAI Whisper AI models (`tiny`, `base`, `small`, `medium`) for speech recognition.
- 📋 **1-Click Copy Transcript**: Interactive interface to copy raw transcript text or timestamped lines with one click.
- 📂 **Multi-Format Caption Exporter**: Save transcript outputs as `.txt`, `.srt` (SubRip), `.vtt` (WebVTT), and `.json` data.
- 🌐 **Dual Web Interfaces**:
  - **Firebase Web Dashboard**: Glassmorphism web UI hosted at `https://instagramtranscript.web.app`.
  - **Streamlit Web App**: Local/cloud interactive dashboard (`streamlit run app.py`).
- ⚡ **Flask REST API**: Production-ready HTTP API server (`server.py`) with cross-origin support (CORS).
- 💻 **Terminal CLI**: Execution script (`cli.py`) for quick command-line processing.
- 🛡️ **Multi-Provider Fallback Pipeline**: Resilience through fallback engines (`yt-dlp` -> HTTP extraction APIs -> Netscape `cookies.txt`).

---

## 🏗️ System Architecture & Workflow

```
       ┌────────────────────────────────────────────────────────┐
       │             User Submits Instagram Link                │
       │  (Web UI / Streamlit Dashboard / Flask API / Terminal)  │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │           InstagramTranscriber Engine                  │
       │   1. Validate URL & Extract Shortcode                  │
       │   2. Multi-Provider Audio Stream Downloader             │
       │      └─ Provider 1: yt-dlp (with cookies support)    │
       │      └─ Provider 2: Direct HTTP Extractor API          │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │             FFmpeg Audio Transcoder                    │
       │    Converts media binary -> 192kbps MP3 audio          │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │             OpenAI Whisper AI Engine                   │
       │  Speech-to-Text Inference (tiny/base/small/medium)     │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │                 Generated Outputs                      │
       │  • Raw Text Transcript  • Timestamp Breakdown          │
       │  • SubRip (.srt)        • WebVTT (.vtt) • JSON Data   │
       └────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start & Local Setup

### 1. Prerequisites
- Python 3.9 - 3.11
- FFmpeg (automatically configured via `imageio_ffmpeg` or system PATH)

### 2. Installation
```bash
git clone https://github.com/Mrswami/instagramTranscript.git
cd instagramTranscript
pip install -r requirements.txt
```

---

## 💻 Usage Guides

### Option A: Run Streamlit Web Application
Launch the interactive Streamlit dashboard:
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

### Option B: Run Flask REST API Backend
Launch the backend server:
```bash
python server.py
```
The REST API runs on `http://localhost:5000`.

### Option C: Run Terminal CLI Tool
Transcribe directly from your command line:
```bash
python cli.py "https://www.instagram.com/reel/Cxxxxxx/" --model base --outdir output
```

**CLI Parameters:**
- `url`: Instagram Reel or Post link.
- `--model`: Whisper model size (`tiny`, `base`, `small`, `medium`). Default: `base`.
- `--outdir`: Directory to store generated MP3 and transcript files. Default: `output`.

---

## 📡 REST API Documentation

### 1. Health Check
- **Endpoint**: `GET /health` or `GET /`
- **Response**:
  ```json
  {
    "service": "Instagramtranscript API Engine",
    "status": "ok",
    "version": "1.0.0"
  }
  ```

### 2. Transcribe Link
- **Endpoint**: `POST /api/transcribe`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "url": "https://www.instagram.com/reel/Cxxxxxx/",
    "model": "base"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "text": "Full transcribed speech text...",
    "segments": [
      {
        "start": 0.0,
        "end": 3.42,
        "text": "First spoken segment"
      }
    ],
    "srt": "1\n00:00:00,000 --> 00:00:03,420\nFirst spoken segment\n",
    "vtt": "WEBVTT\n\n00:00:00.000 --> 00:00:03.420\nFirst spoken segment\n",
    "audio_file": "output/Cxxxxxx.mp3"
  }
  ```

---

## 📂 Repository File Structure

```
instagramTranscript/
├── app.py              # Streamlit Web App interface with glassmorphism design
├── server.py           # Flask REST API backend server with pre-loading & CORS
├── cli.py              # Command-line interface tool
├── transcriber.py      # Core media downloader, FFmpeg transcoder & Whisper AI pipeline
├── ISSUES.md           # QA testing report, latency performance benchmarks & resolved issues
├── DEPLOYMENT.md       # Cloud deployment instructions (Render, Railway, Google Cloud Run)
├── Dockerfile          # Container specification for cloud hosting
├── firebase.json       # Firebase Hosting configuration
├── .firebaserc         # Firebase project target mapping
├── render.yaml         # Render cloud service deployment configuration
├── requirements.txt    # Python dependency manifest
├── public/             # Static web assets for live Web App
│   ├── index.html      # Responsive glassmorphism web client with health indicator
│   └── logo.jpg        # Brand logo asset
└── output/             # Output folder for generated MP3s and transcripts

```

---

## ☁️ Deployment

- **Frontend Hosting (Firebase)**: Configured in `firebase.json` for rapid deployment to `https://instagramtranscript.web.app`.
- **Backend Cloud Hosting (Render / Docker)**: Deploy `Dockerfile` directly to [Render](https://render.com), [Railway](https://railway.app), or [Google Cloud Run](https://cloud.google.com/run). See [`DEPLOYMENT.md`](DEPLOYMENT.md) for step-by-step guidance.

---

## 📜 License

MIT License - Free and open-source for developers, creators, and researchers.
