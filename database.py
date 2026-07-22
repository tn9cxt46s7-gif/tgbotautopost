from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select, func, or_, desc, text
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

from config import DB_URL, DEFAULT_INTERVAL_MINUTES, DEFAULT_JITTER_SECONDS

load_dotenv()

logger = logging.getLogger(__name__)

_connect_args = {"statement_cache_size": 0} if "+asyncpg" in DB_URL else {}
engine = create_async_engine(DB_URL, connect_args=_connect_args)
AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

_IS_PG = "+asyncpg" in DB_URL or "postgresql" in DB_URL


class Base(DeclarativeBase):
    pass


# Missing columns on older DBs (create_all does NOT alter existing tables)
_MIGRATIONS = [
    # users
    ("users", "is_blocked", "BOOLEAN DEFAULT FALSE"),
    ("users", "is_admin", "BOOLEAN DEFAULT FALSE"),
    ("users", "autopost_enabled", "BOOLEAN DEFAULT TRUE"),
    ("users", "default_interval", "INTEGER DEFAULT 60"),
    ("users", "quiet_hours_start", "INTEGER DEFAULT 0"),
    ("users", "quiet_hours_end", "INTEGER DEFAULT 6"),
    ("users", "tg_session", "TEXT"),
    ("users", "tg_phone", "VARCHAR"),
    ("users", "tg_account_name", "VARCHAR"),
    ("users", "trial_used", "BOOLEAN DEFAULT FALSE"),
    # ads
    ("ads", "title", "VARCHAR"),
    ("ads", "price", "VARCHAR"),
    ("ads", "photo_file_id", "VARCHAR"),
    ("ads", "status", "VARCHAR DEFAULT 'draft'"),
    ("ads", "last_posted_at", "TIMESTAMP"),
    ("ads", "variant_seed", "INTEGER DEFAULT 0"),
    ("ads", "created_at", "TIMESTAMP"),
    # target_groups
    ("target_groups", "title", "VARCHAR"),
    ("target_groups", "min_interval_minutes", "INTEGER DEFAULT 60"),
    ("target_groups", "jitter_seconds", "INTEGER DEFAULT 180"),
    ("target_groups", "quiet_hours_start", "INTEGER DEFAULT 0"),
    ("target_groups", "quiet_hours_end", "INTEGER DEFAULT 6"),
    ("target_groups", "fail_count", "INTEGER DEFAULT 0"),
    ("target_groups", "cooldown_until", "TIMESTAMP"),
    ("target_groups", "last_post_at", "TIMESTAMP"),
    ("target_groups", "active", "BOOLEAN DEFAULT TRUE"),
    ("target_groups", "bot_can_post", "BOOLEAN DEFAULT FALSE"),
    ("target_groups", "created_at", "TIMESTAMP"),
    # payments
    ("payments", "amount_rub", "INTEGER DEFAULT 0"),
    ("payments", "status", "VARCHAR DEFAULT 'paid'"),
    ("payments", "note", "TEXT"),
    ("payments", "paid_at", "TIMESTAMP"),
]


async def _add_column_if_missing(conn, table: str, column: str, coltype: str):
    if _IS_PG:
        await conn.execute(text(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {coltype}"
        ))
    else:
        # SQLite: check pragma, then ADD COLUMN
        result = await conn.execute(text(f"PRAGMA table_info({table})"))
        rows = result.fetchall()
        existing = {r[1] for r in rows}  # name is index 1
        if column not in existing:
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))


async def migrate_schema(conn):
    """Add new columns to existing tables. Safe to run repeatedly."""
    for table, column, coltype in _MIGRATIONS:
        try:
            await _add_column_if_missing(conn, table, column, coltype)
        except Exception as e:
            # table may not exist yet — create_all handles that
            logger.debug("migrate skip %s.%s: %s", table, column, e)

    # If old ads used `active` boolean, sync into status once
    try:
        if _IS_PG:
            await conn.execute(text(
                "UPDATE ads SET status = 'active' WHERE status IS NULL OR status = ''"
            ))
            # copy from legacy active column if present
            await conn.execute(text(
                """
                DO $$
                BEGIN
                  IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='ads' AND column_name='active'
                  ) THEN
                    UPDATE ads SET status = CASE WHEN active THEN 'active' ELSE 'paused' END
                    WHERE status IS NULL OR status = 'draft';
                  END IF;
                END $$;
                """
            ))
    except Exception as e:
        logger.debug("ads status sync: %s", e)


