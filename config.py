# Telegram Bot token
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_TOKEN" # Токен бота Telegram (получать у @BotFather)

# Режим отладки (логирование)
debug_mode = True

# Параметры PostgreSQL
POSTGRES_DB = "bot_db"
POSTGRES_USER = "bot_user"
POSTGRES_PASSWORD = "bot_pass"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432

#  URI подключения к SQLAlchemy
SQLALCHEMY_DATABASE_URI = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# GigaChat API key
GigaChatKey = "YOUR_GIGACHAT_API_KEY" # API-ключ GigaChat (получать на сайте https://developers.sber.ru/studio/workspaces/my-space/get/gigachat-api)
