# handlers/registration.py

from aiogram import Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.command import Command

from db import SessionLocal, User
from sqlalchemy.exc import IntegrityError

registration_router = Router()

class RegistrationForm(StatesGroup):
    name = State()
    age = State()
    sex = State()
    weight = State()
    height = State()
    goal = State()
    skill = State()
    timezone = State()

@registration_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await message.answer("Добро пожаловать! Укажите ваше имя:")
    await state.set_state(RegistrationForm.name)

@registration_router.message(RegistrationForm.name)
async def handle_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите ваш возраст (число):")
    await state.set_state(RegistrationForm.age)

@registration_router.message(RegistrationForm.age)
async def handle_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if not (1 <= age <= 120):
            raise ValueError
        await state.update_data(age=age)

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="Мужской", callback_data="sex_Мужской"),
                InlineKeyboardButton(text="Женский", callback_data="sex_Женский")
            ]]
        )
        await message.answer("Ваш пол:", reply_markup=kb)
        await state.set_state(RegistrationForm.sex)
    except ValueError:
        await message.answer("Введите корректный возраст (1-120).")

@registration_router.callback_query(RegistrationForm.sex, lambda c: c.data.startswith("sex_"))
async def handle_sex(callback: CallbackQuery, state: FSMContext):
    sex_value = callback.data.split("_", 1)[1]
    await state.update_data(sex=sex_value)
    await callback.message.answer("Введите ваш вес (кг):")
    await callback.answer()
    await state.set_state(RegistrationForm.weight)

@registration_router.message(RegistrationForm.weight)
async def handle_weight(message: Message, state: FSMContext):
    try:
        w = float(message.text)
        if w <= 0 or w > 500:
            raise ValueError
        await state.update_data(weight=w)
        await message.answer("Введите ваш рост (см):")
        await state.set_state(RegistrationForm.height)
    except ValueError:
        await message.answer("Введите корректный вес (число >0 и <500).")

@registration_router.message(RegistrationForm.height)
async def handle_height(message: Message, state: FSMContext):
    try:
        h = float(message.text)
        if h <= 0 or h > 300:
            raise ValueError
        await state.update_data(height=h)

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="Похудеть", callback_data="goal_Похудеть"),
                InlineKeyboardButton(text="Набрать массу", callback_data="goal_Набрать массу"),
                InlineKeyboardButton(text="Поддерживать форму", callback_data="goal_Поддерживать форму")
            ]]
        )
        await message.answer("Какая у вас цель?", reply_markup=kb)
        await state.set_state(RegistrationForm.goal)
    except ValueError:
        await message.answer("Введите корректный рост (число >0 и <300).")

@registration_router.callback_query(RegistrationForm.goal, lambda c: c.data.startswith("goal_"))
async def handle_goal(callback: CallbackQuery, state: FSMContext):
    goal_value = callback.data.split("_", 1)[1]
    await state.update_data(goal=goal_value)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Новичок", callback_data="skill_Новичок")],
            [InlineKeyboardButton(text="Средний", callback_data="skill_Средний")],
            [InlineKeyboardButton(text="Продвинутый", callback_data="skill_Продвинутый")]
        ]
    )
    await callback.message.answer("Ваш уровень подготовки?", reply_markup=kb)
    await callback.answer()
    await state.set_state(RegistrationForm.skill)

@registration_router.callback_query(RegistrationForm.skill, lambda c: c.data.startswith("skill_"))
async def handle_skill(callback: CallbackQuery, state: FSMContext):
    skill_value = callback.data.split("_", 1)[1]
    await state.update_data(skill=skill_value)

    # Предлагаем выбрать часовой пояс
    tz_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="UTC", callback_data="tz_UTC")],
            [InlineKeyboardButton(text="Europe/Moscow", callback_data="tz_Europe/Moscow")],
            [InlineKeyboardButton(text="Asia/Almaty", callback_data="tz_Asia/Almaty")]
        ]
    )
    await callback.message.answer("Выберите ваш часовой пояс:", reply_markup=tz_kb)
    await callback.answer()
    await state.set_state(RegistrationForm.timezone)

@registration_router.callback_query(RegistrationForm.timezone, lambda c: c.data.startswith("tz_"))
async def handle_timezone(callback: CallbackQuery, state: FSMContext):
    tz_value = callback.data.split("_", 1)[1]
    await state.update_data(timezone=tz_value)

    data = await state.get_data()
    tg_id = callback.from_user.id

    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(tg_id=tg_id).first()
        if not user:
            user = User(
                tg_id=tg_id,
                name=data["name"],
                age=data["age"],
                sex=data["sex"],
                weight=data["weight"],
                height=data["height"],
                goal=data["goal"],
                skill=data["skill"],
                timezone=data["timezone"]
            )
            db_session.add(user)
        else:
            user.name = data["name"]
            user.age = data["age"]
            user.sex = data["sex"]
            user.weight = data["weight"]
            user.height = data["height"]
            user.goal = data["goal"]
            user.skill = data["skill"]
            user.timezone = data["timezone"]
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
        await callback.message.answer("Ошибка записи данных в БД.")
    finally:
        db_session.close()

    await callback.message.answer(
        "Регистрация завершена!\n"
        f"Имя: {data['name']}\n"
        f"Возраст: {data['age']}\n"
        f"Пол: {data['sex']}\n"
        f"Вес: {data['weight']} кг\n"
        f"Рост: {data['height']} см\n"
        f"Цель: {data['goal']}\n"
        f"Уровень: {data['skill']}\n"
        f"Часовой пояс: {data['timezone']}\n\n"
        "Теперь вы можете использовать команду /menu"
    )
    await callback.answer()
    await state.clear()
