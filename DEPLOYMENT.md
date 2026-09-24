# 🚀 Cloud Backend Deployment Guide

This guide explains how to deploy the **Instagramtranscript** Python backend engine (`server.py` + `Whisper AI` + `FFmpeg`) to a cloud provider so that `mtranscript.web.app` works online everywhere on mobile & desktop without needing Python running locally.

---

## 🟢 Option 1: Deploy to Render (Recommended & 100% Free)

Render supports containerized Docker apps out-of-the-box.

1. **Push your latest changes to GitHub**:
   ```bash
   git add .
   git commit -m "Add Dockerfile, server settings, and deployment configs"
   git push origin main
   ```

2. **Deploy on Render**:
   - Go to [dashboard.render.com](https://dashboard.render.com) and click **New +** -> **Web Service**.
   - Connect your GitHub repository `Mrswami/instagramTranscript`.
   - Select **Docker** as the Runtime.
   - Choose the **Free Plan** (or higher).
   - Click **Create Web Service**.

3. **Copy your Public API URL**:
   - Render will give you a public HTTPS URL like `https://instagramtranscript-backend.onrender.com`.

4. **Connect URL to `mtranscript.web.app`**:
   - Open `mtranscript.web.app` in your browser.
   - Click **⚙️ API Settings** in the upper right.
   - Select **Cloud Server API** and paste your URL: `https://instagramtranscript-backend.onrender.com/api/transcribe`.
   - Click **Save Engine URL**.

---

## 🔵 Option 2: Deploy to Railway

1. Install Railway CLI or connect via [railway.app](https://railway.app).
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Select `instagramTranscript`. Railway automatically detects the `Dockerfile` and deploys it.
4. Generate a Domain under settings and copy `https://your-app.up.railway.app`.

---

## 🟡 Option 3: Deploy to Google Cloud Run

1. Build and push container to Google Artifact Registry:
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/insta-transcribe
   ```
2. Deploy container to Cloud Run:
   ```bash
   gcloud run deploy insta-transcribe --image gcr.io/YOUR_PROJECT_ID/insta-transcribe --platform managed --allow-unauthenticated
   ```

---

## 🌐 How the Frontend Resolves the API Endpoint

The frontend (`public/index.html`) automatically handles backend endpoint selection in order:

1. **Custom API URL**: Saved via the **⚙️ API Settings** button on the website (`localStorage.getItem('custom_api_url')`).
2. **URL Parameter**: Passing `?api=https://your-cloud-backend.com/api/transcribe`.
3. **Local Backend Fallback**: Defaults to `http://localhost:5000/api/transcribe` when running locally.
