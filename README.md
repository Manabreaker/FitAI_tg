# FitAI Telegram Bot with GigaChat

Данный проект — асинхронный Telegram-бот, использующий:
- [Aiogram 3+](https://docs.aiogram.dev/)
- [LangChain Community GigaChat](https://github.com/langchain-ai/langchain) для общения
- [SQLAlchemy](https://www.sqlalchemy.org/) для хранения всех данных в **PostgreSQL** (анкета пользователя, лог диалога, уведомления)
- [APSheduler](https://apscheduler.readthedocs.io/en/stable/) для планирования уведомлений

## Запуск

1. Убедитесь, что у вас настроена БД PostgreSQL. Создайте базу и пользователя.
   - Для этого можно использовать `psql` или любой удобный вам инструмент. Пример работы с `psql`:

        _Создайте пользователя с указанным паролем._
        ```bash
        CREATE USER bot_user WITH PASSWORD 'bot_pass';
        ```
        _Создайте базу данных и назначьте владельцем этого пользователя._
        ```bash
        CREATE DATABASE bot_db OWNER bot_user;
        ```
        _Настройте права доступа для пользователя, если потребуется._
        ```bash
        GRANT ALL PRIVILEGES ON DATABASE bot_db TO bot_user;
        ```
     
2. В `config.py` укажите параметры подключения к БД и телеграм-токен.  
3. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```
4. Запустите бота:
   ```bash
   python main.py
   ```
5. В Telegram найдите вашего бота по-указанному токену и нажмите Start.

## Использование

- **/start**: Запуск регистрации. Заполните имя, возраст, пол, вес, рост, цель и уровень.  
- **/menu**: Выводит основные команды.  
- **/meal_plan**: Запросить рацион питания.  
- **/workout_plan**: Запросить программу тренировок.

## Function calling

Внутри system-промпта модель GigaChat знает, что может использовать функцию `notify(...)`. Если она так делает, в сообщение пользователю не попадают эти вызовы напрямую, но в конце добавляется строка: "У вас новое напоминание <date_time> <текст>". Уведомление регистрируется в базе и будет отправлено пользователю в указанное время.

## Структура

```
.
├── config.py            # Параметры Telegram бота и PostgreSQL
├── db.py                # SQLAlchemy-модели, SessionLocal, init_db
├── init_bot.py          # Инициализация бота и диспетчера Aiogram
├── fit_ai.py            # Класс FitAI, логика общения с GigaChat
├── handlers
│   ├── __init__.py
│   ├── menu.py
│   └── registration.py
├── main.py              # Точка входа: запуск бота
├── readme.md
└── requirements.txt
```

---
## Убедитесь, что в `config.py` правильно указаны:

   ```python
   POSTGRES_DB = "bot_db"
   POSTGRES_USER = "bot_user"
   POSTGRES_PASSWORD = "bot_pass"
   POSTGRES_HOST = "localhost"
   POSTGRES_PORT = 5432
   ```

> - При первом запуске таблицы (`users`, `messages`, `notifications`) создаются _автоматически_.

