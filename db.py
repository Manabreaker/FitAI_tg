# db.py

import datetime
from sqlalchemy import (
    create_engine, Column, Integer, Float, String,
    DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from config import SQLALCHEMY_DATABASE_URI

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg_id = Column(Integer, unique=True, nullable=False)  # Telegram user ID
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    sex = Column(String, nullable=False)
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    goal = Column(String, nullable=True)
    skill = Column(String, nullable=True)
    timezone = Column(String, nullable=True, default="UTC")  # Часовой пояс
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    # relationships
    messages = relationship("MessageLog", back_populates="user")
    notifications = relationship("Notification", back_populates="user")


class MessageLog(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # "system" / "user" / "assistant"
    role = Column(String, nullable=False)

    content = Column(Text, nullable=False)

    timestamp_utc = Column(DateTime, default=datetime.datetime.utcnow)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="messages")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Время напоминания (UTC)
    time_utc = Column(DateTime, nullable=False)
    message = Column(String, nullable=False)
    kind = Column(String, default="regular")  # "regular" или "inactivity"

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="notifications")


engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def init_db():
    Base.metadata.create_all(bind=engine)
