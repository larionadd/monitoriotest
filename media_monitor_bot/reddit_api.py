from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import time
from typing import Any

import requests

from .config import Config

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RedditPost:
    source: str
    title: str
    url: str
    published_at: str
    summary: str
    score: int = 0
    comments: int = 0
    subreddit: str = ""


class RedditSearchClient:
    """Read-only Reddit search through OAuth client credentials."""

    def __init__(self, config: Config):
        self.enabled = bool(
            config.reddit_search_enabled
            and config.reddit_client_id
            and config.reddit_client_secret
            and config.reddit_user_agent
        )
        self.client_id = config.reddit_client_id
        self.client_secret = config.reddit_client_secret
        self.user_agent = config.reddit_user_agent
        self.api_base = config.reddit_api_base.rstrip("/")
        self.token_url = config.reddit_token_url
        self.search_sort = config.reddit_search_sort
        self.search_time = config.reddit_search_time
        self.search_limit = config.reddit_search_limit
        self.recent_hours = config.reddit_search_recent_hours
        self.subreddits = config.reddit_subreddits
        self._access_token = ""
        self._access_token_until = 0.0

    def search(self, keyword: str, timeout: int, recent_hours: int | None = None, limit: int | None = None) -> list[RedditPost]:
        keyword = keyword.strip()
        if not self.enabled or not keyword:
            return []
        safe_limit = max(1, min(100, int(limit or self.search_limit)))
        safe_hours = max(1, min(24 * 30, int(recent_hours or self.recent_hours)))
        cutoff = datetime.now(timezone.utc) - timedelta(hours=safe_hours)
        token = self._token(timeout)
        posts: list[RedditPost] = []
        targets = self.subreddits or ("",)
        for subreddit in targets:
            posts.extend(self._search_target(keyword, token, timeout, safe_limit, cutoff, subreddit))
        posts.sort(key=lambda post: post.published_at, reverse=True)
        return posts[:safe_limit]

    def _token(self, timeout: int) -> str:
        now = time()
        if self._access_token and now < self._access_token_until - 60:
            return self._access_token
        response = requests.post(
            self.token_url,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": self.user_agent},
            timeout=timeout,
        )
        if response.status_code >= 400:
            raise RedditSearchError(response.status_code, response.text)
        payload = response.json()
        token = str(payload.get("access_token") or "").strip()
        if not token:
            raise RedditSearchError(response.status_code, "missing access_token")
        expires_in = int(payload.get("expires_in") or 3600)
        self._access_token = token
        self._access_token_until = now + expires_in
        return token

    def _search_target(
        self,
        keyword: str,
        token: str,
        timeout: int,
        limit: int,
        cutoff: datetime,
        subreddit: str,
    ) -> list[RedditPost]:
        path = f"/r/{subreddit.strip().strip('/')}/search.json" if subreddit.strip() else "/search.json"
        params: dict[str, Any] = {
            "q": keyword,
            "restrict_sr": "1" if subreddit.strip() else "0",
            "sort": self.search_sort,
            "t": self.search_time,
            "limit": limit,
            "raw_json": 1,
        }
        response = requests.get(
            self.api_base + path,
            params=params,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": self.user_agent,
            },
            timeout=timeout,
        )
        if response.status_code >= 400:
            raise RedditSearchError(response.status_code, response.text)
        payload = response.json()
        posts: list[RedditPost] = []
        for child in payload.get("data", {}).get("children", []):
            data = child.get("data") or {}
            post = self._post_from_item(data, cutoff)
            if post:
                posts.append(post)
        return posts

    def _post_from_item(self, item: dict[str, Any], cutoff: datetime) -> RedditPost | None:
        title = " ".join(str(item.get("title") or "").split())
        selftext = " ".join(str(item.get("selftext") or "").split())
        permalink = str(item.get("permalink") or "").strip()
        if not title or not permalink:
            return None
        created = float(item.get("created_utc") or 0)
        published = datetime.fromtimestamp(created, timezone.utc) if created else None
        if published and published < cutoff:
            return None
        subreddit = str(item.get("subreddit") or "").strip()
        external_url = str(item.get("url") or "").strip()
        reddit_url = "https://www.reddit.com" + permalink
        summary_parts = [selftext]
        if external_url and external_url != reddit_url:
            summary_parts.append(external_url)
        summary = "\n".join(part for part in summary_parts if part)
        return RedditPost(
            source=f"Reddit r/{subreddit}" if subreddit else "Reddit",
            title=title,
            url=reddit_url,
            published_at=published.isoformat() if published else "",
            summary=summary,
            score=int(item.get("score") or 0),
            comments=int(item.get("num_comments") or 0),
            subreddit=subreddit,
        )


class RedditSearchError(RuntimeError):
    def __init__(self, status_code: int, body: str):
        clean_body = " ".join(str(body or "").split())[:500]
        super().__init__(f"Reddit search failed with HTTP {status_code}: {clean_body}")
