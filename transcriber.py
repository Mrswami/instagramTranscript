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

        Args:
            url (str): The URL string to evaluate.

        Returns:
            bool: True if URL matches Instagram reel/post format, False otherwise.
        """
        pattern = r"https?://(www\.)?(instagram\.com|instagr\.am)/(reel|p|reels|tv|share)/[A-Za-z0-9_-]+/?.*"
        return bool(re.match(pattern, url.strip()))

    @staticmethod
    def extract_shortcode(url: str) -> str:
        """
        Extract the Instagram post/reel shortcode identifier from a URL.

        Args:
            url (str): Instagram post/reel URL.

        Returns:
            str: Shortcode ID, or 'reel' as a default fallback.
        """
        match = re.search(r"/(reel|p|reels|tv|share)/([A-Za-z0-9_-]+)", url)
        return match.group(2) if match else "reel"


    def convert_video_to_mp3(self, video_path: Path, output_mp3: Path) -> Path:
        """
        Convert any source video/audio file into a standardized 192kbps MP3 file using FFmpeg.

        Args:
            video_path (Path): Path to source video file (e.g. .mp4).
            output_mp3 (Path): Destination path for generated .mp3 file.

        Returns:
            Path: Path to the resulting MP3 audio file.

        Raises:
            RuntimeError: If FFmpeg fails or output file is not generated.
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

        Args:
            media_url (str): Direct HTTP link to media stream.
            video_id (str): Unique video shortcode identifier.

        Returns:
            Path: Path to created MP3 file in output directory.
        """
        temp_dir = Path(tempfile.gettempdir()) / "insta_transcribe"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_video = temp_dir / f"{video_id}.mp4"

        r = requests.get(media_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'}, timeout=60)
        with open(temp_video, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        dest_mp3 = self.output_dir / f"{video_id}.mp3"
        return self.convert_video_to_mp3(temp_video, dest_mp3)

    def download_audio_ytdlp(self, url: str) -> Path:
        """
        Download media stream using yt-dlp and convert to MP3 locally using FFmpeg.

        Args:
            url (str): Target Instagram post or reel link.

        Returns:
            Path: Path to output MP3 file.

        Raises:
            FileNotFoundError: If yt-dlp fails to download media stream.
        """
        import yt_dlp
        video_id = self.extract_shortcode(url)
        temp_dir = Path(tempfile.gettempdir()) / "insta_transcribe"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Clear any stale temporary files for this video ID
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
            }
        }

        if ffmpeg_dir:
            ydl_opts['ffmpeg_location'] = ffmpeg_dir

        if self.cookies_file.exists():
            ydl_opts['cookiefile'] = str(self.cookies_file)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        # Locate downloaded media file (.mp4, .m4a, .webm, etc.)
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
        2. Attempt public downloader API extraction.
        3. Raise exception prompting cookie file configuration if all fail.

        Args:
            url (str): Instagram Reel or Post link.

        Returns:
            Path: Path to final converted MP3 file.
        """
        if not self.validate_url(url):
            raise ValueError("Invalid Instagram URL. Please enter a valid Reel or Post link.")

        # Attempt 1: yt-dlp engine
        try:
            return self.download_audio_ytdlp(url)
        except Exception as e1:
            print(f"[Media Extractor] yt-dlp attempt failed: {e1}. Trying direct API extraction...")

        # Attempt 2: Public Instagram Downloader API fallback
        try:
            api_endpoint = f"https://api.vkrdown.com/v4/insta.php?url={url}"
            r = requests.get(api_endpoint, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if r.status_code == 200:
                data = r.json()
                video_url = data.get('data', {}).get('video_url') or data.get('download_url')
                if video_url:
                    video_id = self.extract_shortcode(url)
                    return self.download_direct_url(video_url, video_id)
        except Exception as e2:
            print(f"[Media Extractor] API attempt failed: {e2}")

        raise RuntimeError(
            "Could not download Instagram Reel. If this post is private or rate-limited, "
            "please place a valid 'cookies.txt' file in the project folder."
        )

    def transcribe(self, audio_path: Path, model_name: str = "base") -> Dict[str, Any]:
        """
        Transcribe an MP3 file using OpenAI's Whisper AI models (reuses cached model instances).

        Args:
            audio_path (Path): Path to local MP3 audio file.
            model_name (str): Whisper model model size ('tiny', 'base', 'small', 'medium').

        Returns:
            dict: Raw Whisper dictionary containing 'text', 'segments', and language metadata.
        """
        model = self.get_whisper_model(model_name)
        print(f"[Whisper AI] Transcribing audio file: {audio_path.name} with '{model_name}' model...")
        result = model.transcribe(str(audio_path), fp16=False)
        return result


    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """
        Format floating seconds into HH:MM:SS,mmm timestamp string.

        Args:
            seconds (float): Duration in seconds.

        Returns:
            str: Formatted timestamp string (e.g., '00:01:23,456').
        """
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milli = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{milli:03d}"

    def export_srt(self, segments: List[Dict[str, Any]]) -> str:
        """
        Generate SubRip (.srt) caption formatted string from Whisper segments.

        Args:
            segments (list): Segment list output from Whisper model.

        Returns:
            str: Formatted SRT content.
        """
        lines = []
        for idx, seg in enumerate(segments, 1):
            start = self.format_timestamp(seg['start'])
            end = self.format_timestamp(seg['end'])
            text = seg['text'].strip()
            lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
        return "\n".join(lines)

    def export_vtt(self, segments: List[Dict[str, Any]]) -> str:
        """
        Generate WebVTT (.vtt) caption formatted string from Whisper segments.

        Args:
            segments (list): Segment list output from Whisper model.

        Returns:
            str: Formatted WebVTT content.
        """
        lines = ["WEBVTT\n"]
        for seg in segments:
            start = self.format_timestamp(seg['start']).replace(',', '.')
            end = self.format_timestamp(seg['end']).replace(',', '.')
            text = seg['text'].strip()
            lines.append(f"{start} --> {end}\n{text}\n")
        return "\n".join(lines)

    def process_url(self, url: str, model_name: str = "base") -> Dict[str, Any]:
        """
        Execute full end-to-end processing pipeline for an Instagram URL.

        Pipeline Steps:
        1. Download & convert media to 192kbps MP3.
        2. Run OpenAI Whisper AI speech recognition engine.
        3. Format outputs into raw text, timestamped segments, SRT, VTT, and JSON.

        Args:
            url (str): Target Instagram URL.
            model_name (str): Whisper AI model size ('tiny', 'base', 'small', 'medium').

        Returns:
            dict: Structured dictionary containing all output formats and file paths.
        """
        audio_path = self.download_audio(url)
        transcribe_res = self.transcribe(audio_path, model_name=model_name)

        full_text = transcribe_res.get('text', '').strip()
        segments = transcribe_res.get('segments', [])

        srt_content = self.export_srt(segments)
        vtt_content = self.export_vtt(segments)

        return {
            "audio_file": str(audio_path),
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

