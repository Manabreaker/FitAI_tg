# handlers/menu.py

from aiogram import Router
from aiogram.filters.command import Command
from aiogram.types import Message

from db import SessionLocal, User
from fit_ai import FitAI

menu_router = Router()


async def handle_fitai_request(message: Message, user_text: str):
    """
    Общая функция для обработки запроса к FitAI:
    1. Проверяем, зарегистрирован ли пользователь.
    2. Если да — создаём FitAI и отправляем запрос.
    3. Возвращаем ответ пользователю.
    """
    user_tg_id = message.from_user.id

    # Проверяем, есть ли пользователь в базе
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(tg_id=user_tg_id).first()
        if not user:
            await message.answer("Сначала пройдите регистрацию /start")
            return
    finally:
        db_session.close()

    # Создаём FitAI
    fit_ai = FitAI(user_tg_id=user_tg_id)
    reply = await fit_ai.chat(user_text)
    await message.answer(reply)


@menu_router.message(Command("menu"))
async def cmd_menu(message: Message):
    text = (
        "Меню FitAI:\n"
        "/meal_plan — Составить рацион\n"
        "/workout_plan — Составить программу тренировок\n"
        "/chat <ваш вопрос> — Начать диалог с FitAI\n"
    )
    await message.answer(text)


@menu_router.message(Command("meal_plan"))
async def cmd_meal_plan(message: Message):
    # Текст-запрос к ИИ
    user_text = (
        "Составь рацион питания для меня, учитывая все мои данные: "
        "возраст, пол, вес, рост, уровень, цель."
    )
    # Асинхронно обрабатываем запрос
    await handle_fitai_request(message, user_text)


@menu_router.message(Command("workout_plan"))
async def cmd_workout_plan(message: Message):
    # Текст-запрос к ИИ
    user_text = (
        "Составь для меня программу тренировок, "
        "учитывая все мои параметры и цель."
    )
    await handle_fitai_request(message, user_text)


@menu_router.message(Command("chat"))
async def cmd_chat(message: Message):
    """
    Команда для любого произвольного вопроса к FitAI.
    Пример использования: /chat Привет, подскажи, как начать бегать?
    """
    # Извлекаем текст запроса (всё, что после /chat)
    # Если пользователь ввёл только "/chat" - проверим этот случай
    user_text_parts = message.text.strip().split(maxsplit=1)
    if len(user_text_parts) < 2:
        await message.answer("Пожалуйста, введите вопрос после команды /chat.")
        return

    user_text = user_text_parts[1]
    await handle_fitai_request(message, user_text)
