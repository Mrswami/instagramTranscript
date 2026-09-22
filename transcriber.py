import os
import sys
import re
import json
import time
import tempfile
import subprocess
from pathlib import Path
import requests

try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.path.pathsep + os.environ.get("PATH", "")
except Exception:
    ffmpeg_exe = "ffmpeg"

class InstagramTranscriber:
    def __init__(self, output_dir="output", cookies_file="cookies.txt"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_file = Path(cookies_file)

    @staticmethod
    def validate_url(url: str) -> bool:
        """Verify if URL is a valid Instagram Reel or Post link."""
        pattern = r"https?://(www\.)?instagram\.com/(reel|p|reels)/[A-Za-z0-9_-]+/?.*"
        return bool(re.match(pattern, url.strip()))

    @staticmethod
    def extract_shortcode(url: str) -> str:
        match = re.search(r"/(reel|p|reels)/([A-Za-z0-9_-]+)", url)
        return match.group(2) if match else "reel"

    def convert_video_to_mp3(self, video_path: Path, output_mp3: Path) -> Path:
        """Convert any MP4/video file to 192kbps MP3 audio file using FFmpeg."""
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
        """Download video/audio file directly from HTTP URL."""
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
        """Download audio using yt-dlp with optional cookies support."""
        import yt_dlp
        video_id = self.extract_shortcode(url)
        temp_dir = Path(tempfile.gettempdir()) / "insta_transcribe"
        temp_dir.mkdir(parents=True, exist_ok=True)
        out_template = str(temp_dir / f"{video_id}.%(ext)s")

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': out_template,
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            }
        }

        if self.cookies_file.exists():
            ydl_opts['cookiefile'] = str(self.cookies_file)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        mp3_file = temp_dir / f"{video_id}.mp3"
        if not mp3_file.exists():
            candidates = list(temp_dir.glob(f"{video_id}*.mp3"))
            if candidates:
                mp3_file = candidates[0]
            else:
                raise FileNotFoundError("yt-dlp failed to produce MP3 file.")

        dest_mp3 = self.output_dir / f"{video_id}.mp3"
        with open(mp3_file, 'rb') as sf, open(dest_mp3, 'wb') as df:
            df.write(sf.read())
        return dest_mp3

    def download_audio(self, url: str) -> Path:
        """Download audio using multi-provider fallbacks (yt-dlp -> Direct -> API)."""
        if not self.validate_url(url):
            raise ValueError("Invalid Instagram URL. Please enter a valid Reel or Post link.")

        # Attempt 1: yt-dlp
        try:
            return self.download_audio_ytdlp(url)
        except Exception as e1:
            print(f"yt-dlp attempt failed: {e1}. Trying direct API extraction...")

        # Attempt 2: Public Instagram Downloader API
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
            print(f"API attempt failed: {e2}")

        raise RuntimeError(
            "Could not download Instagram Reel. If this post is private or rate-limited, "
            "please place a valid 'cookies.txt' file in the project folder."
        )

    def transcribe(self, audio_path: Path, model_name="base") -> dict:
        """Transcribe MP3 audio file using Whisper AI (handles long audio seamlessly)."""
        import whisper
        print(f"Loading Whisper model '{model_name}'...")
        model = whisper.load_model(model_name)
        print(f"Transcribing audio file: {audio_path.name}...")
        result = model.transcribe(str(audio_path), fp16=False)
        return result

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """Format seconds into HH:MM:SS,mmm timestamp string."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milli = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{milli:03d}"

    def export_srt(self, segments: list) -> str:
        """Generate SRT format transcript from segments."""
        lines = []
        for idx, seg in enumerate(segments, 1):
            start = self.format_timestamp(seg['start'])
            end = self.format_timestamp(seg['end'])
            text = seg['text'].strip()
            lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
        return "\n".join(lines)

    def export_vtt(self, segments: list) -> str:
        """Generate WebVTT format transcript from segments."""
        lines = ["WEBVTT\n"]
        for seg in segments:
            start = self.format_timestamp(seg['start']).replace(',', '.')
            end = self.format_timestamp(seg['end']).replace(',', '.')
            text = seg['text'].strip()
            lines.append(f"{start} --> {end}\n{text}\n")
        return "\n".join(lines)

    def process_url(self, url: str, model_name="base") -> dict:
        """Full pipeline: Instagram URL -> MP3 Audio -> OpenAI Whisper AI -> Transcript."""
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
