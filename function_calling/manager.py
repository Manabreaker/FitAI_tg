from notifications.manager import schedule_notification


def create_notification_fn(user_id_str: str, msg_text: str, time_str: str):
    """
    Обёртка для вызова schedule_notification
    """
    try:
        uid_int = int(user_id_str)
        schedule_notification(uid_int, time_str, msg_text)
    except ValueError:
        pass

"""
Далее функции для работы с уведомлениями (CRUD) в БД,
которые убрали из functions_calling и промпта т.к.
GigaChat ими все равно не пользуется, но они захламляют его помять.
"""
# def list_notifications_fn(user_id_str: str) -> list:
#     """
#     Обёртка для list_notifications
#     """
#     try:
#         uid_int = int(user_id_str)
#         return list_notifications(uid_int)
#     except ValueError:
#         return []
#
#
# def update_notification_fn(user_id_str: str,
#                            notification_id: int,
#                            new_msg: str = None,
#                            new_time: str = None):
#     """
#     Обёртка для update_notification
#     """
#     try:
#         uid_int = int(user_id_str)
#         update_notification(uid_int, notification_id, new_msg, new_time)
#     except ValueError:
#         pass
#
#
# def delete_notification_fn(user_id_str: str,
#                            notification_id: int):
#     """
#     Обёртка для delete_notification
#     """
#     try:
#         uid_int = int(user_id_str)
#         delete_notification(uid_int, notification_id)
#     except ValueError:
#         pass
#