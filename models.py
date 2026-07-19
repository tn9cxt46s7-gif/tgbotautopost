from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    subscription_end = Column(DateTime, default=None)
    plan = Column(String, default=None)

class Ad(Base):
    __tablename__ = "ads"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    text = Column(String, nullable=False)
    interval_minutes = Column(Integer, default=60)
    active = Column(Boolean, default=True)

class TargetGroup(Base):
    __tablename__ = "target_groups"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    chat_id = Column(Integer, nullable=False)