from flask import Flask, request, jsonify
from flask_cors import CORS
from transcriber import InstagramTranscriber

app = Flask(__name__)
CORS(app)

transcriber = InstagramTranscriber(output_dir="output")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "Instagramtranscript API Engine"})

@app.route('/api/transcribe', methods=['POST'])
def transcribe_endpoint():
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
    print("✨ Instagramtranscript REST API server running on http://0.0.0.0:5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
