from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from .config import Source
from .matching import contains_phrase


RISK_TERMS = {
    "audit",
    "bankrupt",
    "corruption",
    "court",
    "criminal",
    "fine",
    "fraud",
    "investigation",
    "lawsuit",
    "raid",
    "risk",
    "sanction",
    "scandal",
    "штраф",
    "суд",
    "скандал",
    "обшук",
    "підозра",
    "підозрюють",
    "корупція",
    "розслідування",
    "санкції",
    "банкрутство",
    "позов",
    "справа",
    "кримінал",
    "аудит",
    "штраф",
    "суд",
    "скандал",
    "обыск",
    "подозрение",
    "коррупция",
    "расследование",
    "санкции",
    "банкротство",
    "иск",
    "дело",
}


@dataclass(frozen=True)
class Importance:
    score: int
    level: str
    reasons: tuple[str, ...]


def calculate_importance(
    *,
    keyword: str,
    title: str,
    summary: str,
    published_at: str,
    source_type: str = "",
    source: Source | None = None,
) -> Importance:
    text = f"{title}\n{summary}"
    score = 0
    reasons: list[str] = []

    source_points, source_reason = source_score(source, source_type)
    score += source_points
    if source_reason:
        reasons.append(source_reason)

    if contains_phrase(title, keyword):
        score += 25
        reasons.append("keyword_in_title")
    elif contains_phrase(summary, keyword):
        score += 14
        reasons.append("keyword_in_summary")
    elif contains_phrase(text, keyword):
        score += 8
        reasons.append("keyword_in_text")

    risk_count = count_risk_terms(text)
    if risk_count >= 2:
        score += 18
        reasons.append("risk_terms")
    elif risk_count == 1:
        score += 10
        reasons.append("risk_term")

    freshness_points = freshness_score(published_at)
    score += freshness_points
    if freshness_points >= 8:
        reasons.append("fresh")

    score = max(0, min(100, score))
    return Importance(score=score, level=importance_level(score), reasons=tuple(reasons[:5]))


def source_score(source: Source | None, source_type: str) -> tuple[int, str]:
    source_kind = (source.type if source else source_type or "").lower()
    if source_kind == "telegram_paid":
        source_kind = "telegram"

    rank = source.rank if source else None
    subscribers = source.subscribers if source else None

    if rank:
        if rank <= 20:
            return 30, "top_source"
        if rank <= 100:
            return 24, "strong_source"
        if rank <= 300:
            return 18, "known_source"

    if subscribers:
        points = min(26, 8 + int(math.log10(max(10, subscribers)) * 4))
        if subscribers >= 100_000:
            return points, "large_telegram_channel"
        if subscribers >= 10_000:
            return points, "telegram_channel"
        return points, "small_telegram_channel"

    if source_kind == "rss":
        return 16, "rss_source"
    if source_kind == "telegram":
        return 14, "telegram_source"
    if source_kind in {"registry", "prozorro", "prozorro_plan", "prozorro_sale", "rada_bills"}:
        return 18, "registry_source"
    if source_kind in {"threads", "reddit"}:
        return 12, source_kind + "_source"
    return 10, "source"


def count_risk_terms(text: str) -> int:
    normalized = str(text or "").lower()
    count = 0
    for term in RISK_TERMS:
        if re.search(r"[\u0400-\u04ff]", term):
            pattern = rf"(?<!\w){re.escape(term)}\w*(?!\w)"
        else:
            pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            count += 1
    return count


def freshness_score(published_at: str) -> int:
    try:
        value = datetime.fromisoformat(str(published_at or "").replace("Z", "+00:00"))
    except ValueError:
        return 0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - value.astimezone(timezone.utc)).total_seconds() / 3600
    if age_hours <= 6:
        return 10
    if age_hours <= 24:
        return 7
    if age_hours <= 72:
        return 4
    return 0


def importance_level(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def format_importance_block(importance: Importance, language_code: str = "en") -> str:
    language = str(language_code or "en").lower()
    labels = IMPORTANCE_LABELS.get(language, IMPORTANCE_LABELS.get(language[:2], IMPORTANCE_LABELS["en"]))
    level = labels["levels"].get(importance.level, importance.level)
    reasons = [
        labels["reasons"].get(reason, reason.replace("_", " "))
        for reason in importance.reasons
    ]
    reason_text = ", ".join(reasons) if reasons else labels["no_reasons"]
    return (
        f"{labels['title']}: <b>{level}, {importance.score}/100</b>\n"
        f"{labels['reasons_title']}: {reason_text}"
    )


IMPORTANCE_LABELS = {
    "en": {
        "title": "Importance",
        "reasons_title": "Reasons",
        "no_reasons": "basic source signal",
        "levels": {"high": "high", "medium": "medium", "low": "low"},
        "reasons": {
            "top_source": "top source",
            "strong_source": "strong source",
            "known_source": "known source",
            "large_telegram_channel": "large Telegram channel",
            "telegram_channel": "Telegram channel",
            "small_telegram_channel": "small Telegram channel",
            "rss_source": "RSS source",
            "telegram_source": "Telegram source",
            "registry_source": "public registry",
            "threads_source": "Threads source",
            "reddit_source": "Reddit source",
            "source": "source signal",
            "keyword_in_title": "keyword in title",
            "keyword_in_summary": "keyword in summary",
            "keyword_in_text": "keyword in text",
            "risk_terms": "risk words",
            "risk_term": "risk word",
            "fresh": "fresh mention",
        },
    },
    "uk": {
        "title": "Важливість",
        "reasons_title": "Причини",
        "no_reasons": "базовий сигнал джерела",
        "levels": {"high": "висока", "medium": "середня", "low": "низька"},
        "reasons": {
            "top_source": "топ-джерело",
            "strong_source": "сильне джерело",
            "known_source": "відоме джерело",
            "large_telegram_channel": "великий Telegram-канал",
            "telegram_channel": "Telegram-канал",
            "small_telegram_channel": "невеликий Telegram-канал",
            "rss_source": "RSS-джерело",
            "telegram_source": "Telegram-джерело",
            "registry_source": "публічний реєстр",
            "threads_source": "Threads-джерело",
            "reddit_source": "Reddit-джерело",
            "source": "сигнал джерела",
            "keyword_in_title": "ключ у заголовку",
            "keyword_in_summary": "ключ в анонсі",
            "keyword_in_text": "ключ у тексті",
            "risk_terms": "ризикові слова",
            "risk_term": "ризикове слово",
            "fresh": "свіжа згадка",
        },
    },
    "ru": {
        "title": "Важность",
        "reasons_title": "Причины",
        "no_reasons": "базовый сигнал источника",
        "levels": {"high": "высокая", "medium": "средняя", "low": "низкая"},
        "reasons": {
            "top_source": "топ-источник",
            "strong_source": "сильный источник",
            "known_source": "известный источник",
            "large_telegram_channel": "крупный Telegram-канал",
            "telegram_channel": "Telegram-канал",
            "small_telegram_channel": "небольшой Telegram-канал",
            "rss_source": "RSS-источник",
            "telegram_source": "Telegram-источник",
            "registry_source": "публичный реестр",
            "threads_source": "Threads-источник",
            "reddit_source": "Reddit-источник",
            "source": "сигнал источника",
            "keyword_in_title": "ключ в заголовке",
            "keyword_in_summary": "ключ в анонсе",
            "keyword_in_text": "ключ в тексте",
            "risk_terms": "рисковые слова",
            "risk_term": "рисковое слово",
            "fresh": "свежее упоминание",
        },
    },
}
