from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests

from .config import Config

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ThreadsPost:
    source: str
    title: str
    url: str
    published_at: str
    summary: str
    media_type: str = ""
    link_url: str = ""


class ThreadsSearchClient:
    """Small wrapper around the Meta Threads keyword search endpoint."""

    def __init__(self, config: Config):
        self.enabled = bool(config.threads_search_enabled and config.threads_access_token)
        self.access_token = config.threads_access_token
        self.api_base = config.threads_api_base.rstrip("/")
        self.search_type = config.threads_search_type if config.threads_search_type in {"RECENT", "TOP"} else "RECENT"
        self.search_mode = config.threads_search_mode if config.threads_search_mode in {"KEYWORD", "TAG"} else "KEYWORD"
        self.limit = config.threads_search_limit
        self.recent_hours = config.threads_search_recent_hours

    def search(
        self,
        keyword: str,
        timeout: int,
        recent_hours: int | None = None,
        limit: int | None = None,
        search_type: str | None = None,
    ) -> list[ThreadsPost]:
        if not self.enabled or not keyword.strip():
            return []
        safe_hours = max(1, min(24, int(recent_hours or self.recent_hours)))
        safe_limit = max(1, min(100, int(limit or self.limit)))
        safe_type = str(search_type or self.search_type).upper()
        if safe_type not in {"RECENT", "TOP"}:
            safe_type = self.search_type
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=safe_hours)
        response = requests.get(
            f"{self.api_base}/keyword_search",
            params={
                "q": keyword.strip(),
                "search_type": safe_type,
                "search_mode": self.search_mode,
                "fields": "id,text,permalink,timestamp,username,media_type,link_attachment_url",
                "limit": safe_limit,
                "since": int(cutoff.timestamp()),
                "until": int(now.timestamp()),
            },
            timeout=timeout,
            headers={
                "User-Agent": "MonitorioBot/0.1",
                "Authorization": f"Bearer {self.access_token}",
            },
        )
        if response.status_code >= 400:
            raise ThreadsSearchError(response.status_code, response.text)
        payload = response.json()
        posts: list[ThreadsPost] = []
        for item in payload.get("data", []):
            post = self._post_from_item(item, cutoff)
            if post:
                posts.append(post)
        return posts

    def _post_from_item(self, item: dict, cutoff: datetime) -> ThreadsPost | None:
        text = " ".join(str(item.get("text") or "").split())
        url = str(item.get("permalink") or "").strip()
        post_id = str(item.get("id") or "").strip()
        if not url and post_id:
            url = f"https://www.threads.net/t/{post_id}"
        if not text or not url:
            return None
        published_at = str(item.get("timestamp") or "").strip()
        if published_at:
            try:
                published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except ValueError:
                published = None
            if published and published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            if published and published < cutoff:
                return None
        username = str(item.get("username") or "").strip().lstrip("@")
        source = f"Threads @{username}" if username else "Threads"
        return ThreadsPost(
            source=source,
            title=text[:160],
            url=url,
            published_at=published_at,
            summary=text,
            media_type=str(item.get("media_type") or "").strip(),
            link_url=str(item.get("link_attachment_url") or "").strip(),
        )


class ThreadsSearchError(RuntimeError):
    def __init__(self, status_code: int, body: str):
        clean_body = " ".join(str(body or "").split())[:500]
        super().__init__(f"Threads keyword search failed with HTTP {status_code}: {clean_body}")
