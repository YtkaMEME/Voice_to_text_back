import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers import router


# Инициализация бота и хранилища состояния
bot = Bot(token="7341869078:AAF3u9rHAcHFiwMUvlIzTbqyqIT0gOhHvvs")

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключаем маршруты
dp.include_router(router)


async def main():
    """Запуск polling и инициализация бота"""
    await bot.delete_webhook(drop_pending_updates=True)  # Удаляем старый webhook, если был
    await dp.start_polling(bot)  # Запускаем бота в режиме polling


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("❌ Бот остановлен.")