import asyncio
from db import init_db
from init_bot import bot, dp
from handlers.registration import registration_router
from handlers.menu import menu_router
from fit_ai import schedule_existing_notifications

async def main():
    # Инициализация БД
    init_db()
    schedule_existing_notifications()
    # Подключаем роутеры
    dp.include_router(registration_router)
    dp.include_router(menu_router)

    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
