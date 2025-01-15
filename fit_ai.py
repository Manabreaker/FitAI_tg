# fit_ai.py

import re
import datetime
import asyncio
from typing import List

from langchain_community.chat_models import GigaChat
from langchain.schema import SystemMessage, HumanMessage, AIMessage

from db import SessionLocal, User, MessageLog, Notification
from init_bot import bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import GigaChatKey
# Единственный планировщик на всё приложение
scheduler = AsyncIOScheduler()
scheduler.start()


async def _notify_user(tg_id: int, message: str):
    """
    Фактически отправить уведомление пользователю через бота.
    """
    await bot.send_message(chat_id=tg_id, text=message)


def _schedule_notification(tg_id: int, run_date: datetime.datetime, message: str):
    """
    Создать запись в БД и запланировать отправку через APScheduler.
    """
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(tg_id=tg_id).first()
        if not user:
            return  # нет пользователя, не планируем

        notif = Notification(
            user_id=user.id,
            time=run_date,
            message=message
        )
        db_session.add(notif)
        db_session.commit()

        # Добавляем задачу в планировщик
        scheduler.add_job(
            func=asyncio.create_task,
            trigger='date',
            run_date=run_date,
            args=[_notify_user(tg_id, message)]
        )
    finally:
        db_session.close()


class FitAI:
    """
    Класс для общения с GigaChat и управления историей переписки.
    """

    def __init__(self, user_tg_id: int):
        self.user_tg_id = user_tg_id

        # Промпт, где прописываем правила и возможность function calling
        self.system_prompt = (
            "Вы являетесь моделью искусственного интеллекта FitAI и созданы для того, чтобы помогать людям в достижении их спортивных целей. "
            "Вы профессиональный фитнес-тренер и диетолог. Вы создаёте индивидуальные планы питания и программы тренировок на основе информации, введённой пользователем. "
            "Отвечайте только на русском языке, кратко, чётко и структурировано. "
            "Ваши ответы включают порядок выполнения упражнений, количество подходов и повторений, вес снарядов, а также точную граммовку продуктов в рационах питания. "
            "Вы всегда следуете инструкциям пользователя, не задаёте лишних вопросов и не добавляете ненужной информации. "
            "\n\n"
            "Вы можете использовать Function calling (например: notify(2025-05-01 13:45, \"Сходить на тренировку\")) для создания напоминаний пользователю. "
            "Если вы используете Function calling, добавьте в конце ответа строку вида: "
            "notify(2025-05-01 13:45, \"Сходить на тренировку\"). "
            "notify(date_time, message) - создаёт уведомление пользователю в указанное время с указанным текстом. "
            "Эти уведомления будут отправлены пользователю в указанное время. "
            "Если требуется несколько уведомлений, создавайте их по отдельности и добавляйте соответствующие строки в ответ."
        )

        self.llm = GigaChat(
            credentials=GigaChatKey,
            scope="GIGACHAT_API_PERS",  # Для физических лиц
            verify_ssl_certs=False,
            streaming=False
        )

    async def chat(self, user_message: str) -> str:
        """
        Получить ответ от GigaChat, учитывая историю переписки
        (загружаем из БД).
        """
        # Сохраним user_message в БД
        await self._save_message(role="user", content=user_message)

        # Готовим историю для LangChain
        conversation = await self._load_history_as_langchain_messages()
        conversation.insert(0, SystemMessage(content=self.system_prompt))
        conversation.append(HumanMessage(content=user_message))

        # Запрос к GigaChat (синхронный -> asyncio.to_thread)
        response_msg = await asyncio.to_thread(self.llm.predict_messages, conversation)
        assistant_text = response_msg.content

        # Обрабатываем Function calling
        final_text = await self._process_function_calls(assistant_text)

        # Сохраняем ответ ассистента
        await self._save_message(role="assistant", content=final_text)

        return final_text

    async def _save_message(self, role: str, content: str):
        """
        Сохранить сообщение в БД (таблица messages).
        """
        db_session = SessionLocal()
        try:
            user = db_session.query(User).filter_by(tg_id=self.user_tg_id).first()
            if not user:
                return
            msg = MessageLog(
                user_id=user.id,
                role=role,
                content=content
            )
            db_session.add(msg)
            db_session.commit()
        finally:
            db_session.close()

    async def _load_history_as_langchain_messages(self) -> List:
        """
        Загрузить историю сообщений из БД и конвертировать в формат LangChain.
        """
        db_session = SessionLocal()
        try:
            user = db_session.query(User).filter_by(tg_id=self.user_tg_id).first()
            if not user:
                return []

            msgs = (
                db_session.query(MessageLog)
                .filter_by(user_id=user.id)
                .order_by(MessageLog.id.asc())
                .all()
            )

            lc_msgs = []
            for m in msgs:
                if m.role == "system":
                    lc_msgs.append(SystemMessage(content=m.content))
                elif m.role == "assistant":
                    lc_msgs.append(AIMessage(content=m.content))
                elif m.role == "user":
                    lc_msgs.append(HumanMessage(content=m.content))
                else:
                    # fallback
                    lc_msgs.append(HumanMessage(content=m.content))

            return lc_msgs
        finally:
            db_session.close()

    async def _process_function_calls(self, text: str) -> str:
        """
        Ищем notify(YYYY-MM-DD HH:MM, "Текст"), удаляем их из ответа,
        создаём уведомление через APScheduler,
        а в конце добавляем строку "У вас новое напоминание <date_time> <текст>".
        Может быть несколько вызовов.
        """
        pattern = r"notify\(\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*,\s*\"(.*?)\"\s*\)"
        results = re.findall(pattern, text)
        if not results:
            return text

        final_text = text
        reminder_lines = []

        for (datetime_str, msg_text) in results:
            # Удаляем сам вызов из текста
            func_call_str = f'notify({datetime_str}, "{msg_text}")'
            final_text = final_text.replace(func_call_str, "")

            # Пробуем распарсить дату/время
            dt_format = "%Y-%m-%d %H:%M"
            try:
                run_date = datetime.datetime.strptime(datetime_str, dt_format)
            except ValueError:
                # некорректный формат, пропускаем
                continue

            # Создаём уведомление
            _schedule_notification(self.user_tg_id, run_date, msg_text)

            reminder_lines.append(f"У вас новое напоминание {datetime_str} {msg_text}")

        # Чистим от лишних пробелов/переносов
        final_text = re.sub(r"\s+", " ", final_text).strip()

        # Добавляем строчки про напоминания
        if reminder_lines:
            final_text += "\n" + "\n".join(reminder_lines)

        return final_text
