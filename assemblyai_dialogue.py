import os
import time
import requests
from pydub import AudioSegment
from config import API_KEY, FOLDER_OUTPUT


async def transcribe_multiple(files: list[str]) -> list[str]:
    results = []
    for file in files:
        txt_path = await transcribe_audio_to_text(file)
        results.append(txt_path)
    return results

async def transcribe_audio_to_text(input_path: str, original_name) -> str:
    """
    Принимает путь к аудиофайлу (любого формата),
    конвертирует в .mp3 (если нужно), отправляет в AssemblyAI
    и сохраняет результат в .txt. Возвращает путь к .txt.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Файл {input_path} не найден.")

    name, ext = os.path.splitext(os.path.basename(input_path))
    ext = ext.lower().lstrip(".")

    # 1. Конвертация в mp3 (если нужно)
    if ext == "mp3":
        mp3_path = input_path  # уже mp3
        print(f"⚠️ Файл уже в mp3: {mp3_path}")
    else:
        mp3_path = os.path.join("uploads", f"{name}.mp3")
        try:
            audio = AudioSegment.from_file(input_path, format=ext)
            audio.export(mp3_path, format="mp3")
            print(f"✅ Конвертировано в mp3: {mp3_path}")
        except Exception as e:
            raise RuntimeError(f"Ошибка конвертации из {ext} в mp3: {e}")

    # 2. Загрузка файла
    with open(mp3_path, "rb") as f:
        upload_response = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers={"authorization": API_KEY},
            files={"file": f}
        )
    audio_url = upload_response.json()["upload_url"]

    # 3. Запуск транскрипции
    transcribe_response = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        json={
            "audio_url": audio_url,
            "speaker_labels": True,
            "language_code": "ru"
        },
        headers={"authorization": API_KEY}
    )
    transcript_id = transcribe_response.json()["id"]

    # 4. Ожидание завершения
    polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    while True:
        response = requests.get(polling_endpoint, headers={"authorization": API_KEY})
        result = response.json()
        if result["status"] == "completed":
            break
        elif result["status"] == "error":
            raise RuntimeError(result["error"])
        time.sleep(3)

        # 5. Обработка текста
    output_text = ""
    utterances = result.get("utterances")

    if utterances:
        for utterance in utterances:
            speaker = utterance.get("speaker", "неизвестный")
            text = utterance.get("text", "")
            output_text += f"Спикер {speaker}: {text}\n"
    else:
        output_text = result.get("text", "⚠️ Нет текста в ответе от AssemblyAI")

    # 6. Сохраняем в файл
    os.makedirs(FOLDER_OUTPUT, exist_ok=True)
    output_txt_path = os.path.join(FOLDER_OUTPUT, f"{original_name}_{name}.txt")
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"📄 Распознанный текст сохранён: {output_txt_path}")
    return output_txt_path