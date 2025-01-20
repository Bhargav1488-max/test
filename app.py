from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from moviepy.editor import AudioFileClip
import speech_recognition as sr
import google.generativeai as genai

# Configure your Generative AI API Key
genai.configure(api_key="AIzaSyAGDcHAkQDlHj-PKROGDAuvPfzNapYg6Vs")  # Replace with your API key

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'mp4', 'mp3', 'wav', 'm4a'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def transcribe_audio(file_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio_data)
        return text
    except sr.UnknownValueError:
        return "Speech recognition could not understand the audio."
    except sr.RequestError:
        return "Error with the speech recognition service."

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Convert video to audio if necessary
        if filename.rsplit('.', 1)[1].lower() == 'mp4':
            audio_path = file_path.rsplit('.', 1)[0] + '.wav'
            clip = AudioFileClip(file_path)
            clip.audio.write_audiofile(audio_path)
            file_path = audio_path

        # Transcribe audio to text
        transcription = transcribe_audio(file_path)

        # Enhance transcription using Generative AI
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(f"Refine this transcription: {transcription}")
            transcription = response.text
        except Exception as e:
            return jsonify({"error": f"AI enhancement failed: {str(e)}"}), 500

        # Save transcription to a text file
        text_file_path = file_path.rsplit('.', 1)[0] + '.txt'
        with open(text_file_path, 'w') as f:
            f.write(transcription)

        return jsonify({
            "message": "File processed successfully.",
            "transcription": transcription,
            "download_url": f"/download/{os.path.basename(text_file_path)}"
        })

    return jsonify({"error": "File type not allowed"}), 400

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return app.send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
