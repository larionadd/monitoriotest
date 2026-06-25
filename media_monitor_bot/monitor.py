from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from time import mktime, time
from urllib.parse import urljoin, urlparse

import feedparser
import requests
import brotli
from bs4 import BeautifulSoup

from .config import Config, Source
from .db import Database
from .locales import template_text
from .matching import allowed_by_filters, contains_phrase
from .telegram_api import TelegramApi, escape

log = logging.getLogger(__name__)

ARTICLE_LIMIT_PER_SOURCE = 15
SOURCE_ERROR_COOLDOWN_SECONDS = 1800
FULL_TEXT_DOMAIN_COOLDOWN_SECONDS = 1800


@dataclass(frozen=True)
class Article:
    source: str
    title: str
    url: str
    published_at: str
    summary: str
    hidden_links: str = ""

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.summary}\n{self.hidden_links}"


class Monitor:
    def __init__(self, config: Config, db: Database, telegram: TelegramApi, sources: list[Source]):
        self.config = config
        self.db = db
        self.telegram = telegram
        self.sources = sources
        self.source_error_until: dict[str, float] = {}
        self.full_text_domain_error_until: dict[str, float] = {}

    def run_once(self, chat_ids: set[int] | None = None) -> int:
        sent = 0
        users = list(self.db.iter_monitoring_users())
        if chat_ids is not None:
            users = [user for user in users if user.chat_id in chat_ids]
        if not users:
            return 0
        full_text_cache: dict[str, str] = {}
        full_text_failures: dict[str, int] = {}
        article_cache: dict[str, list[Article]] = {}
        source_users = self._source_users(users)

        for source, users_for_source in source_users.values():
            try:
                if self.source_error_until.get(source.url, 0) > time():
                    continue
                if source.url not in article_cache:
                    article_cache[source.url] = fetch_articles(source, self.config.source_timeout_seconds)
                articles = article_cache[source.url]
            except Exception:
                log.exception("Не вдалося прочитати джерело %s", source.name)
                self.source_error_until[source.url] = time() + SOURCE_ERROR_COOLDOWN_SECONDS
                continue

            for article in articles:
                self.db.save_article(
                    article.url,
                    article.source,
                    article.title,
                    article.published_at,
                    article.summary,
                )
                for user in users_for_source:
                    plan = self.db.get_active_plan(user.chat_id)
                    if self.db.sent_today_count(user.chat_id) >= plan.alerts_per_day:
                        continue
                    base_text = article.text
                    if has_stop_word(base_text, user.stop_words):
                        continue
                    keywords = user.keywords[: plan.max_keywords]
                    remaining_keywords: list[str] = []
                    base_plus_ok = has_required_plus_word(base_text, user.plus_words)
                    for keyword in keywords:
                        if self.db.already_sent(user.chat_id, keyword, article.url):
                            continue
                        if base_plus_ok and contains_phrase(base_text, keyword):
                            self._send_alert(user.chat_id, keyword, article)
                            self.db.mark_sent(user.chat_id, keyword, article.url)
                            sent += 1
                            continue
                        remaining_keywords.append(keyword)
                    if not remaining_keywords or not user.full_text_enabled or not plan.full_text:
                        continue
                    full_text = self._full_text(article, full_text_cache, full_text_failures)
                    if not full_text:
                        continue
                    text = f"{base_text}\n{full_text}"
                    if not allowed_by_filters(text, user.stop_words, user.plus_words):
                        continue
                    for keyword in remaining_keywords:
                        if not contains_phrase(text, keyword):
                            continue
                        self._send_alert(user.chat_id, keyword, article)
                        self.db.mark_sent(user.chat_id, keyword, article.url)
                        sent += 1
        return sent

    def _source_users(self, users) -> dict[str, tuple[Source, list]]:
        source_users: dict[str, tuple[Source, list]] = {}
        for user in users:
            for source in self.db.get_enabled_sources(user.chat_id, self.sources):
                if source.url not in source_users:
                    source_users[source.url] = (source, [])
                source_users[source.url][1].append(user)
        return source_users

    def _send_alert(self, chat_id: int, keyword: str, article: Article) -> None:
        settings = self.db.get_user_settings(chat_id)
        template = (
            template_text(settings.language_code, "alert_template")
            if self.config.require_onboarding
            else self.config.alert_template
        )
        text = template.format(
            keyword=escape(keyword),
            source=escape(article.source),
            title=escape(article.title),
            published_at=escape(article.published_at or "не вказана"),
            url=escape(article.url),
        )
        self.telegram.send_message(chat_id, text, disable_web_page_preview=False)

    def _full_text(self, article: Article, cache: dict[str, str], failures: dict[str, int]) -> str:
        if article.url.startswith("https://t.me/"):
            return ""
        if not valid_article_url(article.url):
            return ""
        domain = full_text_domain_key(article.url)
        if self.full_text_domain_error_until.get(domain, 0) > time():
            return ""
        if failures.get(domain, 0) >= 3:
            return ""
        if article.url not in cache:
            try:
                cache[article.url] = fetch_full_text(
                    article.url,
                    self.config.source_timeout_seconds,
                )
            except Exception:
                failures[domain] = failures.get(domain, 0) + 1
                if failures[domain] == 3:
                    self.full_text_domain_error_until[domain] = time() + FULL_TEXT_DOMAIN_COOLDOWN_SECONDS
                    log.warning("Повний текст для домену %s тимчасово пропущено після 3 помилок", domain)
                else:
                    log.debug("Не вдалося прочитати повний текст %s", article.url)
                cache[article.url] = ""
        return cache[article.url]


