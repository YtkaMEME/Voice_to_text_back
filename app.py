import asyncio
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import shutil
from assemblyai_dialogue import transcribe_audio_to_text
from threading import Thread
from db_manager import DBManager

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

db = DBManager("file_tracking.db")


def background_job(user_id, file_path, file_id, original_name):
    async def run_all():
        try:
            # Транскрибируем
            transcript_path = await transcribe_audio_to_text(file_path, original_name)
            output_filename = os.path.basename(transcript_path)

            # Перемещаем результат
            user_folder = os.path.join(PROCESSED_FOLDER, str(user_id))
            os.makedirs(user_folder, exist_ok=True)
            new_path = os.path.join(user_folder, output_filename)
            shutil.move(transcript_path, new_path)

            # Обновляем БД
            db.set_transcript_name(user_id, original_name, output_filename)

        finally:
            # Удаляем исходный файл и .mp3
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                base_name, _ = os.path.splitext(file_path)
                mp3_path = base_name + ".mp3"
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
                print(f"🧹 Удалены: {file_path} и {mp3_path}")
            except Exception as e:
                print(f"⚠️ Ошибка при удалении: {e}")

    asyncio.run(run_all())


@app.route('/upload', methods=['POST'])
def upload():
    user_id = int(request.form.get("user_id", 0))
    if not user_id:
        return jsonify({'error': 'Не передан user_id'}), 400

    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Пустое имя файла'}), 400

    file_id = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, file_id)
    file.save(file_path)
    original_name = file.filename

    db.add_file_record(user_id, original_name)
    Thread(target=background_job, args=(user_id, file_path, file_id, original_name)).start()

    return jsonify({'status': 'accepted', 'file': file_id})


@app.route('/get-transcript', methods=['POST'])
def get_transcript():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'Не передан user_id'}), 400

    transcript = db.get_pending_file(user_id)
    if not transcript:
        return jsonify({'status': 'empty'})

    file_path = os.path.join(PROCESSED_FOLDER, str(user_id), transcript)
    return jsonify({'status': 'ready', 'file_path': file_path, 'file_name': transcript})


@app.route('/delete-transcript', methods=['POST'])
def delete_transcript():
    data = request.json
    user_id = data.get('user_id')
    file_name = data.get('file_name')

    if not user_id or not file_name:
        return jsonify({'error': 'Не переданы user_id или file_name'}), 400

    file_path = os.path.join(PROCESSED_FOLDER, str(user_id), file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
        db.delete_file_record(user_id, file_name)
        return jsonify({'status': 'deleted'})
    else:
        return jsonify({'error': 'Файл не найден'}), 404


@app.route('/download/<user_id>/<file_name>', methods=['GET'])
def download(user_id, file_name):
    file_path = os.path.join(PROCESSED_FOLDER, user_id, file_name)
    if not os.path.exists(file_path):
        return jsonify({'error': 'Файл не найден'}), 404
    return send_from_directory(os.path.join(PROCESSED_FOLDER, user_id), file_name, as_attachment=True)


if __name__ == '__main__':
    app.run(port=5000)