import os
from g4f.client import AsyncClient
from config import g4f_model_name, TestMode, user_data_path
from typing import List, Dict

class FitAI:
    def __init__(self, model_name: str = g4f_model_name, messages: List[Dict] = None,
                 user_name: str = 'Пользователь не указал своё имя',
                 user_goal: str = 'поддержание формы', user_id: int = None,
                 user_age: int = None,
                 user_sex: str = 'Пользователь не указал свой пол',
                 user_weight: float = None,
                 user_height: float = None,
                 user_skill: str = 'Пользователь не указал свой уровень подготовки',
                 user_data_path: str = user_data_path):
        self.user_skill = user_skill
        self.user_name = user_name
        self.model_name = model_name
        self.user_goal = user_goal
        self.user_id = user_id
        self.user_age = user_age
        self.user_sex = user_sex
        self.user_weight = user_weight
        self.user_height = user_height
        self.client = AsyncClient()
        self.messages = [
            {
                'role': 'system',
                'content': "Вы являетесь моделью искусственного интеллекта FItAI и созданы для того чтобы помогать людям в достижении их спортивных целей. Вы профессиональный фитнес-тренер и диетолог. Вы создаете индивидуальные планы питания и программы тренировок на основе информации, введенной пользователем. Вы всегда следуете инструкциям пользователя. Помните, что отвечать нужно только на русском языке. И постарайтесь не задавать лишних вопросов, строго следовать указаниям пользователя и не делать ничего лишнего. Ваш ответ всегда краток, ясен и хорошо структурирован. Вы всегда указываете порядок выполнения упражнений их количество и граммовку еды в тренировках и рационах."
            },
            {
                'role': 'assistant',
                'content': "Привет! Я ваш персональный фитнес ассистент, FitAI. Я помогу вам в достижении ваших целей в области фитнеса и правильного питания. В чем вам нужна помощь сегодня?"
            },
            {
                'role': 'user',
                'content': f"Привет! Меня зовут: {self.user_name}, моя цель это {self.user_goal}. Уровень подготовки: {self.user_skill}. Вес: {self.user_weight} кг, рост: {self.user_height} см, возраст: {self.user_age}, пол: {self.user_sex}."
            }
        ]

        # Создание папки для хранения данных пользователей
        self.user_data_path = user_data_path
        os.makedirs(self.user_data_path, exist_ok=True)
        self.user_file_path = os.path.join(self.user_data_path, f"{self.user_id}.txt")

        if TestMode:
            print("FitAI instance created")
            print(f"User ID: {self.user_id}")
            print(f"User name: {self.user_name}")
            print(f"User age: {self.user_age}")
            print(f"User sex: {self.user_sex}")
            print(f"User weight: {self.user_weight}")
            print(f"User height: {self.user_height}")
            print(f"User goal: {self.user_goal}")
            print(f"User skill: {self.user_skill}")

    def log_message(self, role: str, content: str):
        with open(self.user_file_path, "a", encoding="utf-8") as file:
            content = content.replace("\n", "\n\t")
            file.write(f"[{role}] {content}.\n")

    async def generate_meal_plan(self) -> str:
        message = f"Составь рацион питания для меня. Учти, моя цель: {self.user_goal}. Уровень подготовки: {self.user_skill}. Вес: {self.user_weight} кг, рост: {self.user_height} см, возраст: {self.user_age}, пол: {self.user_sex}."
        response = await self.chat_with_fitai(user_message=message)
        return response

    async def generate_workout_plan(self) -> str:
        message = f"Составь программу тренировок для меня. Учти, моя цель: {self.user_goal}. Уровень подготовки: {self.user_skill}. Вес: {self.user_weight} кг, рост: {self.user_height} см, возраст: {self.user_age}, пол: {self.user_sex}."
        response = await self.chat_with_fitai(user_message=message)
        return response

    async def chat_with_fitai(self, user_message: str) -> str:
        try:
            self.log_message("user", user_message)
            self.messages.append({
                'role': 'user',
                'content': user_message
            })
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=self.messages
            )
            assistant_message = response.choices[0].message.content
            self.messages.append({
                'role': 'assistant',
                'content': assistant_message
            })
            self.log_message("assistant", assistant_message)
            if TestMode:
                print(f"Новое сообщение пользователя:\n\t{user_message}")
                print(f"Ответ ассистента:\n{assistant_message}".replace('\n', '\n\t'))
            return assistant_message.replace('#', '')
        except Exception as e:
            error_message = f"Извините, произошла ошибка при общении с FitAI. 😔 Попробуйте ещё раз или повторите позже."
            self.log_message("error", str(e))
            if TestMode:
                print(f"Error in chat response: {e}")
            return error_message
