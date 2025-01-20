# config.py

# Telegram Bot token
TELEGRAM_BOT_TOKEN = "8181910423:AAFN536a9ZdQsnIh2SB1bZBHMArCoViDS_M"

# Параметры PostgreSQL
POSTGRES_DB = "bot_db"
POSTGRES_USER = "bot_user"
POSTGRES_PASSWORD = "bot_pass"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432

# URI подключения к SQLAlchemy
SQLALCHEMY_DATABASE_URI = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# GigaChat API key
GigaChatKey = "ZTYwYmEwYmYtODUzMC00Y2Q5LTk4ZDktNmVkYzg5NGM3YzdkOmMwNzYwZWY5LWRhMzEtNGFiZS1hNTQyLTYyNGVkOTlkMGRlYQ=="
