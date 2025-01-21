import asyncio
from config import debug_mode
from db import init_db
from init_bot import bot, dp
from handlers.registration import registration_router
from handlers.menu import menu_router
from notifications.manager import scheduler, schedule_existing_notifications


# Для отладки Apscheduler
if debug_mode:
    import logging
    logging.basicConfig()
    logging.getLogger("apscheduler").setLevel(logging.DEBUG)

async def main():
    # Инициализация БД
    init_db()

    # Восстанавливаем уведомления из БД
    schedule_existing_notifications()

    # Стартуем планировщик
    scheduler.start()
    if debug_mode:
        print("[main] APScheduler запущен.")

    # Подключаем роутеры
    dp.include_router(registration_router)
    dp.include_router(menu_router)

    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
