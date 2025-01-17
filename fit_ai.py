import asyncio
import datetime
import json
import re

import pytz  # Для работы с часовыми поясами
from functools import partial
from langchain.schema import SystemMessage, HumanMessage, AIMessage

from langchain_community.chat_models import GigaChat
from config import GigaChatKey
from db import SessionLocal, User, MessageLog, Notification
from init_bot import bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler


# ---------------------------
# Глобальное хранилище для
# "заданий неактивности"
# user_tg_id -> job_id (str)
# ---------------------------
inactivity_jobs = {}

scheduler = AsyncIOScheduler()
scheduler.start()


async def _notify_user(tg_id: int, text: str):
    """Отправка уведомления пользователю через Телеграм."""
    await bot.send_message(chat_id=tg_id, text=text.replace('#', ''), parse_mode='Markdown')


def _schedule_notification(user_id: int, local_dt_str: str, message: str):
    """
    Создание уведомления для пользователя: конвертируем локальное время
    в UTC и планируем задачу в APS.
    """
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return

        user_tz_name = user.timezone or "UTC"
        user_tz = pytz.timezone(user_tz_name)

        try:
            local_dt = datetime.datetime.fromisoformat(local_dt_str)
            if local_dt.tzinfo is None:
                local_dt = user_tz.localize(local_dt)
        except ValueError:
            return

        dt_utc = local_dt.astimezone(pytz.utc)

        notif = Notification(
            user_id=user.id,
            time_utc=dt_utc,
            message=message
        )
        db_session.add(notif)
        db_session.commit()

        scheduler.add_job(
            func=partial(asyncio.create_task, _notify_user(user.tg_id, message)),
            trigger='date',
            run_date=dt_utc
        )
    finally:
        db_session.close()


def _list_notifications(user_id: int) -> list:
    """
    Возвращаем список уведомлений пользователя в локальном времени.
    """
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return []

        notifs = db_session.query(Notification).filter_by(user_id=user.id).all()
        result = []
        for n in notifs:
            user_tz_name = user.timezone or "UTC"
            user_tz = pytz.timezone(user_tz_name)
            local_dt = n.time_utc.astimezone(user_tz)
            time_str = local_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
            result.append({
                "id": n.id,
                "message": n.message,
                "time": time_str
            })
        return result
    finally:
        db_session.close()


def _update_notification(user_id: int, notification_id: int,
                         new_message: str = None,
                         new_time_str: str = None):
    """Изменяем уведомление и перезапланируем его отправку."""
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return

        notif = db_session.query(Notification).filter_by(id=notification_id, user_id=user.id).first()
        if not notif:
            return

        if new_message is not None:
            notif.message = new_message

        if new_time_str is not None:
            try:
                local_dt = datetime.datetime.fromisoformat(new_time_str)
                if local_dt.tzinfo is None:
                    user_tz = pytz.timezone(user.timezone or "UTC")
                    local_dt = user_tz.localize(local_dt)
                dt_utc = local_dt.astimezone(pytz.utc)
                notif.time_utc = dt_utc
            except ValueError:
                pass

        db_session.commit()

        # Перезапланируем (упрощённо, без удаления старой задачи)
        scheduler.add_job(
            func=partial(asyncio.create_task, _notify_user(user.tg_id, notif.message)),
            trigger='date',
            run_date=notif.time_utc
        )
    finally:
        db_session.close()


def _delete_notification(user_id: int, notification_id: int):
    """Удаляем уведомление из БД (в APScheduler старое задание не убираем)."""
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return

        notif = db_session.query(Notification).filter_by(id=notification_id, user_id=user.id).first()
        if notif:
            db_session.delete(notif)
            db_session.commit()
    finally:
        db_session.close()


async def handle_inactivity(user_tg_id: int):
    """
    Функция, которая вызывается после 7 дней неактивности пользователя.
    Генерирует мотивацию "замотивируй меня..." от имени пользователя
    и отправляет ответ реальному пользователю.
    """
    fit_ai = FitAI(user_tg_id)
    # "Системно" отправляем сообщение от имени пользователя,
    # чтобы вызвать логику chat()
    response = await fit_ai.chat("Замотивируй меня начать правильно питаться и заниматься спортом!")
    # Отправим результат реальному пользователю
    # (если модель вернёт function_call, цикл продолжится и в итоге всё же вернётся final_answer)
    user = fit_ai.user
    if user:
        await bot.send_message(chat_id=user.tg_id, text=response)


