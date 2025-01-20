# init_bot.py


from aiogram.client.bot import Bot, DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import TELEGRAM_BOT_TOKEN



bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
