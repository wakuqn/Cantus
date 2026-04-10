from flask import Flask, request, render_template_string, jsonify
import os
import tempfile
from pydub import AudioSegment
import shutil
import time
from datetime import datetime
import threading

from Pre_Processing import clean_n_chunk, transcribe, upload_to_hf
from finetune import run_commands

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For Flask sessions (not related to user id)

ALLOWED_EXTENSIONS = {'mp3', 'flac', 'wav'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_audio_pipeline(wav_path, user_id):
    try:
        # Step 1: Chunk the wav file
        chunk_dir = clean_n_chunk(wav_path)  # returns directory path like user_id/chunks
        print("Chunking complete.")
        # Step 2: Preprocess chunks
        parquet_, wave = transcribe(chunk_dir)
        print("Pre-processing complete.")
        # Create subdirectory for storing wav files for upload
        wav_save_dir = os.path.dirname(wav_path)
        wav_save_dir = os.path.join(wav_save_dir, "wav_chunks")
        os.makedirs(wav_save_dir, exist_ok=True)
        # Step 3: Upload to HuggingFace Hub
        upload_to_hf(wav_save_dir, parquet_, wave, user_id)
        print("Uploaded to HF.")
        time.sleep(30)  # Wait before finetuning
        # Step 4: Finetune
        run_commands(user_id)
        print("Fine-tuning started.")
    except Exception as e:
        print(f"Error in pipeline: {e}")

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/api/apply_model', methods=['POST'])
def apply_model():
    data = request.json
    if not data or 'filename' not in data:
        return jsonify({"error": "No filename provided"}), 400
    
    filename = data['filename']
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    music_dir = os.path.join(base_dir, 'music')
    file_path = os.path.join(music_dir, filename)
    
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    user_id = datetime.now().strftime("%Y%m%d%H%M%S")
    print(f"[INFO] Generated user_id: {user_id} for local file {filename}")
    
    def background_task(f_path, uid):
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                audio = AudioSegment.from_file(f_path)
                wav_path = os.path.join(temp_dir, "converted.wav")
                audio.export(wav_path, format="wav")
                print(f"Converted WAV saved at: {wav_path}")
                
                process_audio_pipeline(wav_path, uid)
        except Exception as e:
            print(f"Error in background_task: {e}")

    threading.Thread(target=background_task, args=(file_path, user_id)).start()
    return jsonify({"status": "started", "user_id": user_id, "message": "Model fine-tuning started in background."})

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_FORM)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)