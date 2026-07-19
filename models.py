from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, ForeignKey
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, default=None)
    referrer_id = Column(BigInteger, default=None)
    subscription_end = Column(DateTime, default=None)
    plan = Column(String, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)


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
    chat_id = Column(BigInteger, nullable=False)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    plan = Column(String, nullable=False)
    amount_stars = Column(Integer, nullable=False)
    method = Column(String, default="stars")
    created_at = Column(DateTime, default=datetime.utcnow)
