import asyncio
import datetime
import json
import re

from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_community.chat_models import GigaChat

from db import SessionLocal, User, MessageLog
from config import GigaChatKey

# Импортируем функции из function_calling
from function_calling.manager import (
    create_notification_fn
)

# Импортируем «неактивность» из notifications
from notifications.manager import schedule_inactivity_job


class FitAI:
    """
    Класс для общения с GigaChat и управления function calling.
    """

    def __init__(self, user_tg_id: int):
        self.user_tg_id = user_tg_id
        self.db_session = SessionLocal()
        self.user = self.db_session.query(User).filter_by(tg_id=user_tg_id).first()

        self.functions_schemas = [
            {
                "name": "create_notification",
                "description": "Создает новое уведомление для пользователя",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "ID пользователя (числовой ID)"
                        },
                        "message": {
                            "type": "string",
                            "description": "Текст уведомления"
                        },
                        "time": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Локальное время (ISO8601), например: 2025-01-18T14:00:00+03:00"
                        }
                    },
                    "required": ["user_id", "message", "time"]
                }
            }]
#            {
#                "name": "list_notifications",
#                "description": "Возвращает список всех уведомлений для пользователя",
#                "parameters": {
#                    "type": "object",
#                    "properties": {
#                        "user_id": {
#                            "type": "string",
#                            "description": "ID пользователя"
#                        }
#                    },
#                    "required": ["user_id"]
#                }
#            },
#            {
#                "name": "update_notification",
#                "description": "Изменяет текст или время уведомления по его ID",
#                "parameters": {
#                    "type": "object",
#                    "properties": {
#                        "user_id": {
#                            "type": "string",
#                            "description": "ID пользователя"
#                        },
#                        "notification_id": {
#                            "type": "integer",
#                            "description": "ID уведомления"
#                        },
#                        "message": {
#                            "type": "string",
#                            "description": "Новый текст уведомления (необязательно)",
#                            "nullable": True
#                        },
#                        "time": {
#                            "type": "string",
#                            "format": "date-time",
#                            "description": "Новое время (ISO8601) (необязательно)",
#                            "nullable": True
#                        }
#                    },
#                    "required": ["user_id", "notification_id"]
#                }
#            },
#            {
#                "name": "delete_notification",
#                "description": "Удаляет уведомление по его ID",
#                "parameters": {
#                    "type": "object",
#                    "properties": {
#                        "user_id": {
#                            "type": "string",
#                            "description": "ID пользователя"
#                        },
#                        "notification_id": {
#                            "type": "integer",
#                            "description": "ID уведомления"
#                        }
#                    },
#                    "required": ["user_id", "notification_id"]
#                }
#            }
#        ]

        self.llm = GigaChat(
            model="GigaChat",
            credentials=GigaChatKey,
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False,
            streaming=False,
            temperature=0.5
        )

    async def chat(self, user_message: str) -> str:
        """Основной метод диалога с моделью."""
        if not self.user:
            return "Пользователь не найден. Сначала пройдите регистрацию."

        # При каждом новом сообщении «обнуляем» таймер неактивности
        schedule_inactivity_job(self.user.id, days=7)

        # Подготовим system prompt:
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        current_weekday_utc = ('Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье')[
            datetime.datetime.now(datetime.timezone.utc).weekday()]
        user_info = (
            f"Имя: {self.user.name}, "
            f"user_id: {self.user.id}, "
            f"Возраст: {self.user.age}, "
            f"Пол: {self.user.sex}, "
            f"Вес: {self.user.weight}кг, Рост: {self.user.height}см, "
            f"Цель: {self.user.goal}, Уровень: {self.user.skill}, "
            f"Часовой пояс: {self.user.timezone}, "
            f"Текущее время и день недели (UTC): {now_utc, current_weekday_utc} "
        )
        current_weekday = ('Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье')[
            datetime.datetime.now().weekday()]
        user_message += f'\n Сообщение отправлено в: {datetime.datetime.now().isoformat()} {current_weekday}\n'

        system_text = (
            "Вы — FitAI, профессиональный фитнес-тренер и диетолог. "
            "Отвечайте на русском, кратко и структурировано. "
            "Составляете планы тренировок и питания, даете советы и отвечаете на вопросы связанные с фитнесом и диетой. "
            "Умеете вызывать функцию create_notification. "
            "Если используете функцию, верните ТОЛЬКО JSON, без дополнительного текста. "
            "После выполнения функции сможете продолжить ответ.\n\n"
            f"Данные о пользователе:\n{user_info}\n"
            f"Схемы функций:\n{self.functions_schemas}"
            "\n\n"
            "Примеры использования функции:\n"
            "   {\n"
            "       \"name\": \"create_notification\",\n"
            "       \"parameters\": {\n"
            "           \"user_id\": \"1\",\n"
            "           \"message\": \"Напоминание: время тренировки подошло!\",\n"
            "           \"time\": \"2025-01-17T09:00:00+03:00\"\n"
            "       }\n"
            "   }\n\n"
            "Если нужно вызвать функцию, вы должны вернуть JSON, как в примере."
            "Обязательно учитывайте timezone пользователя при планировании уведомлений."
        )

        # Превращаем историю диалога в LangChain-месседжи
        conversation = await self._load_history_as_langchain_messages()
        conversation.insert(0, SystemMessage(content=system_text))
        conversation.append(HumanMessage(content=user_message))

        # Вызываем GigaChat
        assistant_response = await asyncio.to_thread(self.llm.invoke, conversation)
        assistant_text = assistant_response.content

        # Сохраняем входящее сообщение пользователя (role="user")
        user_message += '\n Сообщение отправлено в ' + datetime.datetime.now().isoformat()
        await self._save_message(role="user", content=user_message)

        final_answer = ""
        while True:
            # Ищем JSON-функции
            function_calls = self._extract_multiple_json_objects(assistant_text)

            if not function_calls:
                # Нет функций — обычный ответ от ассистента
                await self._save_message(role="assistant", content=assistant_text)
                final_answer = assistant_text
                break

            # Сохраняем ответ ассистента (как он есть, без отправки юзеру)
            await self._save_message(role="assistant", content=assistant_text)

            # Выполняем каждую функцию
            for fc in function_calls:
                fname = fc.get("name")
                fargs = fc.get("parameters", {})

                # Сохраняем отдельным сообщением запись о вызове функции
                await self._save_message(
                    role="user",
                    content=f"Функция была вызвана успешно. Теперь ты сообщишь об этом пользователю! Сказав, что все прошло успешно! Текущее время: {datetime.datetime.now().isoformat()}",
                    function_name=fname,
                    function_args=json.dumps(fargs, ensure_ascii=False)
                )

                if fname == "create_notification":
                    create_notification_fn(
                        user_id_str=fargs.get("user_id", ""),
                        msg_text=fargs.get("message", ""),
                        time_str=fargs.get("time", "")
                    )
                """
                Далее функции для работы с уведомлениями (CRUD) в БД,
                которые убрали из functions_calling и промпта т.к.
                GigaChat ими все равно не пользуется, но они захламляют его помять.
                """
                ### elif fname == "list_notifications":
                ###     notifs = list_notifications_fn(fargs.get("user_id", ""))
                ###     # Чтобы модель могла «увидеть» результат,
                ###     # добавляем новое HumanMessage со списком
                ###     conversation.append(HumanMessage(
                ###         content=f"NOTIFICATION_LIST={json.dumps(notifs, ensure_ascii=False)}"
                ###     ))

                ### elif fname == "update_notification":
                ###     update_notification_fn(
                ###         user_id_str=fargs.get("user_id", ""),
                ###         notification_id=fargs.get("notification_id", None),
                ###         new_msg=fargs.get("message", None),
                ###         new_time=fargs.get("time", None)
                ###     )

                ### elif fname == "delete_notification":
                ###     delete_notification_fn(
                ###         user_id_str=fargs.get("user_id", ""),
                ###         notification_id=fargs.get("notification_id", None)
                ###     )

            # Даем модели «переосмыслить» после выполнения функций
            conversation = await self._load_history_as_langchain_messages()
            # conversation.append(HumanMessage(content="Функция выполнена успешно."))
            new_response = await asyncio.to_thread(self.llm.invoke, conversation)
            assistant_text = new_response.content

        return final_answer

    async def _save_message(self, role: str, content: str,
                            function_name: str = None, function_args: str = None):
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        uid = self.user.id if self.user else None
        msg = MessageLog(
            user_id=uid,
            role=role,
            content=content,
            function_name=function_name,
            function_args=function_args,
            timestamp_utc=now_utc
        )
        self.db_session.add(msg)
        self.db_session.commit()

    async def _load_history_as_langchain_messages(self):
        if not self.user:
            return []

        msgs = (
            self.db_session.query(MessageLog)
            .filter_by(user_id=self.user.id)
            .order_by(MessageLog.id.asc())
            .all()
        )
        lc_messages = []
        for m in msgs:
            if m.role == "system":
                lc_messages.append(SystemMessage(content=m.content))
            elif m.role == "assistant":
                lc_messages.append(AIMessage(content=m.content))
            else:  # user
                lc_messages.append(HumanMessage(content=m.content))

        return lc_messages

    def _extract_multiple_json_objects(self, text: str):
        # Удаляем markdown-блоки ```json
        clean_text = re.sub(r"```(?:json)?(.*?)```", r"\1", text, flags=re.DOTALL).strip()
        results = []

        # 1) Пробуем как единый JSON-массив
        arr = self._try_parse_json(clean_text)
        if isinstance(arr, list):
            for item in arr:
                if isinstance(item, dict):
                    results.append(item)
            if results:
                return results

        # 2) Пробуем искать { } { }
        remaining = clean_text
        while True:
            remaining = remaining.lstrip()
            if not remaining.startswith("{"):
                break
            obj, consumed_len = self._parse_first_json_object(remaining)
            if not obj:
                break
            results.append(obj)
            remaining = remaining[consumed_len:]

        # 3) Может быть один объект
        if not results:
            single_obj = self._try_parse_json(clean_text)
            if isinstance(single_obj, dict):
                results.append(single_obj)

        return results

    def _try_parse_json(self, raw_text: str):
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            return None

    def _parse_first_json_object(self, raw_text: str):
        bracket_stack = 0
        end_idx = 0
        for i, ch in enumerate(raw_text):
            if ch == '{':
                bracket_stack += 1
            elif ch == '}':
                bracket_stack -= 1
                if bracket_stack == 0:
                    end_idx = i
                    break
        if bracket_stack != 0:
            return None, 0
        candidate = raw_text[:end_idx+1]
        try:
            obj = json.loads(candidate)
            return (obj, end_idx+1)
        except json.JSONDecodeError:
            return None, 0

    def __del__(self):
        self.db_session.close()
