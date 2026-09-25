import os
import threading
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from transcriber import InstagramTranscriber

app = Flask(__name__)
# Enable CORS for all routes and origins
CORS(app, resources={r"/*": {"origins": "*"}})

# Load configuration parameters from environment or defaults
output_dir = os.environ.get("OUTPUT_DIR", "output")
output_abs_dir = os.path.abspath(output_dir)
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
        "version": "1.2.0",
        "model_cached": "base" in transcriber._model_cache
    })


@app.route('/api/download/<filename>', methods=['GET', 'OPTIONS'])
@app.route('/output/<filename>', methods=['GET', 'OPTIONS'])
def download_file(filename):
    """
    Serve generated MP3 audio, TXT transcript, SRT, or VTT files.

    Args:
        filename (str): Name of the generated file in output directory.

    Returns:
        File stream attachment response.
    """
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    as_attachment = request.args.get('download', 'true').lower() == 'true'
    return send_from_directory(output_abs_dir, filename, as_attachment=as_attachment)


@app.route('/api/transcribe', methods=['POST', 'OPTIONS'])
def transcribe_endpoint():
    """
    Transcribe speech from an Instagram Reel or Post link.
    """
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    data = request.get_json(force=True, silent=True) or {}
    url = data.get('url', '').strip()
    model_name = data.get('model', 'base')
    openai_key = data.get('openai_api_key') or request.headers.get('X-OpenAI-Key')

    if not url:
        return jsonify({"error": "Missing Instagram URL"}), 400

    if not transcriber.validate_url(url):
        return jsonify({"error": "Invalid Instagram URL format"}), 400

    try:
        print(f"[API Engine] Processing request for URL: {url} (Model: {model_name})")
        result = transcriber.process_url(url, model_name=model_name, openai_api_key=openai_key)
        
        host_url = request.host_url.rstrip('/')
        mp3_filename = result.get('mp3_filename')
        txt_filename = result.get('txt_filename')
        srt_filename = result.get('srt_filename')
        vtt_filename = result.get('vtt_filename')

        return jsonify({
            "status": "success",
            "text": result['text'],
            "video_id": result.get('video_id'),
            "segments": result['segments'],
            "srt": result['srt'],
            "vtt": result['vtt'],
            "mp3_filename": mp3_filename,
            "txt_filename": txt_filename,
            "mp3_url": f"{host_url}/api/download/{mp3_filename}" if mp3_filename else None,
            "txt_url": f"{host_url}/api/download/{txt_filename}" if txt_filename else None,
            "srt_url": f"{host_url}/api/download/{srt_filename}" if srt_filename else None,
            "vtt_url": f"{host_url}/api/download/{vtt_filename}" if vtt_filename else None,
            "audio_file": result['audio_file'],
            "txt_file": result.get('txt_file')
        })
    except Exception as e:
        print(f"[API Engine Error] Error processing URL {url}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/upload', methods=['POST', 'OPTIONS'])
def upload_endpoint():
    """
    Direct Video/Audio File Upload Transcribe Endpoint.
    Workaround for private reels, auth barriers, or cloud IP blocks.
    """
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded. Please select an MP4, MOV, M4A, or MP3 file."}), 400

    file = request.files['file']
    model_name = request.form.get('model', 'base')
    openai_key = request.form.get('openai_api_key') or request.headers.get('X-OpenAI-Key')

    if file.filename == '':
        return jsonify({"error": "No selected file."}), 400

    temp_path = None
    try:
        import tempfile
        from pathlib import Path
        temp_dir = Path(tempfile.gettempdir()) / "insta_transcribe_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        filename = file.filename
        temp_path = temp_dir / filename
        file.save(str(temp_path))

        print(f"[API Engine] Processing uploaded file: {filename}")
        result = transcriber.process_file(temp_path, model_name=model_name, openai_api_key=openai_key)

        host_url = request.host_url.rstrip('/')
        mp3_filename = result.get('mp3_filename')
        txt_filename = result.get('txt_filename')
        srt_filename = result.get('srt_filename')
        vtt_filename = result.get('vtt_filename')

        return jsonify({
            "status": "success",
            "text": result['text'],
            "video_id": result.get('video_id'),
            "segments": result['segments'],
            "srt": result['srt'],
            "vtt": result['vtt'],
            "mp3_filename": mp3_filename,
            "txt_filename": txt_filename,
            "mp3_url": f"{host_url}/api/download/{mp3_filename}" if mp3_filename else None,
            "txt_url": f"{host_url}/api/download/{txt_filename}" if txt_filename else None,
            "srt_url": f"{host_url}/api/download/{srt_filename}" if srt_filename else None,
            "vtt_url": f"{host_url}/api/download/{vtt_filename}" if vtt_filename else None,
            "audio_file": result['audio_file'],
            "txt_file": result.get('txt_file')
        })
    except Exception as e:
        print(f"[API Engine Error] Error processing uploaded file: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"[API Engine] Instagramtranscript REST API server running on http://0.0.0.0:{port}...")
    app.run(host='0.0.0.0', port=port, debug=False)




