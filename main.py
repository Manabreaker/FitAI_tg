# main.py

import asyncio

from aiogram import Bot
from config import TELEGRAM_BOT_TOKEN
from db import init_db
from init_bot import bot, dp
from handlers.registration import registration_router
from handlers.menu import menu_router


async def main():
    # Инициализация БД
    init_db()

    # Подключаем роутеры
    dp.include_router(registration_router)
    dp.include_router(menu_router)

    # Запускаем поллинг
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
