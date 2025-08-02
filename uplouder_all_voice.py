import os
import time
import requests
from pydub import AudioSegment
from config import API_KEY  # 🔐 Убедись, что config.py содержит API_KEY
import logging

FOLDER_INPUT = "voice/voice"
FOLDER_OUTPUT = "processed"
FOLDER_TEMP = "uploads"

# Настройка логов
logging.basicConfig(filename="log.txt", level=logging.INFO, format="%(asctime)s - %(message)s")

# Удаление файла
def delete_file_safely(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"🗑 Удалён: {path}")
    except Exception as e:
        print(f"⚠️ Не удалось удалить {path}: {e}")

# Основная транскрипция
def transcribe_audio_file(input_path: str) -> str:
    name, ext = os.path.splitext(os.path.basename(input_path))
    ext = ext.lower().lstrip(".")

    output_txt_path = os.path.join(FOLDER_OUTPUT, f"{name}.txt")
    if os.path.exists(output_txt_path):
        print(f"⏭ Уже обработан: {name}")
        return output_txt_path

    # Конвертация
    success = False
    if ext == "mp3":
        mp3_path = input_path
    else:
        mp3_path = os.path.join(FOLDER_TEMP, f"{name}.mp3")
        try:
            audio = AudioSegment.from_file(input_path, format=ext)
            audio.export(mp3_path, format="mp3")
            print(f"✅ Конвертировано: {mp3_path}")
        except Exception as e:
            print(f"❌ Ошибка конвертации {input_path}: {e}")
            return ""

    try:
        # Загрузка с повторными попытками
        upload_response = None
        for attempt in range(3):
            try:
                with open(mp3_path, "rb") as f:
                    upload_response = requests.post(
                        "https://api.assemblyai.com/v2/upload",
                        headers={"authorization": API_KEY},
                        files={"file": f}
                    )
                upload_response.raise_for_status()
                break
            except Exception as e:
                print(f"⚠️ Попытка загрузки {attempt + 1}/3 не удалась: {e}")
                time.sleep(2)
        else:
            raise RuntimeError(f"Не удалось загрузить {input_path} после 3 попыток.")

        audio_url = upload_response.json()["upload_url"]

        # Запуск транскрипции
        transcribe_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            json={"audio_url": audio_url, "speaker_labels": True, "language_code": "ru"},
            headers={"authorization": API_KEY}
        )
        transcribe_response.raise_for_status()
        transcript_id = transcribe_response.json()["id"]

        # Ожидание завершения
        polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        while True:
            response = requests.get(polling_endpoint, headers={"authorization": API_KEY})
            result = response.json()
            if result["status"] == "completed":
                break
            elif result["status"] == "error":
                raise RuntimeError(result["error"])
            time.sleep(3)

        # Обработка текста
        output_text = ""
        utterances = result.get("utterances")
        if utterances:
            for u in utterances:
                speaker = u.get("speaker", "неизвестный")
                text = u.get("text", "")
                output_text += f"Спикер {speaker}: {text}\n"
        else:
            output_text = result.get("text", "⚠️ Нет текста в ответе от AssemblyAI")

        os.makedirs(FOLDER_OUTPUT, exist_ok=True)
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(output_text)

        print(f"📄 Сохранено: {output_txt_path}")
        success = True
        return output_txt_path

    except Exception as e:
        print(f"❌ Ошибка при обработке {input_path}: {e}")
        logging.error(f"{input_path} - {e}")
        return ""

    finally:
        if success and mp3_path != input_path:
            delete_file_safely(mp3_path)

# Последовательный запуск
if __name__ == "__main__":
    os.makedirs(FOLDER_OUTPUT, exist_ok=True)
    os.makedirs(FOLDER_TEMP, exist_ok=True)

    all_files = [
        os.path.join(FOLDER_INPUT, f)
        for f in os.listdir(FOLDER_INPUT)
        if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg"))
    ]

    print(f"🔍 Найдено {len(all_files)} файлов. Начинаем распознавание...\n")

    if all_files:
        for file in all_files:
            transcribe_audio_file(file)
    else:
        print("⚠️ Нет подходящих файлов для обработки.")