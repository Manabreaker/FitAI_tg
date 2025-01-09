from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.utils import executor # - ?
from config import TOKEN
from handlers import registration, menu

# Telegram bot initialization
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=storage)
scheduler = AsyncIOScheduler()

# Register handlers
registration.register_handlers(dp)
menu.register_handlers(dp, scheduler)

if __name__ == "__main__":
    async def main():
        scheduler.start()
        await dp.start_polling()

    import asyncio
    asyncio.run(main())
