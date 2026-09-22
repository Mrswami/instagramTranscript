# 🎙️ Instagram Reel & Post Transcriber

An end-to-end Python Web Application and CLI tool that downloads high-quality MP3 audio from any Instagram Reel or Post URL and distills it into copyable text transcripts, SRT subtitles, WebVTT captions, and structured JSON data using OpenAI's Whisper AI engine.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-ff4b4b)
![Whisper](https://img.shields.io/badge/OpenAI-Whisper-green)
![yt-dlp](https://img.shields.io/badge/yt--dlp-Media_Extractor-red)

---

## ✨ Features

- 🔗 **Instagram Reel & Post Audio Extraction**: Converts Instagram video links directly to `.mp3` format.
- 🗣️ **AI Speech-to-Text Transcription**: Utilizes local OpenAI Whisper models (`tiny`, `base`, `small`, `medium`).
- 📋 **One-Click Copyable Transcript**: Interactive UI to instantly copy raw text or formatted timestamps.
- 📂 **Multi-Format Subtitle Exporter**: Export as `.txt`, `.srt`, `.vtt`, and `.json`.
- 🎧 **In-Browser Audio Player**: Play audio preview directly on the Web App before downloading.
- 🌐 **Web Dashboard & CLI Interface**: Includes both a glassmorphism Streamlit landing page and a CLI terminal script.

---

## 🚀 Quick Start

### 1. Installation

Clone the repository and install requirements:

```bash
git clone https://github.com/Mrswami/instagramTranscript.git
cd instagramTranscript
pip install -r requirements.txt
```

---

### 2. Run Web Application

Launch the Web UI in your browser:

```bash
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

---

### 3. Run Command-Line Tool (CLI)

Transcribe directly from your terminal:

```bash
python cli.py "https://www.instagram.com/reel/Cxxxxxx/" --model base
```

Options:
- `--model`: `tiny`, `base` (default), `small`, `medium`
- `--outdir`: Directory to save outputs (default: `./output`)

---

## 🌐 Custom Domain & Deployment Setup Guide

### Deploying to Streamlit Community Cloud (Free)
1. Push your repository to GitHub: `https://github.com/Mrswami/instagramTranscript.git`.
2. Go to [share.streamlit.io](https://share.streamlit.io/).
3. Connect your GitHub account and select repository `instagramTranscript` and main file `app.py`.
4. Click **Deploy**.

### Connecting a Custom Domain (e.g. `transcript.yourdomain.com`)
1. In Cloudflare / Namecheap / GoDaddy, add a **CNAME** record pointing your domain to your deployment URL.
2. If using Cloudflare or Render / Vercel, set up SSL certificates automatically via Let's Encrypt.

---

## 🛠️ Architecture & Developer Modules

- `transcriber.py`: Core media pipeline (`yt-dlp` download, MP3 conversion, Whisper AI engine).
- `app.py`: Streamlit Web App landing page with glassmorphism UI & audio/transcript controls.
- `cli.py`: Automated terminal execution script.
- `requirements.txt`: Dependencies specification.

---

## 📜 License
MIT License - Open Source for developers & creators.
