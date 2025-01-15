# init_bot.py

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import TELEGRAM_BOT_TOKEN

# Создаём общий Bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Памятное хранилище (FSM)
storage = MemoryStorage()

# Создаём Dispatcher без указания бота на момент инициализации
# (согласно рекомендуемому подходу Aiogram 3.17)
dp = Dispatcher(storage=storage)
