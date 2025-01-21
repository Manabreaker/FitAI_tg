import datetime
import pytz

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor
from db import SessionLocal, User, Notification
from init_bot import bot


scheduler = AsyncIOScheduler(
    timezone=pytz.utc,
    executors={"default": AsyncIOExecutor()}
)

# Внимание: Чтобы планировщик начал работать нужно вызывать в main.py (или аналогичном месте),

async def _notify_user(tg_id: int, text: str):
    """
    Асинхронная функция отправки уведомления пользователю Telegram.
    APScheduler вызовет её напрямую, поскольку мы используем AsyncIOExecutor.
    """
    text = text.replace('#', '').replace('*', '') # убираем спецсимволы MD
    try:
        await bot.send_message(chat_id=tg_id, text=text, parse_mode="Markdown")
    except Exception as e:
        print(f"[NOTIFY] Ошибка при отправке уведомления пользователю tg_id={tg_id}: {e}")


async def handle_inactivity(user_id: int):
    """
    Вызывается, если 7 дней не было сообщений от пользователя (inactivity).
    Тоже асинхронная функция.
    """
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return
        user_tg_id = user.tg_id
    finally:
        db_session.close()

    # Простой пример: отправка "Вы не были активны 7 дней! ..."
    try:
        await bot.send_message(
            chat_id=user_tg_id,
            text="Вы не были активны 7 дней! Пора вернуться к тренировкам и правильному питанию!"
        )
    except Exception as e:
        print(f"[INACTIVITY] Ошибка при отправке сообщения о неактивности: {e}")


def schedule_notification(user_id: int, local_dt_str: str, message: str):
    """
    Планируем ОДНО уведомление (kind="regular").
    local_dt_str — локальное время пользователя в формате ISO8601.
      Пример: "2025-01-17T09:00:00+03:00" или без смещения, тогда добавляем user.timezone.
    """
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return

        # Определяем его часовой пояс или UTC
        user_tz = pytz.timezone(user.timezone or "UTC")

        # Парсим локальное время
        try:
            local_dt = datetime.datetime.fromisoformat(local_dt_str)
            if local_dt.tzinfo is None:
                local_dt = user_tz.localize(local_dt)
        except ValueError:
            return

        # Конвертируем в UTC
        dt_utc = local_dt.astimezone(pytz.utc) + datetime.timedelta(seconds=10)
        now_utc = datetime.datetime.now(pytz.utc)
        if dt_utc <= now_utc:
            return

        # Создаём Notification в БД
        notif = Notification(
            user_id=user.id,
            time_utc=dt_utc,
            message=message,
            kind="regular"
        )
        db_session.add(notif)
        db_session.commit()

        # Планируем задачу (асинхронную) в Apscheduler
        scheduler.add_job(
            _notify_user,
            trigger='date',
            run_date=dt_utc,
            args=[user.tg_id, message],
            misfire_grace_time=60
        )

    finally:
        db_session.close()


def schedule_inactivity_job(user_id: int, days: int = 7):
    """
    Планируем уведомление о неактивности (kind="inactivity").
    То есть если пользователь не напишет боту в течение N дней, высылаем предупреждение.
    """
    db_session = SessionLocal()
    try:
        # Сначала удаляем старые 'inactivity' записи
        olds = db_session.query(Notification).filter_by(
            user_id=user_id,
            kind='inactivity'
        ).all()
        for old in olds:
            db_session.delete(old)
        db_session.commit()

        # Создаём новую
        run_date = datetime.datetime.now(tz=pytz.utc) + datetime.timedelta(days=days)
        new_notif = Notification(
            user_id=user_id,
            time_utc=run_date,
            message="INACTIVITY_REMINDER",
            kind="inactivity"
        )
        db_session.add(new_notif)
        db_session.commit()

        # Планируем задачу
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
    """
    При старте бота (или перезапуске) восстанавливаем задачи:
    1. Читаем все уведомления из БД (regular, inactivity).
    2. Для будущих дат снова добавляем задачи в Apscheduler.
    """
    db_session = SessionLocal()
    try:
        notifs = db_session.query(Notification).all()
        now_utc = datetime.datetime.now(tz=pytz.utc)

        for n in notifs:
            user = db_session.query(User).filter_by(id=n.user_id).first()
            if not user:
                continue

            # Приводим время к UTC (aware), если вдруг tzinfo = None
            if n.time_utc.tzinfo is None:
                n.time_utc = pytz.utc.localize(n.time_utc)
                db_session.add(n)
                db_session.commit()

            if n.time_utc <= now_utc:
                # Считаем, что время уже прошло — не планируем.
                continue

            if n.kind == 'inactivity':
                scheduler.add_job(
                    handle_inactivity,
                    trigger='date',
                    run_date=n.time_utc,
                    args=[n.user_id],
                    misfire_grace_time=60
                )
            else:
                # Обычное уведомление
                scheduler.add_job(
                    _notify_user,
                    trigger='date',
                    run_date=n.time_utc,
                    args=[user.tg_id, n.message],
                    misfire_grace_time=60
                )

    finally:
        db_session.close()


