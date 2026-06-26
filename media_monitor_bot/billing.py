from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    stars: int
    days: int
    max_keywords: int
    max_custom_sources: int
    alerts_per_day: int
    full_text: bool
    description: str


PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="Free",
        stars=0,
        days=0,
        max_keywords=1,
        max_custom_sources=0,
        alerts_per_day=15,
        full_text=False,
        description=(
            "🔑 1 ключ • 📰 стандартні RSS • "
            "🚫 без бази TG-каналів • "
            "🔔 15 сповіщень/день • "
            "⏱ моніторинг раз на годину"
        ),
    ),
    "basic": Plan(
        id="basic",
        name="Basic",
        stars=149,
        days=30,
        max_keywords=10,
        max_custom_sources=3,
        alerts_per_day=100,
        full_text=False,
        description=(
            "🔑 10 ключів • 🧩 3 власні RSS/TG • "
            "📡 база TG-каналів • "
            "🔔 100 сповіщень/день • "
            "⏱ моніторинг кожні 30 хвилин"
        ),
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        stars=399,
        days=30,
        max_keywords=50,
        max_custom_sources=15,
        alerts_per_day=500,
        full_text=True,
        description=(
            "🔑 50 ключів • 🧩 15 власних RSS/TG • "
            "📡 база TG-каналів • "
            "🧾 пошук по повному тексту • "
            "🔔 500 сповіщень/день • "
            "⏱ моніторинг кожні 30 хвилин"
        ),
    ),
    "business": Plan(
        id="business",
        name="Business",
        stars=999,
        days=30,
        max_keywords=100000,
        max_custom_sources=100000,
        alerts_per_day=100000,
        full_text=True,
        description=(
            "♾ безлімітні ключі • "
            "♾ безлімітні RSS/TG • "
            "📡 база TG-каналів • "
            "🧾 пошук по повному тексту • "
            "🔔 безлімітні сповіщення • "
            "⚡ моніторинг кожні 5 хвилин"
        ),
    ),
}


def paid_plans() -> list[Plan]:
    return [PLANS["basic"], PLANS["pro"], PLANS["business"]]


def plan_by_id(plan_id: str) -> Plan:
    return PLANS.get(plan_id.lower(), PLANS["free"])


def is_subscription_active(expires_at: str | None) -> bool:
    if not expires_at:
        return False
    try:
        expires = datetime.fromisoformat(expires_at)
    except ValueError:
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires > datetime.now(timezone.utc)


def plan_text(plan: Plan) -> str:
    if plan.id == "free":
        return f"{plan.name}: {plan.description}"
    return f"{plan.name}: {plan.stars} Stars / {plan.days} \u0434\u043d\u0456\u0432. {plan.description}"
