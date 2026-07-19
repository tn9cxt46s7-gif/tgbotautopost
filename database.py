from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///bot.db")
_connect_args = {"statement_cache_size": 0} if "+asyncpg" in DB_URL else {}
engine = create_async_engine(DB_URL, connect_args=_connect_args)
AsyncSession = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    from models import User, Ad, TargetGroup, Payment
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_or_create_user(telegram_id: int, username: str | None = None, referrer_id: int | None = None):
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            if username and user.username != username:
                user.username = username
                await session.commit()
                await session.refresh(user)
            return user
        user = User(telegram_id=telegram_id, username=username, referrer_id=referrer_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def get_user(telegram_id: int):
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def count_referrals(telegram_id: int) -> int:
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(select(User).where(User.referrer_id == telegram_id))
        return len(result.scalars().all())


async def extend_subscription(telegram_id: int, plan: str, days: int):
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        now = datetime.utcnow()
        base = user.subscription_end if user.subscription_end and user.subscription_end > now else now
        user.subscription_end = base + timedelta(days=days)
        user.plan = plan
        await session.commit()
        await session.refresh(user)
        return user


async def save_payment(telegram_id: int, plan: str, amount_stars: int, method: str = "stars"):
    from models import Payment
    async with AsyncSession() as session:
        payment = Payment(telegram_id=telegram_id, plan=plan, amount_stars=amount_stars, method=method)
        session.add(payment)
        await session.commit()
