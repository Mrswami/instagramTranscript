"""
Instagram Media Extractor & Whisper AI Speech-to-Text Pipeline.

This module provides the core `InstagramTranscriber` engine, capable of:
1. Validating Instagram Reel & Post URLs.
2. Extracting high-quality audio streams via multi-provider fallbacks (`yt-dlp` -> HTTP direct extraction API -> `cookies.txt`).
3. Converting video/audio binaries to standardized 192kbps MP3 format using FFmpeg.
4. Running OpenAI Whisper AI speech recognition locally to produce text transcripts.
5. Exporting timestamped captions in SRT, WebVTT, and structured JSON formats.
"""

import os
import sys
import re
import json
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests

# Dynamically locate FFmpeg binary via imageio_ffmpeg if available
try:
    import imageio_ffmpeg
    import shutil
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)

    # Whisper expects 'ffmpeg.exe' in PATH on Windows.
    # imageio_ffmpeg names binary e.g. 'ffmpeg-win64-v4.2.2.exe'.
    # Copy to 'ffmpeg.exe' inside ffmpeg_dir if missing.
    target_ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    if not os.path.exists(target_ffmpeg_exe):
        try:
            shutil.copyfile(ffmpeg_exe, target_ffmpeg_exe)
        except Exception as copy_err:
            print(f"[FFmpeg Setup] Warning creating ffmpeg.exe: {copy_err}")

    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.path.pathsep + os.environ.get("PATH", "")
except Exception as e:
    ffmpeg_exe = "ffmpeg"
    ffmpeg_dir = None



