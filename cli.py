"""
Instagramtranscript CLI Script.

Command-line execution script for transcribing Instagram Reels and Posts directly
from the terminal without launching a web browser.

Usage:
    python cli.py "https://www.instagram.com/reel/Cxxxxxx/" --model base --outdir ./output
"""

import sys
import argparse
from pathlib import Path
from transcriber import InstagramTranscriber


def main() -> None:
    """
    Parse command-line arguments and run Instagram Transcriber pipeline.
    """
    parser = argparse.ArgumentParser(
        description="Download audio and transcribe Instagram Reels or Posts using OpenAI Whisper AI."
    )
    parser.add_argument("url", help="Instagram Reel or Post URL (e.g. https://www.instagram.com/reel/Cxxxxxx/)")
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium"],
        help="Whisper AI model size (default: base)"
    )
    parser.add_argument(
        "--outdir",
        default="output",
        help="Target output directory for audio and transcript files (default: output)"
    )

    args = parser.parse_args()

    print(f"🚀 Processing Instagram URL: {args.url}")
    transcriber = InstagramTranscriber(output_dir=args.outdir)

    try:
        result = transcriber.process_url(args.url, model_name=args.model)

        print("\n" + "=" * 50)
        print("🎉 TRANSCRIPTION COMPLETE")
        print("=" * 50)
        print(f"🎵 Audio Saved: {result['audio_file']}")
        print("\n📝 TRANSCRIPT:")
        print(result['text'])
        print("=" * 50)

        out_path = Path(args.outdir)
        (out_path / "transcript.txt").write_text(result['text'], encoding="utf-8")
        (out_path / "transcript.srt").write_text(result['srt'], encoding="utf-8")
        (out_path / "transcript.vtt").write_text(result['vtt'], encoding="utf-8")
        (out_path / "transcript.json").write_text(result['json'], encoding="utf-8")

        print(f"✅ Saved transcript files (.txt, .srt, .vtt, .json) to folder: {out_path.resolve()}")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

