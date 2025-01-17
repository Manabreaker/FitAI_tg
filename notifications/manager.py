# notifications/manager.py

import asyncio
import datetime
from functools import partial
from time import timezone

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db import SessionLocal, User, Notification
from init_bot import bot


scheduler = AsyncIOScheduler()
scheduler.start()


async def _notify_user(tg_id: int, text: str):
    """Отправка уведомления пользователю через Телеграм."""
    # Удаляем markdown-символы, чтобы избежать конфликтов, если в тексте были # или *
    await bot.send_message(chat_id=tg_id, text=text.replace('#', '').replace('*', ''))


def schedule_notification(user_id: int, local_dt_str: str, message: str):
    """
    Создание уведомления для пользователя: конвертируем локальное время
    в UTC и планируем задачу в APS. kind="regular"
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
            message=message,
            kind="regular"
        )
        db_session.add(notif)
        db_session.commit()

        # Планируем задачу
        scheduler.add_job(
            func=partial(asyncio.create_task, _notify_user(user.tg_id, message)),
            trigger='date',
            run_date=dt_utc
        )
    finally:
        db_session.close()


def list_notifications(user_id: int) -> list:
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
            time_str = local_dt.isoformat()  # в формате 2025-01-17T09:00:00+03:00
            result.append({
                "id": n.id,
                "message": n.message,
                "time": time_str
            })
        return result
    finally:
        db_session.close()


def update_notification(user_id: int, notification_id: int,
                        new_message: str = None,
                        new_time_str: str = None):
    """Изменяем уведомление и перезапланируем его отправку."""
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return

        notif = db_session.query(Notification).filter_by(
            id=notification_id,
            user_id=user.id
        ).first()
        if not notif:
            return

        if new_message is not None:
            notif.message = new_message

        if new_time_str is not None:
            try:
                user_tz = pytz.timezone(user.timezone or "UTC")
                local_dt = datetime.datetime.fromisoformat(new_time_str)
                if local_dt.tzinfo is None:
                    local_dt = user_tz.localize(local_dt)
                dt_utc = local_dt.astimezone(pytz.utc)
                notif.time_utc = dt_utc
            except ValueError:
                pass

        db_session.commit()

        # Перезапланируем (упрощённо, без удаления старой задачи) —
        # планируем новую задачу с новыми параметрами
        scheduler.add_job(
            func=partial(asyncio.create_task, _notify_user(user.tg_id, notif.message)),
            trigger='date',
            run_date=notif.time_utc
        )
    finally:
        db_session.close()


def delete_notification(user_id: int, notification_id: int):
    """
    Удаляем уведомление из БД.
    (В APScheduler старое задание не убираем, но оно всё равно не найдёт этот notif впоследствии.)
    """
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return

        notif = db_session.query(Notification).filter_by(
            id=notification_id,
            user_id=user.id
        ).first()
        if notif:
            db_session.delete(notif)
            db_session.commit()
    finally:
        db_session.close()


def schedule_existing_notifications():
    """
    Восстанавливает задачи уведомлений (включая 'inactivity') из БД в Apscheduler.
    """
    db_session = SessionLocal()
    try:
        notifs = db_session.query(Notification).all()
        for notif in notifs:
            user = db_session.query(User).filter_by(id=notif.user_id).first()
            if not user:
                continue

            run_date = notif.time_utc  # время (UTC)
            if notif.kind == "inactivity":
                # Планируем задачу handle_inactivity (см. ниже)
                scheduler.add_job(
                    func=partial(asyncio.create_task, handle_inactivity(user.id)),
                    trigger='date',
                    run_date=run_date
                )
            else:
                # Обычное уведомление

                scheduler.add_job(
                    func=partial(asyncio.create_task, _notify_user(user.tg_id, notif.message)),
                    trigger='date',
                    run_date=run_date
                )
    finally:
        db_session.close()


async def handle_inactivity(user_id: int):
    """
    Функция, которая вызывается, когда истекло 7 дней неактивности.
    """
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return
        user_tg_id = user.tg_id
    finally:
        db_session.close()

    from fit_ai import FitAI  # импортируем здесь, чтобы избежать циклических импортов
    fit_ai = FitAI(user_tg_id)
    response = await fit_ai.chat("Замотивируй меня продолжать занятия спортом и питаться правильно!")
    await bot.send_message(chat_id=user_tg_id, text=response)


def schedule_inactivity_job(user_id: int, days: int = 7):
    """
    Сохраняем (или перезаписываем) задание о неактивности в БД (kind='inactivity').
    По умолчанию days=7 (7 суток).
    """
    db_session = SessionLocal()
    try:
        # Удалим старое уведомление 'inactivity' (если есть)
        existing_notifs = db_session.query(Notification).filter_by(
            user_id=user_id,
            kind='inactivity'
        ).all()
        for old in existing_notifs:
            db_session.delete(old)
        db_session.commit()

        run_date = datetime.datetime.utcnow() + datetime.timedelta(days=days)
        new_notif = Notification(
            user_id=user_id,
            time_utc=run_date,
            message="INACTIVITY_REMINDER",
            kind="inactivity"
        )
        db_session.add(new_notif)
        db_session.commit()

        scheduler.add_job(
            func=partial(asyncio.create_task, handle_inactivity(user_id)),
            trigger='date',
            run_date=run_date
        )

    finally:
        db_session.close()

