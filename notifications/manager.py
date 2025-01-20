# notifications/manager.py

import asyncio
import datetime
import pytz


from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor

from db import SessionLocal, User, Notification
from init_bot import bot



# Создаём планировщик c указанием executors={"default": AsyncIOExecutor()}
# Это значит, что все задачи будут выполняться в том же event loop, что и наш бот.
scheduler = AsyncIOScheduler(
    timezone=pytz.utc,
    executors={"default": AsyncIOExecutor()}
)
# Обратите внимание, что .start() мы будем вызывать в main.py после configure()

async def _notify_user(tg_id: int, text: str):
    """
    Асинхронная функция отправки уведомления.
    APScheduler сможет вызвать её напрямую, т.к. мы используем AsyncIOExecutor.
    """

    await bot.send_message(chat_id=tg_id, text=text)

async def handle_inactivity(user_id: int):
    """
    Вызывается, если 7 дней не было сообщений.
    Тоже асинхронно.
    """

    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:

            return
        user_tg_id = user.tg_id
    finally:
        db_session.close()

    # Здесь просто отправим сообщение
    await bot.send_message(
        chat_id=user_tg_id,
        text="Вы не были активны 7 дней! Пора вернуться к тренировкам и правильному питанию!"
    )

def schedule_notification(user_id: int, local_dt_str: str, message: str):
    """
    Планируем обычное уведомление (kind="regular").
    local_dt_str — локальное время пользователя (ISO8601).
    """

    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:

            return

        user_tz = pytz.timezone(user.timezone or "UTC")
        try:
            local_dt = datetime.datetime.fromisoformat(local_dt_str)
            if local_dt.tzinfo is None:
                local_dt = user_tz.localize(local_dt)
        except ValueError:

            return

        dt_utc = local_dt.astimezone(pytz.utc)
        now_utc = datetime.datetime.now(pytz.utc)
        if dt_utc <= now_utc:
            return

        notif = Notification(
            user_id=user.id,
            time_utc=dt_utc,
            message=message,
            kind="regular"
        )
        db_session.add(notif)
        db_session.commit()


        # Теперь планируем задачу (асинхронную) напрямую
        scheduler.add_job(
            _notify_user,
            trigger='date',
            run_date=dt_utc,
            args=[user.tg_id, message],
            misfire_grace_time=60  # На случай, если сработало чуть позже
        )

    finally:
        db_session.close()

def schedule_inactivity_job(user_id: int, days: int = 7):
    """
    Планируем уведомление об неактивности (kind="inactivity").
    Ставим run_date = текущее время + days.
    """

    db_session = SessionLocal()
    try:
        # Удаляем старые inactivity
        olds = db_session.query(Notification).filter_by(
            user_id=user_id,
            kind='inactivity'
        ).all()
        for old in olds:
            db_session.delete(old)
        db_session.commit()

        run_date = datetime.datetime.now(tz=pytz.utc) + datetime.timedelta(days=days)
        new_notif = Notification(
            user_id=user_id,
            time_utc=run_date,
            message="INACTIVITY_REMINDER",
            kind="inactivity"
        )
        db_session.add(new_notif)
        db_session.commit()



        scheduler.add_job(
            handle_inactivity,
            trigger='date',
            run_date=run_date,
            args=[user_id],
            misfire_grace_time=60
        )
    finally:
        db_session.close()

def schedule_existing_notifications():

    db_session = SessionLocal()
    try:
        notifs = db_session.query(Notification).all()
        now_utc = datetime.datetime.now(tz=pytz.utc)

        for n in notifs:
            user = db_session.query(User).filter_by(id=n.user_id).first()
            if not user:
                ...
                continue

            # Принудительно делаем offset-aware, если tzinfo == None
            if n.time_utc.tzinfo is None:
                n.time_utc = pytz.utc.localize(n.time_utc)
                # Можно сохранить это обновление в БД,
                # чтобы в будущем всегда были aware-значения:
                db_session.add(n)
                db_session.commit()

            if n.time_utc <= now_utc:

                continue

            if n.kind == 'inactivity':
                scheduler.add_job(
                    handle_inactivity,
                    trigger='date',
                    run_date=n.time_utc,
                    args=[n.user_id],
                    misfire_grace_time=60
                )
                ...
            else:
                scheduler.add_job(
                    _notify_user,
                    trigger='date',
                    run_date=n.time_utc,
                    args=[user.tg_id, n.message],
                    misfire_grace_time=60
                )
                ...
    finally:
        db_session.close()

