from datetime import datetime

from config import PLAN_LIMITS


def has_active_subscription(user) -> bool:
    if not user or not user.subscription_end:
        return False
    if getattr(user, "is_blocked", False):
        return False
    return user.subscription_end > datetime.utcnow()


def plan_limits(plan: str | None) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[None])


def effective_limits(user) -> dict:
    if not has_active_subscription(user):
        return PLAN_LIMITS[None]
    return plan_limits(user.plan)