async def init_db():
    from models import User, Ad, TargetGroup, Payment, PostLog, SupportTicket  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await migrate_schema(conn)



# ── Users ──────────────────────────────────────────────────────────────────

async def get_or_create_user(telegram_id: int, username: str | None = None, referrer_id: int | None = None):
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            changed = False
            if username and user.username != username:
                user.username = username
                changed = True
            if changed:
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


async def get_user_by_id(user_id: int):
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def find_users(query: str, limit: int = 20):
    from models import User
    async with AsyncSession() as session:
        q = query.lstrip("@")
        if q.isdigit():
            result = await session.execute(
                select(User).where(
                    or_(User.telegram_id == int(q), User.id == int(q))
                ).limit(limit)
            )
        else:
            result = await session.execute(
                select(User).where(User.username.ilike(f"%{q}%")).limit(limit)
            )
        return list(result.scalars().all())


async def list_users(offset: int = 0, limit: int = 20):
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(
            select(User).order_by(desc(User.created_at)).offset(offset).limit(limit)
        )
        return list(result.scalars().all())


async def count_users() -> int:
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(select(func.count()).select_from(User))
        return result.scalar() or 0


async def count_active_subs() -> int:
    from models import User
    now = datetime.utcnow()
    async with AsyncSession() as session:
        result = await session.execute(
            select(func.count()).select_from(User).where(
                User.subscription_end.isnot(None),
                User.subscription_end > now,
                User.is_blocked == False,  # noqa: E712
            )
        )
        return result.scalar() or 0


async def count_referrals(telegram_id: int) -> int:
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(
            select(func.count()).select_from(User).where(User.referrer_id == telegram_id)
        )
        return result.scalar() or 0


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


async def set_user_blocked(telegram_id: int, blocked: bool):
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        user.is_blocked = blocked
        await session.commit()
        await session.refresh(user)
        return user


async def set_autopost_enabled(telegram_id: int, enabled: bool):
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        user.autopost_enabled = enabled
        await session.commit()
        await session.refresh(user)
        return user


async def update_user_settings(
    telegram_id: int,
    default_interval: int | None = None,
    quiet_hours_start: int | None = None,
    quiet_hours_end: int | None = None,
):
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        if default_interval is not None:
            user.default_interval = default_interval
        if quiet_hours_start is not None:
            user.quiet_hours_start = quiet_hours_start
        if quiet_hours_end is not None:
            user.quiet_hours_end = quiet_hours_end
        await session.commit()
        await session.refresh(user)
        return user


async def set_user_tg_session(
    telegram_id: int,
    session_encrypted: str | None,
    phone: str | None = None,
    account_name: str | None = None,
):
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        user.tg_session = session_encrypted
        if session_encrypted is None:
            user.tg_phone = None
            user.tg_account_name = None
        else:
            if phone is not None:
                user.tg_phone = phone
            if account_name is not None:
                user.tg_account_name = account_name
        await session.commit()
        await session.refresh(user)
        return user


def user_has_tg_account(user) -> bool:
    return bool(user and user.tg_session)


async def get_subscribed_telegram_ids() -> list[int]:
    from models import User
    now = datetime.utcnow()
    async with AsyncSession() as session:
        result = await session.execute(
            select(User.telegram_id).where(
                User.subscription_end.isnot(None),
                User.subscription_end > now,
                User.is_blocked == False,  # noqa: E712
            )
        )
        return list(result.scalars().all())


async def get_all_telegram_ids() -> list[int]:
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(
            select(User.telegram_id).where(User.is_blocked == False)  # noqa: E712
        )
        return list(result.scalars().all())


