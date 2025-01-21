from aiogram import Router
from aiogram.filters.command import Command
from aiogram.types import Message

from db import SessionLocal, User
from fit_ai import FitAI

menu_router = Router()


async def handle_fitai_request(message: Message, user_text: str):
    user_tg_id = message.from_user.id
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(tg_id=user_tg_id).first()
        if not user:
            await message.answer("Сначала пройдите регистрацию /start.")
            return
    finally:
        db_session.close()

    fit_ai = FitAI(user_tg_id=user_tg_id)
    reply = await fit_ai.chat(user_text)
    await message.answer(reply)


@menu_router.message(Command("menu"))
async def cmd_menu(message: Message):
    text = (
        "Меню FitAI:\n"
        "/meal_plan — Составить рацион\n"
        "/workout_plan — Составить программу тренировок\n"
        "/chat <ваш вопрос> — Начать диалог с FitAI (произвольный вопрос)\n"
    )
    await message.answer(text)


@menu_router.message(Command("meal_plan"))
async def cmd_meal_plan(message: Message):
    user_text = (
        "Составь рацион питания для меня, учитывая мои данные, "
        "(возраст, пол, вес, рост, цель, уровень подготовки). Я хочу чтобы ты составил сбалансированный план питания на каждый день недели.\n"
        "Не задавай дополнительных вопросов, напиши подробный план питания. "
    )
    await handle_fitai_request(message, user_text)


@menu_router.message(Command("workout_plan"))
async def cmd_workout_plan(message: Message):
    user_text = (
        "Составь программу тренировок для меня, учитывая мои данные, "
        "(возраст, пол, вес, рост, цель, уровень подготовки). Я хочу чтобы ты составил сбалансированную программу тренировок на неделю.\n"
        "Не задавай дополнительных вопросов, напиши подробную программу тренировок. "
    )
    await handle_fitai_request(message, user_text)


@menu_router.message(Command("chat"))
async def cmd_chat(message: Message):
    """
    Произвольный диалог с FitAI.
    Пример: /chat Подскажи, как мне перестать есть сладкое?
    """
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Введите вопрос после /chat.")
        return

    user_text = parts[1]
    await handle_fitai_request(message, user_text)

@menu_router.message()
async def chat(message: Message):
    """
    Произвольный диалог с FitAI.
    Пример: /chat Подскажи, как мне перестать есть сладкое?
    """
    await message.answer("Введите вопрос после /chat или воспользуйтесь /menu.")
