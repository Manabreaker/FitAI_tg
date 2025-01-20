# handlers/chat.py

import re
import datetime
import pytz
from aiogram import Router
from aiogram.types import Message
from aiogram.filters.command import Command
from db import SessionLocal, User
from notifications.manager import schedule_notification, schedule_inactivity_job
from fit_ai import FitAI

chat_router = Router()

@chat_router.message(Command("chat"))
async def cmd_chat(message: Message):
    """
    Если текст содержит "напомни" — пытаемся распарсить время,
    иначе всё уходит в FitAI (LLM) как обычный вопрос.
    """
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Введите вопрос/сообщение после /chat.")
        return

    user_text = parts[1].lower()
    user_tg_id = message.from_user.id

    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(tg_id=user_tg_id).first()
        if not user:
            await message.answer("Сначала пройдите регистрацию /start.")
            return
        user_id = user.id
        user_tz_name = user.timezone or "UTC"
    finally:
        db_session.close()

    # 1. Сбрасываем таймер неактивности на 7 дней
    schedule_inactivity_job(user_id)

    # 2. Проверяем, есть ли в тексте "напомни"
    if "напомни" in user_text or "создай напоминание" in user_text:
        # Пример крайне простого парсинга: ищем "через X минут"
        # Вы можете улучшать (рег. выражения, dateparser, etc.)
        # Здесь для примера: "через 5 минут" или "через 2 часа"
        # ... или "в 15:00" — код для демонстрации
        found = re.search(r"через\s+(\d+)\s*(минут|минуты|минута)", user_text)
        if found:
            delta_minutes = int(found.group(1))
            # Локальное время пользователя
            tz = pytz.timezone(user_tz_name)
            now_local = datetime.datetime.now(tz)
            future_local = now_local + datetime.timedelta(minutes=delta_minutes)
            iso_time = future_local.isoformat()

            schedule_notification(user_id, iso_time, "Ваше напоминание!")
            await message.answer(f"Создал напоминание через {delta_minutes} минут.")
            return

        found_hours = re.search(r"через\s+(\d+)\s*(час|часа|часов)", user_text)
        if found_hours:
            delta_hours = int(found_hours.group(1))
            tz = pytz.timezone(user_tz_name)
            now_local = datetime.datetime.now(tz)
            future_local = now_local + datetime.timedelta(hours=delta_hours)
            iso_time = future_local.isoformat()

            schedule_notification(user_id, iso_time, "Ваше напоминание!")
            await message.answer(f"Создал напоминание через {delta_hours} часов.")
            return

        # Если шаблон не найден — сообщим, что мы не поняли
        await message.answer(
            "Не понял время для напоминания. Укажите, например: 'напомни через 10 минут'."
        )
    else:
        # 3. Если не "напомни", отправляем в LLM (FitAI)
        fit_ai = FitAI(user_tg_id)
        reply = await fit_ai.chat(parts[1])
        await message.answer(reply)