def schedule_inactivity_job(user_tg_id: int, days: int = 7):
    """
    Ставим (или перезапускаем) задание в планировщике на неактивность.
    Если юзер не напишет ничего в течение days, сработает handle_inactivity.
    """
    # Удаляем старое задание, если было
    old_job_id = inactivity_jobs.get(user_tg_id)
    if old_job_id:
        try:
            scheduler.remove_job(old_job_id)
        except:
            pass

    run_date = datetime.datetime.now() + datetime.timedelta(days=days)
    new_job = scheduler.add_job(
        func=partial(asyncio.create_task, handle_inactivity(user_tg_id)),
        trigger='date',
        run_date=run_date
    )
    inactivity_jobs[user_tg_id] = new_job.id


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
                            "description": "Время (ISO8601) локального ч.п. или со смещением"
                        }
                    },
                    "required": ["user_id", "message", "time"]
                }
            },
            {
                "name": "list_notifications",
                "description": "Возвращает список всех уведомлений для пользователя",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "ID пользователя"
                        }
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "update_notification",
                "description": "Изменяет текст или время уведомления по его ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "ID пользователя"
                        },
                        "notification_id": {
                            "type": "integer",
                            "description": "ID уведомления"
                        },
                        "message": {
                            "type": "string",
                            "description": "Новый текст уведомления (необязательно)",
                            "nullable": True
                        },
                        "time": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Новое время (ISO8601) (необязательно)",
                            "nullable": True
                        }
                    },
                    "required": ["user_id", "notification_id"]
                }
            },
            {
                "name": "delete_notification",
                "description": "Удаляет уведомление по его ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "ID пользователя"
                        },
                        "notification_id": {
                            "type": "integer",
                            "description": "ID уведомления"
                        }
                    },
                    "required": ["user_id", "notification_id"]
                }
            }
        ]

        self.llm = GigaChat(
            model="GigaChat",
            credentials=GigaChatKey,
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False,
            streaming=False,
            temperature=0.5
        )

    async def chat(self, user_message: str) -> str:
        """Основной метод диалога."""
        if not self.user:
            return "Пользователь не найден. Сначала пройдите регистрацию."

        # Каждый раз, когда пользователь/приложение вызывает chat(...),
        # мы перезапускаем таймер неактивности на 7 дней:
        schedule_inactivity_job(self.user_tg_id, days=7)

        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        user_info = (
            f"Имя: {self.user.name}, "
            f"user_id: {self.user.id}, "
            f"Возраст: {self.user.age}, "
            f"Пол: {self.user.sex}, "
            f"Вес: {self.user.weight}кг, Рост: {self.user.height}см, "
            f"Цель: {self.user.goal}, Уровень: {self.user.skill}, "
            f"Часовой пояс: {self.user.timezone}, "
            f"Текущее время (UTC): {now_utc}"
        )

        user_message += '\n Сообщение отправлено в ' + datetime.datetime.now().isoformat()

        system_text = (
            "Вы являетесь моделью искусственного интеллекта FitAI и созданы для того, чтобы помогать людям в достижении их спортивных целей. "
            "Вы профессиональный фитнес-тренер и диетолог. Вы создаёте индивидуальные планы питания и программы тренировок на основе информации, введённой пользователем. "
            "Отвечайте только на русском языке, кратко, чётко и структурировано. "
            "Ваши ответы включают порядок выполнения упражнений, количество подходов и повторений, вес снарядов, а также точную граммовку продуктов в рационах питания. "
            "Вы всегда следуете инструкциям пользователя, не задаёте лишних вопросов и не добавляете ненужной информации.\n\n"
            "Вы умеете работать с уведомлениями (создание, просмотр, изменение, удаление).\n\n"
            "Если вы вызываете функцию(ии), напишите только JSON без лишнего текста. При использовании функций не нужно писать обычный текст ответа для пользователя. "
            "Если функция выполнена, вы получите system-сообщение 'Функция выполнена успешно' — после этого вы можете отправить ответ пользователю.\n\n"
            f"Данные о пользователе:\n{user_info}\n"
            f"Данные о функциях:\n{self.functions_schemas}"
        )

        conversation = await self._load_history_as_langchain_messages()
        conversation.insert(0, SystemMessage(content=system_text))
        conversation.append(HumanMessage(content=user_message))

        assistant_response = await asyncio.to_thread(self.llm.invoke, conversation)
        assistant_text = assistant_response.content

        # Сохраняем входящее сообщение пользователя
        await self._save_message(role="user", content=user_message)

        final_answer = ""
        while True:
            # Ищем функции
            function_calls = self._extract_multiple_json_objects(assistant_text)

            if not function_calls:
                # Обычный текст
                await self._save_message(role="assistant", content=assistant_text)
                final_answer = assistant_text
                break

            # Сохраняем ответ ассистента как есть (но не показываем пользователю напрямую)
            await self._save_message(role="assistant", content=assistant_text)

            # Обрабатываем каждую функцию
            for fc in function_calls:
                fname = fc.get("name")
                # Исправление: берём параметры из "parameters", а не "arguments"
                fargs = fc.get("parameters", {})

                await self._save_message(
                    role="assistant",
                    content="(function_call)",
                    function_name=fname,
                    function_args=json.dumps(fargs, ensure_ascii=False)
                )

                if fname == "create_notification":
                    user_id_str = fargs.get("user_id")
                    msg_text = fargs.get("message")
                    time_str = fargs.get("time")
                    if user_id_str and msg_text and time_str:
                        try:
                            uid_int = int(user_id_str)
                            _schedule_notification(uid_int, time_str, msg_text)
                        except ValueError:
                            pass

                elif fname == "list_notifications":
                    user_id_str = fargs.get("user_id")
                    if user_id_str:
                        try:
                            uid_int = int(user_id_str)
                            notifs = _list_notifications(uid_int)
                            # Делаем "обратную связь" для модели:
                            # добавляем "сообщение" о списке уведомлений
                            # как если бы пользователь ответил модельке
                            # (чтобы она могла среагировать в следующем шаге)
                            conversation.append(HumanMessage(
                                content=f"NOTIFICATION_LIST={json.dumps(notifs, ensure_ascii=False)}"
                            ))
                        except ValueError:
                            pass

                elif fname == "update_notification":
                    user_id_str = fargs.get("user_id")
                    notification_id = fargs.get("notification_id")
                    new_msg = fargs.get("message")
                    new_time = fargs.get("time")
                    if user_id_str and notification_id is not None:
                        try:
                            uid_int = int(user_id_str)
                            _update_notification(uid_int, notification_id, new_msg, new_time)
                        except ValueError:
                            pass

                elif fname == "delete_notification":
                    user_id_str = fargs.get("user_id")
                    notification_id = fargs.get("notification_id")
                    if user_id_str and notification_id is not None:
                        try:
                            uid_int = int(user_id_str)
                            _delete_notification(uid_int, notification_id)
                        except ValueError:
                            pass

            # Добавляем "от пользователя" сообщение: "Функция выполнена успешно"
            conversation.append(HumanMessage(content="Функция выполнена успешно."))

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
            elif m.role == "user":
                lc_messages.append(HumanMessage(content=m.content))
            else:
                lc_messages.append(HumanMessage(content=m.content))
        return lc_messages

    def _extract_multiple_json_objects(self, text: str):
        """
        Извлекаем все подряд JSON-объекты (или массив [ {..}, {..} ]),
        учитывая, что модель может присылать их в разном формате.
        """
        # Удаляем тройные кавычки
        clean_text = re.sub(r"```(?:json)?(.*?)```", r"\1", text, flags=re.DOTALL).strip()
        results = []

        # Сперва пробуем как массив
        arr = self._try_parse_json(clean_text)
        if isinstance(arr, list):
            for item in arr:
                if isinstance(item, dict):
                    results.append(item)
            if results:
                return results

        # Если не массив — пробуем извлечь несколько подряд { } { }
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

        # Может быть один объект
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
