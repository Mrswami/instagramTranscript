"""
Instagramtranscript Flask REST API Server.

Provides endpoints for frontend web clients and external microservices to submit
Instagram Reel or Post URLs for automated audio extraction and Whisper AI speech transcription.

Endpoints:
- GET / or /health: Health check and status metadata.
- POST /api/transcribe: Accepts JSON payload `{"url": "...", "model": "base"}` and returns transcribed text & subtitle tracks.
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from transcriber import InstagramTranscriber

app = Flask(__name__)
CORS(app)

# Load configuration parameters from environment or defaults
output_dir = os.environ.get("OUTPUT_DIR", "output")
transcriber = InstagramTranscriber(output_dir=output_dir)


@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint verifying API server status.

    Returns:
        JSON response with service metadata and status code 200.
    """
    return jsonify({
        "status": "ok",
        "service": "Instagramtranscript API Engine",
        "version": "1.0.0"
    })


@app.route('/api/transcribe', methods=['POST'])
def transcribe_endpoint():
    """
    Transcribe speech from an Instagram Reel or Post link.

    Request Body (JSON):
        url (str): Required Instagram post/reel link.
        model (str): Optional Whisper model size ('tiny', 'base', 'small', 'medium'). Default: 'base'.

    Returns:
        JSON:
            status (str): "success"
            text (str): Full raw transcript string.
            segments (list): Timestamped speech segments.
            srt (str): SubRip format subtitles.
            vtt (str): WebVTT format subtitles.
            audio_file (str): Local path to saved MP3 file.
    """
    data = request.get_json(force=True, silent=True) or {}
    url = data.get('url', '').strip()
    model_name = data.get('model', 'base')

    if not url:
        return jsonify({"error": "Missing Instagram URL"}), 400

    if not transcriber.validate_url(url):
        return jsonify({"error": "Invalid Instagram URL format"}), 400

    try:
        print(f"🚀 Processing request for URL: {url}")
        result = transcriber.process_url(url, model_name=model_name)
        return jsonify({
            "status": "success",
            "text": result['text'],
            "segments": result['segments'],
            "srt": result['srt'],
            "vtt": result['vtt'],
            "audio_file": result['audio_file']
        })
    except Exception as e:
        print(f"❌ Error processing URL {url}: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"✨ Instagramtranscript REST API server running on http://0.0.0.0:{port}...")
    app.run(host='0.0.0.0', port=port, debug=False)


