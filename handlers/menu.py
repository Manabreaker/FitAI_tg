# handlers/menu.py

from aiogram import Router
from aiogram.filters.command import Command
from aiogram.types import Message

from db import SessionLocal, User
from fit_ai import FitAI

menu_router = Router()

@menu_router.message(Command("menu"))
async def cmd_menu(message: Message):
    text = (
        "Меню FitAI:\n"
        "/meal_plan — Составить рацион\n"
        "/workout_plan — Составить программу тренировок\n"
        "/chat <ваш вопрос> — Задать вопрос FitAI (либо «напомни ...»)\n"
    )
    await message.answer(text)

@menu_router.message(Command("meal_plan"))
async def cmd_meal_plan(message: Message):
    user_tg_id = message.from_user.id
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(tg_id=user_tg_id).first()
        if not user:
            await message.answer("Сначала пройдите регистрацию /start.")
            return
    finally:
        db_session.close()

    # Здесь просто обращаемся к FitAI за примерным рационом
    fit_ai = FitAI(user_tg_id)
    reply = await fit_ai.chat("Составь рацион питания с учетом моих данных.")
    await message.answer(reply)

@menu_router.message(Command("workout_plan"))
async def cmd_workout_plan(message: Message):
    user_tg_id = message.from_user.id
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(tg_id=user_tg_id).first()
        if not user:
            await message.answer("Сначала пройдите регистрацию /start.")
            return
    finally:
        db_session.close()

    fit_ai = FitAI(user_tg_id)
    reply = await fit_ai.chat("Составь программу тренировок с учетом моих данных.")
    await message.answer(reply)