"""
Далее функции для работы с уведомлениями (CRUD) в БД,
которые убрали из functions_calling и промпта т.к.
GigaChat ими все равно не пользуется, но они захламляют его помять.
"""
# def list_notifications(user_id: int) -> list:
#     """
#     Возвращаем список уведомлений пользователя в локальном времени.
#     """
#     db_session = SessionLocal()
#     try:
#         user = db_session.query(User).filter_by(id=user_id).first()
#         if not user:
#             return []
#
#         notifs = db_session.query(Notification).filter_by(user_id=user.id).all()
#         result = []
#         for n in notifs:
#             user_tz_name = user.timezone or "UTC"
#             user_tz = pytz.timezone(user_tz_name)
#             local_dt = n.time_utc.astimezone(user_tz)
#             time_str = local_dt.isoformat()  # в формате 2025-01-17T09:00:00+03:00
#             result.append({
#                 "id": n.id,
#                 "message": n.message,
#                 "time": time_str
#             })
#         return result
#     finally:
#         db_session.close()
#
# def delete_notification(user_id: int, notification_id: int):
#     """
#     Удаляем уведомление из БД.
#     (В APScheduler старое задание не убираем, но оно всё равно не найдёт этот notif впоследствии.)
#     """
#     db_session = SessionLocal()
#     try:
#         user = db_session.query(User).filter_by(id=user_id).first()
#         if not user:
#             return
#
#         notif = db_session.query(Notification).filter_by(
#             id=notification_id,
#             user_id=user.id
#         ).first()
#         if notif:
#             db_session.delete(notif)
#             db_session.commit()
#     finally:
#         db_session.close()
#
# def update_notification(user_id: int, notification_id: int,
#                         new_message: str = None,
#                         new_time_str: str = None):
#     """Изменяем уведомление и перезапланируем его отправку."""
#     db_session = SessionLocal()
#     try:
#         user = db_session.query(User).filter_by(id=user_id).first()
#         if not user:
#             return
#
#         notif = db_session.query(Notification).filter_by(
#             id=notification_id,
#             user_id=user.id
#         ).first()
#         if not notif:
#             return
#
#         if new_message is not None:
#             notif.message = new_message
#
#         if new_time_str is not None:
#             try:
#                 user_tz = pytz.timezone(user.timezone or "UTC")
#                 local_dt = datetime.datetime.fromisoformat(new_time_str)
#                 if local_dt.tzinfo is None:
#                     local_dt = user_tz.localize(local_dt)
#                 dt_utc = local_dt.astimezone(pytz.utc)
#                 notif.time_utc = dt_utc
#             except ValueError:
#                 pass
#
#         db_session.commit()
#
#         # Перезапланируем (упрощённо, без удаления старой задачи) —
#         # планируем новую задачу с новыми параметрами
#         scheduler.add_job(
#             func=partial(asyncio.create_task, _notify_user(user.tg_id, notif.message)),
#             trigger='date',
#             run_date=notif.time_utc
#         )
#     finally:
#         db_session.close()