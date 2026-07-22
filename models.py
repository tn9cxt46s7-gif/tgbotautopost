from sqlalchemy import (
    Column, Integer, BigInteger, String, DateTime, Boolean, ForeignKey, Text
)
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
    is_blocked = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    autopost_enabled = Column(Boolean, default=True)
    default_interval = Column(Integer, default=60)
    quiet_hours_start = Column(Integer, default=0)
    quiet_hours_end = Column(Integer, default=6)
    # Encrypted Telethon StringSession — posts go from the client's account
    tg_session = Column(Text, default=None)
    tg_phone = Column(String, default=None)
    tg_account_name = Column(String, default=None)
    trial_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Ad(Base):
    __tablename__ = "ads"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, default=None)
    text = Column(Text, nullable=False)
    price = Column(String, default=None)
    photo_file_id = Column(String, default=None)
    status = Column(String, default="draft")  # draft / active / paused / sold
    interval_minutes = Column(Integer, default=60)
    last_posted_at = Column(DateTime, default=None)
    variant_seed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class TargetGroup(Base):
    __tablename__ = "target_groups"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    title = Column(String, default=None)
    min_interval_minutes = Column(Integer, default=60)
    jitter_seconds = Column(Integer, default=180)
    quiet_hours_start = Column(Integer, default=0)
    quiet_hours_end = Column(Integer, default=6)
    fail_count = Column(Integer, default=0)
    cooldown_until = Column(DateTime, default=None)
    last_post_at = Column(DateTime, default=None)
    active = Column(Boolean, default=True)
    bot_can_post = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    plan = Column(String, nullable=False)
    amount_stars = Column(Integer, nullable=False)
    amount_rub = Column(Integer, default=0)
    method = Column(String, default="stars")  # stars / card / crypto / manual
    status = Column(String, default="paid")  # pending / paid / cancelled
    note = Column(Text, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, default=None)


class PostLog(Base):
    __tablename__ = "post_logs"
    id = Column(Integer, primary_key=True)
    ad_id = Column(Integer, ForeignKey("ads.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("target_groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False)  # ok / error / skipped
    error = Column(Text, default=None)
    posted_at = Column(DateTime, default=datetime.utcnow)


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_id = Column(BigInteger, nullable=False)
    status = Column(String, default="open")  # open / closed
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, default=None)