async def save_payment(
    telegram_id: int,
    plan: str,
    amount_stars: int,
    method: str = "stars",
    *,
    amount_rub: int = 0,
    status: str = "paid",
    note: str | None = None,
):
    from models import Payment
    async with AsyncSession() as session:
        payment = Payment(
            telegram_id=telegram_id,
            plan=plan,
            amount_stars=amount_stars,
            amount_rub=amount_rub or 0,
            method=method,
            status=status,
            note=note,
            paid_at=datetime.utcnow() if status == "paid" else None,
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment


async def create_pending_payment(
    telegram_id: int,
    plan: str,
    amount_stars: int,
    amount_rub: int,
    method: str,
):
    return await save_payment(
        telegram_id,
        plan,
        amount_stars,
        method=method,
        amount_rub=amount_rub,
        status="pending",
    )


async def get_payment(payment_id: int):
    from models import Payment
    async with AsyncSession() as session:
        result = await session.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()


async def mark_payment_paid(payment_id: int):
    from models import Payment
    async with AsyncSession() as session:
        result = await session.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalar_one_or_none()
        if not payment:
            return None
        payment.status = "paid"
        payment.paid_at = datetime.utcnow()
        await session.commit()
        await session.refresh(payment)
        return payment


async def cancel_payment(payment_id: int):
    from models import Payment
    async with AsyncSession() as session:
        result = await session.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalar_one_or_none()
        if not payment:
            return None
        payment.status = "cancelled"
        await session.commit()
        await session.refresh(payment)
        return payment


async def list_pending_payments(limit: int = 20):
    from models import Payment
    async with AsyncSession() as session:
        result = await session.execute(
            select(Payment)
            .where(Payment.status == "pending")
            .order_by(desc(Payment.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())


async def mark_trial_used(telegram_id: int):
    from models import User
    async with AsyncSession() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        user.trial_used = True
        await session.commit()
        await session.refresh(user)
        return user


# ── Ads ────────────────────────────────────────────────────────────────────

async def create_ad(
    user_id: int,
    text: str,
    price: str | None = None,
    photo_file_id: str | None = None,
    interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
    status: str = "draft",
):
    from models import Ad
    title = (text.strip().split("\n")[0])[:80]
    async with AsyncSession() as session:
        ad = Ad(
            user_id=user_id,
            title=title,
            text=text,
            price=price,
            photo_file_id=photo_file_id,
            interval_minutes=interval_minutes,
            status=status,
        )
        session.add(ad)
        await session.commit()
        await session.refresh(ad)
        return ad


async def get_ad(ad_id: int):
    from models import Ad
    async with AsyncSession() as session:
        result = await session.execute(select(Ad).where(Ad.id == ad_id))
        return result.scalar_one_or_none()


async def get_user_ads(user_id: int):
    from models import Ad
    async with AsyncSession() as session:
        result = await session.execute(
            select(Ad).where(Ad.user_id == user_id).order_by(desc(Ad.created_at))
        )
        return list(result.scalars().all())


async def count_user_ads(user_id: int) -> int:
    from models import Ad
    async with AsyncSession() as session:
        result = await session.execute(
            select(func.count()).select_from(Ad).where(
                Ad.user_id == user_id,
                Ad.status != "sold",
            )
        )
        return result.scalar() or 0


async def update_ad(ad_id: int, **kwargs):
    from models import Ad
    async with AsyncSession() as session:
        result = await session.execute(select(Ad).where(Ad.id == ad_id))
        ad = result.scalar_one_or_none()
        if not ad:
            return None
        for k, v in kwargs.items():
            if hasattr(ad, k):
                setattr(ad, k, v)
        await session.commit()
        await session.refresh(ad)
        return ad


async def delete_ad(ad_id: int) -> bool:
    from models import Ad, PostLog
    async with AsyncSession() as session:
        result = await session.execute(select(Ad).where(Ad.id == ad_id))
        ad = result.scalar_one_or_none()
        if not ad:
            return False
        await session.execute(
            PostLog.__table__.delete().where(PostLog.ad_id == ad_id)
        )
        await session.delete(ad)
        await session.commit()
        return True


async def get_active_ads_for_posting():
    """Active ads — only owners with linked client account + autopost + subscription."""
    from models import Ad, User
    now = datetime.utcnow()
    async with AsyncSession() as session:
        result = await session.execute(
            select(Ad, User).join(User, Ad.user_id == User.id).where(
                Ad.status == "active",
                User.autopost_enabled == True,  # noqa: E712
                User.is_blocked == False,  # noqa: E712
                User.subscription_end.isnot(None),
                User.subscription_end > now,
                User.tg_session.isnot(None),
            )
        )
        return list(result.all())


async def count_ads(status: str | None = None) -> int:
    from models import Ad
    async with AsyncSession() as session:
        q = select(func.count()).select_from(Ad)
        if status:
            q = q.where(Ad.status == status)
        result = await session.execute(q)
        return result.scalar() or 0


async def list_recent_ads(limit: int = 20):
    from models import Ad
    async with AsyncSession() as session:
        result = await session.execute(select(Ad).order_by(desc(Ad.created_at)).limit(limit))
        return list(result.scalars().all())


# ── Groups ─────────────────────────────────────────────────────────────────

async def create_group(
    user_id: int,
    chat_id: int,
    title: str | None = None,
    min_interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
    jitter_seconds: int = DEFAULT_JITTER_SECONDS,
    quiet_hours_start: int = 0,
    quiet_hours_end: int = 6,
    bot_can_post: bool = False,
):
    from models import TargetGroup
    async with AsyncSession() as session:
        existing = await session.execute(
            select(TargetGroup).where(
                TargetGroup.user_id == user_id,
                TargetGroup.chat_id == chat_id,
            )
        )
        if existing.scalar_one_or_none():
            return None  # already exists
        group = TargetGroup(
            user_id=user_id,
            chat_id=chat_id,
            title=title,
            min_interval_minutes=min_interval_minutes,
            jitter_seconds=jitter_seconds,
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end,
            bot_can_post=bot_can_post,
        )
        session.add(group)
        await session.commit()
        await session.refresh(group)
        return group


async def get_group(group_id: int):
    from models import TargetGroup
    async with AsyncSession() as session:
        result = await session.execute(select(TargetGroup).where(TargetGroup.id == group_id))
        return result.scalar_one_or_none()


async def get_user_groups(user_id: int):
    from models import TargetGroup
    async with AsyncSession() as session:
        result = await session.execute(
            select(TargetGroup).where(TargetGroup.user_id == user_id).order_by(desc(TargetGroup.created_at))
        )
        return list(result.scalars().all())


async def count_user_groups(user_id: int) -> int:
    from models import TargetGroup
    async with AsyncSession() as session:
        result = await session.execute(
            select(func.count()).select_from(TargetGroup).where(TargetGroup.user_id == user_id)
        )
        return result.scalar() or 0


async def update_group(group_id: int, **kwargs):
    from models import TargetGroup
    async with AsyncSession() as session:
        result = await session.execute(select(TargetGroup).where(TargetGroup.id == group_id))
        group = result.scalar_one_or_none()
        if not group:
            return None
        for k, v in kwargs.items():
            if hasattr(group, k):
                setattr(group, k, v)
        await session.commit()
        await session.refresh(group)
        return group


async def delete_group(group_id: int) -> bool:
    from models import TargetGroup, PostLog
    async with AsyncSession() as session:
        result = await session.execute(select(TargetGroup).where(TargetGroup.id == group_id))
        group = result.scalar_one_or_none()
        if not group:
            return False
        await session.execute(
            PostLog.__table__.delete().where(PostLog.group_id == group_id)
        )
        await session.delete(group)
        await session.commit()
        return True


async def get_active_groups_for_user(user_id: int):
    from models import TargetGroup
    now = datetime.utcnow()
    async with AsyncSession() as session:
        result = await session.execute(
            select(TargetGroup).where(
                TargetGroup.user_id == user_id,
                TargetGroup.active == True,  # noqa: E712
                or_(
                    TargetGroup.cooldown_until.is_(None),
                    TargetGroup.cooldown_until <= now,
                ),
            )
        )
        return list(result.scalars().all())


async def get_problem_groups(limit: int = 20):
    from models import TargetGroup
    async with AsyncSession() as session:
        result = await session.execute(
            select(TargetGroup).where(
                or_(
                    TargetGroup.fail_count > 0,
                    TargetGroup.active == False,  # noqa: E712
                    TargetGroup.cooldown_until.isnot(None),
                )
            ).order_by(desc(TargetGroup.fail_count)).limit(limit)
        )
        return list(result.scalars().all())


async def count_groups() -> int:
    from models import TargetGroup
    async with AsyncSession() as session:
        result = await session.execute(select(func.count()).select_from(TargetGroup))
        return result.scalar() or 0


# ── Post logs ──────────────────────────────────────────────────────────────

async def add_post_log(ad_id: int, group_id: int, user_id: int, status: str, error: str | None = None):
    from models import PostLog
    async with AsyncSession() as session:
        log = PostLog(ad_id=ad_id, group_id=group_id, user_id=user_id, status=status, error=error)
        session.add(log)
        await session.commit()


async def count_posts_since(since: datetime) -> int:
    from models import PostLog
    async with AsyncSession() as session:
        result = await session.execute(
            select(func.count()).select_from(PostLog).where(
                PostLog.posted_at >= since,
                PostLog.status == "ok",
            )
        )
        return result.scalar() or 0


async def count_user_ok_posts_since(user_id: int, since: datetime) -> int:
    from models import PostLog
    async with AsyncSession() as session:
        result = await session.execute(
            select(func.count()).select_from(PostLog).where(
                PostLog.user_id == user_id,
                PostLog.posted_at >= since,
                PostLog.status == "ok",
            )
        )
        return result.scalar() or 0


async def count_group_ok_posts_since(group_id: int, since: datetime) -> int:
    from models import PostLog
    async with AsyncSession() as session:
        result = await session.execute(
            select(func.count()).select_from(PostLog).where(
                PostLog.group_id == group_id,
                PostLog.posted_at >= since,
                PostLog.status == "ok",
            )
        )
        return result.scalar() or 0


# ── Support ────────────────────────────────────────────────────────────────

async def open_ticket(user_id: int, telegram_id: int):
    from models import SupportTicket
    async with AsyncSession() as session:
        existing = await session.execute(
            select(SupportTicket).where(
                SupportTicket.user_id == user_id,
                SupportTicket.status == "open",
            )
        )
        ticket = existing.scalar_one_or_none()
        if ticket:
            return ticket
        ticket = SupportTicket(user_id=user_id, telegram_id=telegram_id)
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        return ticket


async def get_open_ticket(telegram_id: int):
    from models import SupportTicket
    async with AsyncSession() as session:
        result = await session.execute(
            select(SupportTicket).where(
                SupportTicket.telegram_id == telegram_id,
                SupportTicket.status == "open",
            )
        )
        return result.scalar_one_or_none()


async def get_ticket(ticket_id: int):
    from models import SupportTicket
    async with AsyncSession() as session:
        result = await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
        return result.scalar_one_or_none()


async def close_ticket(ticket_id: int):
    from models import SupportTicket
    async with AsyncSession() as session:
        result = await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
        ticket = result.scalar_one_or_none()
        if not ticket:
            return None
        ticket.status = "closed"
        ticket.closed_at = datetime.utcnow()
        await session.commit()
        await session.refresh(ticket)
        return ticket


async def list_open_tickets(limit: int = 30):
    from models import SupportTicket
    async with AsyncSession() as session:
        result = await session.execute(
            select(SupportTicket).where(SupportTicket.status == "open")
            .order_by(desc(SupportTicket.created_at)).limit(limit)
        )
        return list(result.scalars().all())


async def count_open_tickets() -> int:
    from models import SupportTicket
    async with AsyncSession() as session:
        result = await session.execute(
            select(func.count()).select_from(SupportTicket).where(SupportTicket.status == "open")
        )
        return result.scalar() or 0
