# fit_ai.py

import asyncio
import datetime
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_gigachat import GigaChat  # Или другая LLM
from db import SessionLocal, User, MessageLog
from config import GigaChatKey

class FitAI:
    """
    Класс для общения с GigaChat (или другой LLM).
    Не используем function calling для уведомлений:
    в этом примере делаем напоминания сами, без LLM.
    """

    def __init__(self, user_tg_id: int):
        self.user_tg_id = user_tg_id
        self.db_session = SessionLocal()
        self.user = self.db_session.query(User).filter_by(tg_id=user_tg_id).first()

        # Создаём GigaChat
        self.llm = GigaChat(
            model="GigaChat",
            credentials=GigaChatKey,
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False,
            streaming=False,
            temperature=0.5
        )

    async def chat(self, user_message: str) -> str:
        if not self.user:
            return "Пользователь не найден. Сначала пройдите регистрацию."

        # Пример system prompt
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        user_info = (
            f"Имя: {self.user.name}, "
            f"Возраст: {self.user.age}, "
            f"Пол: {self.user.sex}, "
            f"Вес: {self.user.weight}, Рост: {self.user.height}, "
            f"Цель: {self.user.goal}, Уровень: {self.user.skill}, "
            f"Часовой пояс: {self.user.timezone}, "
            f"Текущее (UTC): {now_utc}"
        )
        system_text = (
            "Ты — FitAI, профессиональный фитнес-тренер и диетолог. "
            "Отвечай по-русски, кратко и структурированно.\n\n"
            f"Данные пользователя: {user_info}\n"
        )

        conversation = await self._load_history_as_langchain_messages()
        conversation.insert(0, SystemMessage(content=system_text))
        conversation.append(HumanMessage(content=user_message))

        assistant_response = await asyncio.to_thread(self.llm.invoke, conversation)
        assistant_text = assistant_response.content

        # Сохраняем user_message
        await self._save_message(role="user", content=user_message)
        # Сохраняем ассистента
        await self._save_message(role="assistant", content=assistant_text)

        return assistant_text

    async def _save_message(self, role: str, content: str):
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        uid = self.user.id if self.user else None
        msg = MessageLog(
            user_id=uid,
            role=role,
            content=content,
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
            if m.role == "assistant":
                lc_messages.append(AIMessage(content=m.content))
            elif m.role == "system":
                lc_messages.append(SystemMessage(content=m.content))
            else:
                lc_messages.append(HumanMessage(content=m.content))
        return lc_messages

    def __del__(self):
        self.db_session.close()
