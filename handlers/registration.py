import os

from aiogram import types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import user_data_path
from fit_ai import FitAI

# Словарь для хранения клиентов FitAI, привязанных к каждому пользователю
user_ai_clients = {}

# Определение состояний для Finite State Machine (FSM)
class RegistrationForm(StatesGroup):
    name = State()
    age = State()
    sex = State()
    weight = State()
    height = State()
    goal = State()
    skill = State()

# Регистрация обработчиков
def register_handlers(dp):
    @dp.message_handler(commands=['start'])
    async def start_handler(message: types.Message):
        await message.answer("Добро пожаловать! Укажите ваше имя:")
        await RegistrationForm.name.set()

    @dp.message_handler(state=RegistrationForm.name)
    async def name_handler(message: types.Message, state: FSMContext):
        await state.update_data(name=message.text)
        await message.answer("Введите ваш возраст:")
        await RegistrationForm.age.set()

    @dp.message_handler(state=RegistrationForm.age)
    async def age_handler(message: types.Message, state: FSMContext):
        try:
            age = int(message.text)
            if age < 1 or age > 120:
                raise ValueError
            await state.update_data(age=age)
            keyboard = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("Мужской", callback_data="sex_Мужской"),
                InlineKeyboardButton("Женский", callback_data="sex_Женский")
            )
            await message.answer("Ваш пол (выберите из предложенных вариантов):", reply_markup=keyboard)
            await RegistrationForm.sex.set()
        except ValueError:
            await message.answer("Введите корректный возраст (число от 1 до 120):")

    @dp.callback_query_handler(lambda c: c.data.startswith("sex_"), state=RegistrationForm.sex)
    async def sex_handler(callback_query: types.CallbackQuery, state: FSMContext):
        sex = callback_query.data.split("_")[1]
        await state.update_data(sex=sex)
        await callback_query.message.answer("Введите ваш вес (в кг):")
        await callback_query.answer()
        await RegistrationForm.weight.set()

    @dp.message_handler(state=RegistrationForm.weight)
    async def weight_handler(message: types.Message, state: FSMContext):
        try:
            weight = float(message.text)
            if weight <= 0 or weight > 500:
                raise ValueError
            await state.update_data(weight=weight)
            await message.answer("Введите ваш рост (в см):")
            await RegistrationForm.height.set()
        except ValueError:
            await message.answer("Введите корректный вес (число больше 0 и меньше 500):")

    @dp.message_handler(state=RegistrationForm.height)
    async def height_handler(message: types.Message, state: FSMContext):
        try:
            height = float(message.text)
            if height <= 0 or height > 300:
                raise ValueError
            await state.update_data(height=height)
            keyboard = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("Похудеть", callback_data="goal_похудеть"),
                InlineKeyboardButton("Набрать массу", callback_data="goal_набрать массу"),
                InlineKeyboardButton("Поддерживать форму", callback_data="goal_поддерживать форму")
            )
            await message.answer("Какова ваша цель? (выберите из предложенных вариантов):", reply_markup=keyboard)
            await RegistrationForm.goal.set()
        except ValueError:
            await message.answer("Введите корректный рост (число больше 0 и меньше 300):")

    @dp.callback_query_handler(lambda c: c.data.startswith("goal_"), state=RegistrationForm.goal)
    async def goal_handler(callback_query: types.CallbackQuery, state: FSMContext):
        goal = callback_query.data.split("_")[1]
        await state.update_data(goal=goal)
        keyboard = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("Новичок", callback_data="skill_Новичок"),
            InlineKeyboardButton("Средний", callback_data="skill_Средний"),
            InlineKeyboardButton("Продвинутый", callback_data="skill_Продвинутый")
        )
        await callback_query.message.answer("Каков ваш уровень подготовки? (выберите из предложенных вариантов):", reply_markup=keyboard)
        await callback_query.answer()
        await RegistrationForm.skill.set()

    @dp.callback_query_handler(lambda c: c.data.startswith("skill_"), state=RegistrationForm.skill)
    async def skill_handler(callback_query: types.CallbackQuery, state: FSMContext):
        skill = callback_query.data.split("_")[1]

        # Завершение регистрации
        user_data = await state.get_data()
        user_data['skill'] = skill
        user_id = callback_query.from_user.id

        # Создание клиента FitAI
        user_ai_clients[user_id] = FitAI(
            user_id=user_id,
            user_name=user_data['name'],
            user_age=user_data['age'],
            user_sex=user_data['sex'],
            user_weight=user_data['weight'],
            user_height=user_data['height'],
            user_goal=user_data['goal'],
            user_skill=user_data['skill']
        )

        user_file_path = os.path.join(user_data_path, f"{user_id}.txt")
        with open(user_file_path, "w", encoding="utf-8") as file:
            file.write(
                f"[system] Вы являетесь моделью искусственного интеллекта FItAI и созданы для того чтобы помогать людям в достижении их спортивных целей. Вы профессиональный фитнес-тренер и диетолог. Вы создаете индивидуальные планы питания и программы тренировок на основе информации, введенной пользователем. Вы всегда следуете инструкциям пользователя. Помните, что отвечать нужно только на русском языке. И постарайтесь не задавать лишних вопросов, строго следовать указаниям пользователя и не делать ничего лишнего. Ваш ответ всегда краток, ясен и хорошо структурирован. Вы всегда указываете порядок выполнения упражнений их количество и граммовку еды в тренировках и рационах.\n" +
                f"[assistant] Привет! Я ваш персональный фитнес ассистент, FitAI. Я помогу вам в достижении ваших целей в области фитнеса и правильного питания. В чем вам нужна помощь сегодня?\n" +
                f"[user] Привет! Меня зовут: {user_data['name']}, моя цель это {user_data['goal']}. Уровень подготовки: {user_data['skill']}. Вес: {user_data['weight']} кг, рост: {user_data['height']} см, возраст: {user_data['age']}, пол: {user_data['sex']}.\n"
            )


        # Подтверждение завершения регистрации
        await callback_query.message.answer(
            f"Регистрация завершена! Вот ваши данные:\n"
            f"id: {user_id}\n"
            f"Имя: {user_data['name']}\n"
            f"Возраст: {user_data['age']}\n"
            f"Пол: {user_data['sex']}\n"
            f"Вес: {user_data['weight']} кг\n"
            f"Рост: {user_data['height']} см\n"
            f"Цель: {user_data['goal']}\n"
            f"Уровень: {user_data['skill']}\n\n"
            f"Теперь вы можете воспользоваться меню с помощью команды /menu."
        )
        await callback_query.answer()
        await state.finish()