def has_stop_word(text: str, stop_words: tuple[str, ...]) -> bool:
    return any(contains_phrase(text, word) for word in stop_words)


def has_required_plus_word(text: str, plus_words: tuple[str, ...]) -> bool:
    return not plus_words or any(contains_phrase(text, word) for word in plus_words)


def full_text_domain_key(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    parts = domain.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in {"com.ua", "net.ua", "org.ua"}:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


def fetch_articles(source: Source, timeout: int) -> list[Article]:
    if source.type == "rss":
        return fetch_rss(source, timeout)
    if source.type in {"telegram", "telegram_paid"}:
        return fetch_telegram_channel(source, timeout)
    log.warning("Непідтримуваний тип джерела %s для %s", source.type, source.name)
    return []


def fetch_rss(source: Source, timeout: int) -> list[Article]:
    response = requests.get(
        source.url,
        timeout=timeout,
        headers={
            "User-Agent": "MediaMonitorBot/0.1 (+local Telegram monitoring bot)",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    response.raise_for_status()
    parsed = feedparser.parse(response_body(response))
    articles: list[Article] = []
    for entry in parsed.entries[:ARTICLE_LIMIT_PER_SOURCE]:
        url = clean_article_url(entry.get("link") or "")
        title = strip_html(entry.get("title") or "").strip()
        summary_html = entry.get("summary") or entry.get("description") or ""
        summary = strip_html(summary_html).strip()
        hidden_links = extract_links_text(summary_html, url)
        entry_links = [
            clean_article_url(link.get("href", ""))
            for link in entry.get("links", [])
            if isinstance(link, dict)
        ]
        hidden_links = join_search_parts(
            hidden_links,
            links_search_text(link for link in entry_links if link != url),
        )
        if not url or not title:
            continue
        articles.append(
            Article(
                source=source.name,
                title=title,
                url=url,
                published_at=entry_published(entry),
                summary=summary,
                hidden_links=hidden_links,
            )
        )
    return articles


def fetch_telegram_channel(source: Source, timeout: int) -> list[Article]:
    channel_url = telegram_preview_url(source.url)
    response = requests.get(
        channel_url,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; MediaMonitorBot/0.1)",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    response.raise_for_status()
    html = response_body(response).decode(response.encoding or "utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    articles: list[Article] = []

    for message in soup.select(".tgme_widget_message")[-ARTICLE_LIMIT_PER_SOURCE:]:
        text_node = message.select_one(".tgme_widget_message_text")
        link_node = message.select_one("a.tgme_widget_message_date")
        time_node = message.select_one("time")
        text = text_node.get_text(" ", strip=True) if text_node else ""
        hidden_links = extract_links_text(text_node, channel_url) if text_node else ""
        url = link_node.get("href", "").strip() if link_node else ""
        published_at = time_node.get("datetime", "").strip() if time_node else ""
        if not is_recent_telegram_datetime(published_at):
            continue
        if not text or not url:
            continue
        title = text[:160]
        articles.append(
            Article(
                source=source.name,
                title=title,
                url=url,
                published_at=published_at,
                summary=text,
                hidden_links=hidden_links,
            )
        )
    return articles


def is_recent_telegram_datetime(value: str, now: datetime | None = None, hours: int = 24) -> bool:
    if not value:
        return False
    try:
        published = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current - timedelta(hours=hours) <= published <= current + timedelta(minutes=5)


def entry_published(entry) -> str:
    if entry.get("published_parsed"):
        return datetime.fromtimestamp(mktime(entry.published_parsed)).isoformat(timespec="seconds")
    if entry.get("updated_parsed"):
        return datetime.fromtimestamp(mktime(entry.updated_parsed)).isoformat(timespec="seconds")
    for key in ("published", "updated"):
        value = entry.get(key)
        if not value:
            continue
        try:
            return parsedate_to_datetime(value).isoformat(timespec="seconds")
        except (TypeError, ValueError):
            return str(value)
    return ""


def strip_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return " ".join(unescape(without_tags).split())


def fetch_full_text(url: str, timeout: int) -> str:
    if not valid_article_url(url):
        return ""
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": "MediaMonitorBot/0.1 (+local Telegram monitoring bot)",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    response.raise_for_status()
    body = response_body(response)
    encoding = response.encoding or response.apparent_encoding or "utf-8"
    html = body.decode(encoding, errors="replace")
    return extract_full_text(html, url)


def extract_full_text(html: str, base_url: str = "") -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "form", "iframe"]):
        tag.decompose()

    candidates = []
    for selector in ("article", "main", "[role='main']", ".article", ".post", ".content"):
        candidates.extend(soup.select(selector))

    blocks = candidates or ([soup.body] if soup.body else [soup])
    texts = [block.get_text(" ", strip=True) for block in blocks if block]
    text = max(texts, key=len, default="")
    link_text = links_search_text(
        href
        for block in blocks
        if block
        for href in extract_link_urls(block, base_url)
    )
    return join_search_parts(" ".join(unescape(text).split()), link_text)


def extract_links_text(value, base_url: str = "") -> str:
    soup = value if isinstance(value, BeautifulSoup) else BeautifulSoup(str(value or ""), "html.parser")
    return links_search_text(extract_link_urls(soup, base_url))


def extract_link_urls(node, base_url: str = "") -> list[str]:
    urls: list[str] = []
    for link in node.select("a[href]"):
        href = clean_article_url(link.get("href", ""))
        if not href or href.startswith("#"):
            continue
        absolute = urljoin(base_url, href) if base_url else href
        if valid_article_url(absolute):
            urls.append(absolute)
    return urls


def links_search_text(urls) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for url in urls:
        clean_url = clean_article_url(str(url or ""))
        if not valid_article_url(clean_url) or clean_url in seen:
            continue
        seen.add(clean_url)
        parts.append(clean_url)
        parsed = urlparse(clean_url)
        parts.append(re.sub(r"[^0-9A-Za-z\u0400-\u04FF]+", " ", f"{parsed.netloc} {parsed.path} {parsed.query}"))
    return join_search_parts(*parts)


def join_search_parts(*parts: str) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip())


def response_body(response: requests.Response) -> bytes:
    content = response.content
    if response.headers.get("Content-Encoding", "").lower() == "br" and not content.lstrip().startswith(b"<"):
        try:
            return brotli.decompress(content)
        except brotli.error:
            return content
    return content


def clean_article_url(value: str) -> str:
    url = value.strip()
    for scheme in ("https://", "http://"):
        first = url.find(scheme)
        second = url.find(scheme, first + len(scheme)) if first >= 0 else -1
        if second > 0:
            url = url[second:]
            break
    if url.startswith("//"):
        return "https:" + url
    return url


def valid_article_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def telegram_preview_url(value: str) -> str:
    raw = value.strip().rstrip("/")
    parsed = urlparse(raw)
    if parsed.netloc in {"t.me", "telegram.me"}:
        parts = [part for part in parsed.path.split("/") if part]
        if parts and parts[0] == "s" and len(parts) > 1:
            return f"https://t.me/s/{parts[1]}"
        if parts:
            return f"https://t.me/s/{parts[0]}"
    username = raw.lstrip("@")
    return f"https://t.me/s/{username}"
