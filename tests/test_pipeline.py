"""
Unit and Integration Tests for Instagramtranscript Media Pipeline and API Server.
"""

import os
import wave
import struct
import tempfile
import unittest
from pathlib import Path
from transcriber import InstagramTranscriber
from server import app


class TestInstagramTranscriber(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.transcriber = InstagramTranscriber(output_dir=str(self.output_dir))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_url_validation(self):
        valid_urls = [
            "https://www.instagram.com/reel/DdZxkZRkZL4/",
            "https://instagram.com/reel/Cxxxxxx/",
            "https://www.instagram.com/p/Cxxxxxx/",
            "https://www.instagram.com/tv/Cxxxxxx/",
            "https://instagr.am/p/Cxxxxxx/"
        ]
        invalid_urls = [
            "https://google.com",
            "https://instagram.com/username",
            "not_a_url",
            "ftp://instagram.com/reel/123"
        ]

        for url in valid_urls:
            self.assertTrue(self.transcriber.validate_url(url), f"Should be valid: {url}")

        for url in invalid_urls:
            self.assertFalse(self.transcriber.validate_url(url), f"Should be invalid: {url}")

    def test_shortcode_extraction(self):
        urls_and_expected = [
            ("https://www.instagram.com/reel/DdZxkZRkZL4/?utm_source=ig_web_copy_link", "DdZxkZRkZL4"),
            ("https://www.instagram.com/share/p/C7X_X11v8-0/", "C7X_X11v8-0"),
            ("https://www.instagram.com/share/reel/C7X_X11v8-0/?igsh=123", "C7X_X11v8-0"),
            ("https://ddinstagram.com/reel/DdZxkZRkZL4/", "DdZxkZRkZL4"),
        ]
        for url, expected in urls_and_expected:
            shortcode = self.transcriber.extract_shortcode(url)
            self.assertEqual(shortcode, expected, f"Failed for URL: {url}")

    def test_ffmpeg_mp3_conversion(self):
        # Generate a 1-second synthetic WAV audio file
        sample_rate = 44100
        duration = 1.0
        wav_path = Path(self.temp_dir.name) / "synthetic.wav"
        
        with wave.open(str(wav_path), 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for i in range(int(sample_rate * duration)):
                value = int(32767.0 * 0.5 * (i % 100 / 50.0 - 1.0))
                data = struct.pack('<h', value)
                wav_file.writeframesraw(data)

        mp3_dest = self.output_dir / "synthetic.mp3"
        result_mp3 = self.transcriber.convert_video_to_mp3(wav_path, mp3_dest)
        
        self.assertTrue(result_mp3.exists(), "MP3 output file should exist")
        self.assertGreater(result_mp3.stat().st_size, 0, "MP3 output file should not be empty")

    def test_caption_export_formats(self):
        mock_segments = [
            {"start": 0.0, "end": 2.5, "text": "Hello world!"},
            {"start": 2.5, "end": 5.0, "text": "This is a transcript test."}
        ]

        srt_out = self.transcriber.export_srt(mock_segments)
        vtt_out = self.transcriber.export_vtt(mock_segments)

        self.assertIn("00:00:00,000 --> 00:00:02,500", srt_out)
        self.assertIn("Hello world!", srt_out)
        self.assertIn("WEBVTT", vtt_out)
        self.assertIn("00:00:02.500 --> 00:00:05.000", vtt_out)


class TestFlaskAPIServer(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_health_endpoint(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'ok')
        self.assertIn('service', json_data)

    def test_invalid_url_transcribe_endpoint(self):
        response = self.client.post('/api/transcribe', json={'url': 'invalid_url'})
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertIn('error', json_data)

    def test_upload_missing_file_endpoint(self):
        response = self.client.post('/api/upload')
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertIn('error', json_data)


if __name__ == '__main__':
    unittest.main()
