import os
import sys
import re
import json
import tempfile
from pathlib import Path
import yt_dlp

try:
    import imageio_ffmpeg
    # Register imageio_ffmpeg path into PATH environment if system ffmpeg is missing
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.path.pathsep + os.environ.get("PATH", "")
except Exception as e:
    pass

class InstagramTranscriber:
    def __init__(self, output_dir="output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validate_url(url: str) -> bool:
        """Verify if URL is a valid Instagram Reel or Post link."""
        pattern = r"https?://(www\.)?instagram\.com/(reel|p|reels)/[A-Za-z0-9_-]+/?.*"
        return bool(re.match(pattern, url.strip()))

    def download_audio(self, url: str) -> Path:
        """Download audio from Instagram URL and save as MP3."""
        if not self.validate_url(url):
            raise ValueError("Invalid Instagram URL. Please enter a valid Reel or Post link.")

        temp_dir = Path(tempfile.gettempdir()) / "insta_transcribe"
        temp_dir.mkdir(parents=True, exist_ok=True)
        out_template = str(temp_dir / "%(id)s.%(ext)s")

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
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id', 'audio')
            title = info.get('title', 'Instagram Audio')

        mp3_file = temp_dir / f"{video_id}.mp3"
        if not mp3_file.exists():
            # Fallback check for any matching file in temp directory
            candidates = list(temp_dir.glob(f"{video_id}*"))
            if candidates:
                mp3_file = candidates[0]
            else:
                raise FileNotFoundError("Audio extraction failed. MP3 file not found.")

        # Copy to output directory
        dest_mp3 = self.output_dir / f"{video_id}.mp3"
        with open(mp3_file, 'rb') as sf, open(dest_mp3, 'wb') as df:
            df.write(sf.read())

        return dest_mp3

    def transcribe(self, audio_path: Path, model_name="base") -> dict:
        """Transcribe MP3 audio file using Whisper."""
        try:
            import whisper
        except ImportError:
            raise ImportError("openai-whisper is not installed. Run: pip install openai-whisper")

        model = whisper.load_model(model_name)
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
        """Full process: Download audio -> Transcribe -> Return structured outputs."""
        audio_path = self.download_audio(url)
        transcribe_res = self.transcribe(audio_path, model_name=model_name)

        full_text = transcribe_res.get('text', '').strip()
        segments = transcribe_res.get('segments', [])

        srt_content = self.export_srt(segments)
        vtt_content = self.export_vtt(segments)

        result_data = {
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
        return result_data