class InstagramTranscriber:
    """
    Automated pipeline to download Instagram video audio and transcribe speech using OpenAI Whisper.

    Attributes:
        output_dir (Path): Directory where output MP3 files and transcripts are saved.
        cookies_file (Path): Path to optional Instagram cookies text file for auth-gated posts.
        _model_cache (dict): In-memory cache store for loaded PyTorch Whisper model objects.
    """

    def __init__(self, output_dir: str = "output", cookies_file: str = "cookies.txt") -> None:
        """
        Initialize the InstagramTranscriber instance.

        Args:
            output_dir (str): Relative or absolute path for storing generated audio files.
            cookies_file (str): File path for Netscape-format cookies to bypass private post barriers.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_file = Path(cookies_file)
        self._model_cache: Dict[str, Any] = {}

    def get_whisper_model(self, model_name: str = "base") -> Any:
        """
        Retrieve a loaded Whisper model instance from cache or load it into memory.

        Args:
            model_name (str): Model size identifier ('tiny', 'base', 'small', 'medium').

        Returns:
            Any: Loaded Whisper model object ready for transcription.
        """
        if model_name not in self._model_cache:
            import whisper
            print(f"[Whisper AI] Pre-loading & caching Whisper model '{model_name}' into memory...")
            self._model_cache[model_name] = whisper.load_model(model_name)
        return self._model_cache[model_name]

    def preload_model(self, model_name: str = "base") -> None:
        """
        Pre-load a Whisper model on startup to eliminate cold-start latency for first requests.

        Args:
            model_name (str): Model size identifier to pre-load.
        """
        try:
            self.get_whisper_model(model_name)
            print(f"[Whisper AI] Whisper model '{model_name}' pre-loaded successfully.")
        except Exception as e:
            print(f"[Whisper AI] Warning: Pre-loading Whisper model '{model_name}' failed: {e}")


    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Verify whether an input string is a valid Instagram Reel, Post, or TV link.
        """
        pattern = r"https?://(www\.)?(instagram\.com|instagr\.am|ddinstagram\.com|fxtagram\.com)/(?:[^/]+/)*(reel|p|reels|tv|share)/[A-Za-z0-9_-]+"
        return bool(re.search(pattern, url.strip()))

    @staticmethod
    def extract_shortcode(url: str) -> str:
        """
        Extract the Instagram post/reel shortcode identifier accurately from any URL format.
        """
        clean_url = url.strip().split('?')[0].rstrip('/')
        parts = [p for p in clean_url.split('/') if p]

        for i, p in enumerate(parts):
            if p in ('reel', 'p', 'reels', 'tv'):
                if i + 1 < len(parts) and parts[i + 1] not in ('share', 'reels'):
                    return parts[i + 1]
            if p == 'share':
                if i + 2 < len(parts) and parts[i + 1] in ('p', 'reel', 'reels', 'tv'):
                    return parts[i + 2]
                elif i + 1 < len(parts):
                    return parts[i + 1]

        match = re.search(r"/(?:reel|p|reels|tv|share)/(?:p/|reel/)?([A-Za-z0-9_-]+)", url)
        return match.group(1) if match else "reel"


    def convert_video_to_mp3(self, video_path: Path, output_mp3: Path) -> Path:
        """
        Convert any source video/audio file into a standardized 192kbps MP3 file using FFmpeg.
        """
        cmd = [
            ffmpeg_exe, "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "libmp3lame",
            "-ab", "192k",
            "-ar", "44100",
            str(output_mp3)
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0 or not output_mp3.exists():
            raise RuntimeError(f"FFmpeg MP3 conversion failed: {result.stderr.decode('utf-8', errors='ignore')}")
        return output_mp3

    def download_direct_url(self, media_url: str, video_id: str) -> Path:
        """
        Download media stream directly from an HTTP URL and encode to MP3.
        """
        temp_dir = Path(tempfile.gettempdir()) / "insta_transcribe"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_video = temp_dir / f"{video_id}.mp4"

        r = requests.get(media_url, stream=True, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}, timeout=60)
        with open(temp_video, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        dest_mp3 = self.output_dir / f"{video_id}.mp3"
        return self.convert_video_to_mp3(temp_video, dest_mp3)

    def download_audio_ytdlp(self, url: str) -> Path:
        """
        Download media stream using yt-dlp and convert to MP3 locally using FFmpeg.
        """
        import yt_dlp
        video_id = self.extract_shortcode(url)
        temp_dir = Path(tempfile.gettempdir()) / "insta_transcribe"
        temp_dir.mkdir(parents=True, exist_ok=True)

        for old_file in temp_dir.glob(f"{video_id}.*"):
            try:
                old_file.unlink()
            except Exception:
                pass

        out_template = str(temp_dir / f"{video_id}.%(ext)s")

        ydl_opts = {
            'format': 'bestaudio/best/bestvideo+bestaudio',
            'outtmpl': out_template,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        }

        if ffmpeg_dir:
            ydl_opts['ffmpeg_location'] = ffmpeg_dir

        if self.cookies_file.exists():
            ydl_opts['cookiefile'] = str(self.cookies_file)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        candidates = list(temp_dir.glob(f"{video_id}.*"))
        if not candidates:
            raise FileNotFoundError("yt-dlp failed to download media stream.")

        source_media = candidates[0]
        dest_mp3 = self.output_dir / f"{video_id}.mp3"

        print(f"[Media Extractor] Local media downloaded ({source_media.name}). Converting to MP3 audio...")
        return self.convert_video_to_mp3(source_media, dest_mp3)


    def download_audio(self, url: str) -> Path:
        """
        Execute multi-provider download fallback routine for Instagram media.

        Sequence:
        1. Attempt `yt-dlp` audio extraction.
        2. Attempt DDInstagram OpenGraph video stream extraction.
        3. Attempt Instagram Embed HTML extraction.
        4. Attempt Public Instagram Downloader API extraction.
        """
        if not self.validate_url(url):
            raise ValueError("Invalid Instagram URL. Please enter a valid Reel or Post link.")

        shortcode = self.extract_shortcode(url)
        normalized_url = f"https://www.instagram.com/reel/{shortcode}/" if shortcode and shortcode != "reel" else url

        # Attempt 1: yt-dlp engine with normalized URL
        try:
            return self.download_audio_ytdlp(normalized_url)
        except Exception as e1:
            print(f"[Media Extractor] yt-dlp attempt failed: {e1}. Trying DDInstagram open-graph fallback...")

        # Attempt 2: DDInstagram OpenGraph Mirror Extractor
        try:
            dd_url = f"https://ddinstagram.com/reel/{shortcode}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            r = requests.get(dd_url, headers=headers, timeout=12)
            if r.status_code == 200:
                video_match = re.search(r'<meta\s+property=["\']og:video["\']\s+content=["\']([^"\']+)["\']', r.text)
                if not video_match:
                    video_match = re.search(r'<meta\s+property=["\']og:video:secure_url["\']\s+content=["\']([^"\']+)["\']', r.text)
                if video_match:
                    media_url = video_match.group(1).replace("&amp;", "&")
                    print(f"[Media Extractor] DDInstagram mirror video stream found. Downloading direct MP4...")
                    return self.download_direct_url(media_url, shortcode)
        except Exception as e2:
            print(f"[Media Extractor] DDInstagram fallback failed: {e2}")

        # Attempt 3: Instagram Embed Scraper
        try:
            embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
            r = requests.get(embed_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code == 200:
                matches = re.findall(r'video_url["\']\s*:\s*["\']([^"\']+)["\']', r.text)
                if matches:
                    media_url = matches[0].replace('\\u0026', '&').replace('\\/', '/')
                    print(f"[Media Extractor] Instagram embed stream found. Downloading direct MP4...")
                    return self.download_direct_url(media_url, shortcode)
        except Exception as e3:
            print(f"[Media Extractor] Embed scraper failed: {e3}")

        # Attempt 4: Public Downloader API fallback
        try:
            api_endpoint = f"https://api.vkrdown.com/v4/insta.php?url={url}"
            r = requests.get(api_endpoint, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if r.status_code == 200:
                data = r.json()
                video_url = data.get('data', {}).get('video_url') or data.get('download_url')
                if video_url:
                    return self.download_direct_url(video_url, shortcode)
        except Exception as e4:
            print(f"[Media Extractor] API attempt failed: {e4}")

        raise RuntimeError(
            f"Could not download Instagram Reel ({shortcode}). "
            "If this Reel is private or rate-limited by Instagram, please use the Direct File Upload feature in the Web App to process the video directly!"
        )

    def transcribe(self, audio_path: Path, model_name: str = "base", openai_api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe an MP3 file using OpenAI's cloud API, OpenRouter API, or local PyTorch Whisper models.
        """
        api_key = (openai_api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
        if api_key:
            try:
                from openai import OpenAI
                if api_key.startswith("sk-or-"):
                    print(f"[Whisper Cloud API] Using OpenRouter API (openai/whisper-1)...")
                    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
                    target_model = "openai/whisper-1"
                else:
                    print(f"[Whisper Cloud API] Using OpenAI API (whisper-1)...")
                    client = OpenAI(api_key=api_key)
                    target_model = "whisper-1"

                with open(audio_path, "rb") as f:
                    res = client.audio.transcriptions.create(
                        model=target_model,
                        file=f,
                        response_format="verbose_json"
                    )
                text = getattr(res, 'text', '') if not isinstance(res, dict) else res.get('text', '')
                segments_raw = getattr(res, 'segments', []) if not isinstance(res, dict) else res.get('segments', [])
                segments = []
                for s in segments_raw:
                    s_dict = s if isinstance(s, dict) else (getattr(s, '__dict__', {}) if hasattr(s, '__dict__') else s)
                    segments.append({
                        "start": s_dict.get('start', 0.0) if isinstance(s_dict, dict) else getattr(s, 'start', 0.0),
                        "end": s_dict.get('end', 0.0) if isinstance(s_dict, dict) else getattr(s, 'end', 0.0),
                        "text": (s_dict.get('text', '') if isinstance(s_dict, dict) else getattr(s, 'text', '')).strip()
                    })
                return {"text": text, "segments": segments}
            except Exception as api_err:
                print(f"[Whisper Cloud API] Cloud API call failed ({api_err}). Falling back to local PyTorch Whisper...")

        model = self.get_whisper_model(model_name)
        print(f"[Whisper AI] Transcribing audio file: {audio_path.name} with '{model_name}' model...")
        result = model.transcribe(str(audio_path), fp16=False)
        return result


    @staticmethod
    def format_timestamp(seconds: float) -> str:
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milli = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{milli:03d}"

    def export_srt(self, segments: List[Dict[str, Any]]) -> str:
        lines = []
        for idx, seg in enumerate(segments, 1):
            start = self.format_timestamp(seg['start'])
            end = self.format_timestamp(seg['end'])
            text = seg['text'].strip()
            lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
        return "\n".join(lines)

    def export_vtt(self, segments: List[Dict[str, Any]]) -> str:
        lines = ["WEBVTT\n"]
        for seg in segments:
            start = self.format_timestamp(seg['start']).replace(',', '.')
            end = self.format_timestamp(seg['end']).replace(',', '.')
            text = seg['text'].strip()
            lines.append(f"{start} --> {end}\n{text}\n")
        return "\n".join(lines)

    def process_url(self, url: str, model_name: str = "base", openai_api_key: Optional[str] = None) -> Dict[str, Any]:
        audio_path = self.download_audio(url)
        video_id = self.extract_shortcode(url)
        return self._build_result_package(video_id, audio_path, model_name, openai_api_key)

    def process_file(self, file_path: Path, model_name: str = "base", openai_api_key: Optional[str] = None) -> Dict[str, Any]:
        video_id = file_path.stem
        dest_mp3 = self.output_dir / f"{video_id}.mp3"
        print(f"[Media Extractor] Processing direct uploaded file ({file_path.name}). Converting to MP3...")
        audio_path = self.convert_video_to_mp3(file_path, dest_mp3)
        return self._build_result_package(video_id, audio_path, model_name, openai_api_key)

    def _build_result_package(self, video_id: str, audio_path: Path, model_name: str, openai_api_key: Optional[str]) -> Dict[str, Any]:
        transcribe_res = self.transcribe(audio_path, model_name=model_name, openai_api_key=openai_api_key)

        full_text = transcribe_res.get('text', '').strip()
        segments = transcribe_res.get('segments', [])

        srt_content = self.export_srt(segments)
        vtt_content = self.export_vtt(segments)

        txt_path = self.output_dir / f"{video_id}.txt"
        srt_path = self.output_dir / f"{video_id}.srt"
        vtt_path = self.output_dir / f"{video_id}.vtt"

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write(vtt_content)

        return {
            "video_id": video_id,
            "mp3_filename": audio_path.name,
            "txt_filename": txt_path.name,
            "srt_filename": srt_path.name,
            "vtt_filename": vtt_path.name,
            "audio_file": str(audio_path),
            "txt_file": str(txt_path),
            "srt_file": str(srt_path),
            "vtt_file": str(vtt_path),
            "text": full_text,
            "segments": [
                {
                    "start": seg['start'],
                    "end": seg['end'],
                    "text": seg['text'].strip()
                } for seg in segments
            ],
            "srt": srt_content,
            "vtt": vtt_content,
            "json": json.dumps({"text": full_text, "segments": segments}, indent=2)
        }

