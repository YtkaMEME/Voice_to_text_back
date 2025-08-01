from aiogram import F, Router
from aiogram.types import (
    Message, WebAppInfo, ReplyKeyboardMarkup,
    KeyboardButton, ReplyKeyboardRemove, FSInputFile
)
from aiogram.fsm.context import FSMContext
import os
import asyncio

from bot.FSM import FileUploadState
from db_manager import DBManager

router = Router()
PROCESSED_FOLDER = "processed"
db = DBManager()

@router.message(F.text == "/start")
async def start_command(message: Message, state: FSMContext):
    await state.set_state(FileUploadState.waiting_upload)
    await state.update_data(saved_message=message)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(
            text="Загрузить файлы",
            web_app=WebAppInfo(url="https://fearlessly-jocular-bowfin.cloudpub.ru/")
        )]],
        resize_keyboard=True
    )

    expected_count = db.get_expected_files_count(message.from_user.id)
    await message.answer("👋 Привет! Нажми кнопку ниже, чтобы загрузить аудиофайл:", reply_markup=keyboard)

    if expected_count > 0:
        asyncio.create_task(watch_and_send_ready_files(message, state, expected_count))


async def watch_and_send_ready_files(message: Message, state: FSMContext, expected_count: int):
    user_id = message.from_user.id

    await message.answer(f"⏳ Ожидаем {expected_count} файл(ов)...")

    for _ in range(60):  # до 5 минут ожидания
        await asyncio.sleep(5)

        transcript_name = db.get_pending_file(user_id)
        if transcript_name:
            file_path = os.path.join(PROCESSED_FOLDER, str(user_id), transcript_name)
            if os.path.exists(file_path):
                document = FSInputFile(path=file_path, filename=transcript_name)
                await message.answer_document(
                    document=document,
                    caption=f"🎧 Расшифровка файла: <b>{transcript_name}</b>",
                    parse_mode="HTML"
                )
                try:
                    os.remove(file_path)
                except Exception as e:
                    await message.answer(f"⚠️ Ошибка при удалении: {e}")

                db.delete_file_record(user_id, transcript_name)
                expected_count -= 1

        if expected_count <= 0:
            await message.answer("✅ Все файлы отправлены!", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            return

    await message.answer("⌛ Ожидание закончилось. Все доступные файлы отправлены.")
    await state.clear()