# main.py

import asyncio


from db import init_db
from init_bot import bot, dp
from notifications.manager import scheduler, schedule_existing_notifications
from handlers.registration import registration_router
from handlers.menu import menu_router
from handlers.chat import chat_router  # если у вас отдельный чат
# или вы можете оставлять в menu.py — не принципиально



async def on_startup():
    init_db()
    schedule_existing_notifications()
    loop = asyncio.get_running_loop()
    scheduler.configure(event_loop=loop)
    scheduler.start()


async def main():
    # Подключаем роутеры
    dp.include_router(registration_router)
    dp.include_router(menu_router)
    dp.include_router(chat_router)

    # Регистрируем on_startup
    dp.startup.register(on_startup)

    # Запуск поллинга
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
