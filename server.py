import os
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
from transcriber import InstagramTranscriber

app = Flask(__name__)
# Enable CORS for all routes and origins
CORS(app, resources={r"/*": {"origins": "*"}})

# Load configuration parameters from environment or defaults
output_dir = os.environ.get("OUTPUT_DIR", "output")
transcriber = InstagramTranscriber(output_dir=output_dir)

# Asynchronously pre-load default 'base' Whisper model in background on server start
threading.Thread(target=transcriber.preload_model, args=("base",), daemon=True).start()


@app.after_request
def add_cors_headers(response):
    """Ensure all API responses include required CORS headers for cross-origin web apps."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response


@app.route('/', methods=['GET', 'OPTIONS'])
@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    """
    Health check endpoint verifying API server status and readiness.

    Returns:
        JSON response with service metadata and status code 200.
    """
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    return jsonify({
        "status": "ok",
        "service": "Instagramtranscript API Engine",
        "version": "1.1.0",
        "model_cached": "base" in transcriber._model_cache
    })


@app.route('/api/transcribe', methods=['POST', 'OPTIONS'])
def transcribe_endpoint():
    """
    Transcribe speech from an Instagram Reel or Post link.

    Request Body (JSON):
        url (str): Required Instagram post/reel link.
        model (str): Optional Whisper model size ('tiny', 'base', 'small', 'medium'). Default: 'base'.

    Returns:
        JSON response with transcribed text, SRT, VTT, segments, and audio file path.
    """
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    data = request.get_json(force=True, silent=True) or {}
    url = data.get('url', '').strip()
    model_name = data.get('model', 'base')

    if not url:
        return jsonify({"error": "Missing Instagram URL"}), 400

    if not transcriber.validate_url(url):
        return jsonify({"error": "Invalid Instagram URL format"}), 400

    try:
        print(f"🚀 Processing request for URL: {url} (Model: {model_name})")
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



