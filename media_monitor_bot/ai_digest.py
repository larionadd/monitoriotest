from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import requests

from .config import Config, clean_source_display_name


class AiDigestError(RuntimeError):
    pass


@dataclass(frozen=True)
class DigestMention:
    sent_at: str
    keyword: str
    source: str
    source_type: str
    title: str
    published_at: str
    url: str
    summary: str


def create_ai_digest(
    config: Config,
    mentions: Iterable[DigestMention],
    *,
    period_label: str,
    language_code: str,
    digest_focus: str = "overview",
) -> dict:
    if not config.ai_digest_enabled:
        raise AiDigestError("ai_digest_disabled")
    if config.ai_digest_provider != "deepseek":
        raise AiDigestError("ai_provider_unsupported")
    if not config.deepseek_api_key:
        raise AiDigestError("deepseek_key_missing")

    mention_list = list(mentions)
    if not mention_list:
        return empty_digest(period_label)

    payload_mentions = [
        {
            "sent_at": item.sent_at,
            "keyword": item.keyword,
            "source": clean_source_display_name(item.source),
            "source_type": item.source_type or "",
            "title": item.title,
            "published_at": item.published_at,
            "summary": shorten(item.summary, 700),
            "url": item.url,
        }
        for item in mention_list[: config.ai_digest_max_mentions]
    ]
    response = requests.post(
        f"{config.deepseek_api_base}/chat/completions",
        headers={
            "Authorization": f"Bearer {config.deepseek_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.deepseek_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You create concise media monitoring digests. "
                        "Use only the supplied mentions. Do not invent facts. "
                        "Respect the requested focus: overview gives a balanced summary, "
                        "important prioritizes the strongest mentions, risks highlights threats, "
                        "sources explains source activity, and actions focuses on next steps. "
                        "Return valid JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "language": language_code,
                            "period": period_label,
                            "focus": normalize_focus(digest_focus),
                            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                            "mentions_total": len(mention_list),
                            "mentions_included": len(payload_mentions),
                            "mentions": payload_mentions,
                            "required_json_schema": {
                                "summary": "2-4 sentences with the main picture",
                                "key_topics": ["short topic strings"],
                                "important_mentions": [
                                    {
                                        "title": "mention title",
                                        "source": "source name",
                                        "why_important": "why it matters",
                                        "url": "source url",
                                    }
                                ],
                                "risks": ["potential risks or empty array"],
                                "top_sources": [{"source": "name", "count": 1}],
                                "next_steps": ["practical next step strings"],
                            },
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 1800,
        },
        timeout=config.ai_digest_timeout_seconds,
    )
    if response.status_code >= 400:
        raise AiDigestError(f"deepseek_http_{response.status_code}: {response.text[:500]}")
    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        digest = json.loads(content)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AiDigestError("bad_deepseek_response") from exc
    return normalize_digest(digest, period_label, len(mention_list), len(payload_mentions))


def empty_digest(period_label: str) -> dict:
    return {
        "period": period_label,
        "mentions_total": 0,
        "mentions_included": 0,
        "summary": "No mentions found for the selected period.",
        "key_topics": [],
        "important_mentions": [],
        "risks": [],
        "top_sources": [],
        "next_steps": [],
    }


def normalize_digest(digest: dict, period_label: str, total: int, included: int) -> dict:
    return {
        "period": period_label,
        "mentions_total": total,
        "mentions_included": included,
        "summary": str(digest.get("summary") or "").strip(),
        "key_topics": list_of_strings(digest.get("key_topics")),
        "important_mentions": list_of_mentions(digest.get("important_mentions")),
        "risks": list_of_strings(digest.get("risks")),
        "top_sources": list_of_sources(digest.get("top_sources")),
        "next_steps": list_of_strings(digest.get("next_steps")),
    }


def normalize_focus(value: object) -> str:
    text = str(value or "").strip().lower()
    if text in {"risks", "important", "sources", "actions"}:
        return text
    return "overview"


def list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:10]


def list_of_mentions(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, str]] = []
    for item in value[:8]:
        if not isinstance(item, dict):
            continue
        items.append(
            {
                "title": str(item.get("title") or "").strip(),
                "source": str(item.get("source") or "").strip(),
                "why_important": str(item.get("why_important") or "").strip(),
                "url": str(item.get("url") or "").strip(),
            }
        )
    return items


def list_of_sources(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, object]] = []
    for item in value[:8]:
        if not isinstance(item, dict):
            continue
        try:
            count = int(item.get("count") or 0)
        except (TypeError, ValueError):
            count = 0
        source = str(item.get("source") or "").strip()
        if source:
            items.append({"source": source, "count": count})
    return items


def shorten(value: object, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
