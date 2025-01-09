from aiogram import types
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from handlers.registration import user_ai_clients  # Импорт словаря клиентов

def register_handlers(dp, scheduler):
    @dp.message_handler(commands=['menu'])
    async def menu_handler(message: types.Message):
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("Составление рациона"),
            KeyboardButton("Составление программы тренировок"),
            KeyboardButton("Чат с FitAI")
        )
        await message.answer("Главное меню:", reply_markup=keyboard)

    @dp.message_handler(lambda message: message.text == "Составление программы тренировок")
    async def workout_plan_handler(message: types.Message):
        user_id = message.from_user.id
        ai_client = user_ai_clients.get(user_id)
        if ai_client:
            workout_plan = await ai_client.generate_workout_plan()
            await message.answer(f"Ваша программа тренировок:\n{workout_plan}", parse_mode="Markdown")
        else:
            await message.answer("Вы не прошли регистрацию. Используйте команду /start.")

    @dp.message_handler(lambda message: message.text == "Составление рациона")
    async def meal_plan_handler(message: types.Message):
        user_id = message.from_user.id
        ai_client = user_ai_clients.get(user_id)
        if ai_client:
            meal_plan = await ai_client.generate_meal_plan()
            await message.answer(f"Ваш рацион питания:\n{meal_plan}", parse_mode="Markdown")
        else:
            await message.answer("Вы не прошли регистрацию. Используйте команду /start.")

    @dp.message_handler(lambda message: message.text == "Чат с FitAI")
    async def chat_handler(message: types.Message):
        user_id = message.from_user.id
        ai_client = user_ai_clients.get(user_id)
        if ai_client:
            await message.answer("Привет! Я ваш персональный фитнес ассистент, FitAI. Я помогу вам в достижении ваших целей в области фитнеса и правильного питания. В чем вам нужна помощь сегодня?")
        else:
            await message.answer("Вы не прошли регистрацию. Используйте команду /start.")

    @dp.message_handler()
    async def default_chat_handler(message: types.Message):
        user_id = message.from_user.id
        ai_client = user_ai_clients.get(user_id)
        if ai_client:
            response = await ai_client.chat_with_fitai(message.text)
            await message.answer(response, parse_mode="Markdown")
        else:
            await message.answer("Вы не прошли регистрацию. Используйте команду /start.")
