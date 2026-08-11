from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from threading import RLock, Semaphore
from time import mktime, monotonic, time
from typing import Any
from urllib.parse import urljoin, urlparse

import feedparser
import requests
import brotli
from bs4 import BeautifulSoup

from .config import Config, Source, clean_source_display_name
from .db import Database
from .datetime_format import display_date_time, display_datetime_line
from .importance import calculate_importance, format_importance_block
from .locales import normalize_country, template_text
from .matching import allowed_by_filters, contains_phrase
from .reddit_api import RedditPost, RedditSearchClient
from .telegram_api import TelegramApi, escape
from .threads_api import ThreadsPost, ThreadsSearchClient

log = logging.getLogger(__name__)

ARTICLE_LIMIT_PER_SOURCE = 15
FULL_TEXT_DOMAIN_COOLDOWN_SECONDS = 1800
FULL_TEXT_QUEUE_MAX_SIZE = 5000
RSS_RESPONSE_MAX_BYTES = 2_000_000
RSS_RESPONSE_CHUNK_SIZE = 65536
PROZORRO_API_BASE = "https://public-api.prozorro.gov.ua/api/2.5"
PROZORRO_PUBLIC_TENDER_BASE = "https://prozorro.gov.ua/tender/"
PROZORRO_PUBLIC_PLAN_BASE = "https://prozorro.gov.ua/plan/"
PROZORRO_SALE_PUBLIC_BASE = "https://prozorro.sale/auction/"


@dataclass
class SourceHealth:
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    cooldown_until: float = 0.0
    last_duration_seconds: float = 0.0
    last_error: str = ""


@dataclass
class SourceFetchResult:
    source: Source
    articles: list["Article"] = field(default_factory=list)
    duration_seconds: float = 0.0
    error: BaseException | None = None


@dataclass
class SourceFetchShardResult:
    shard: str
    results: list[SourceFetchResult] = field(default_factory=list)
    duration_seconds: float = 0.0
    workers: int = 0


@dataclass
class SourceQueueFetchResult:
    queue_name: str
    source_items: list[tuple[Source, list]]
    article_cache: dict[str, list["Article"]]
    stats: "MonitorRunStats"


@dataclass
class FullTextFetchResult:
    article: "Article"
    domain: str
    text: str = ""
    duration_seconds: float = 0.0
    error: BaseException | None = None


@dataclass
class FullTextQueueItem:
    article: "Article"
    queued_at: float
    priority_at: float


@dataclass
class MonitorRunStats:
    users: int = 0
    sources_total: int = 0
    sources_attempted: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    sources_skipped: int = 0
    articles: int = 0
    alerts_sent: int = 0
    fetch_duration_seconds: float = 0.0
    full_text_attempted: int = 0
    full_text_succeeded: int = 0
    full_text_failed: int = 0
    full_text_skipped: int = 0
    full_text_duration_seconds: float = 0.0
    duration_seconds: float = 0.0
    slowest_sources: list[tuple[str, float]] = field(default_factory=list)
    queue_durations: dict[str, float] = field(default_factory=dict)

    def slowest_summary(self) -> str:
        return ", ".join(f"{name}={duration:.1f}s" for name, duration in self.slowest_sources) or "-"

    def queue_summary(self) -> str:
        return ", ".join(f"{name}={duration:.1f}s" for name, duration in self.queue_durations.items()) or "-"


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
        self.threads = ThreadsSearchClient(config)
        self.reddit = RedditSearchClient(config)
        self.admin_chat_ids = set(config.admin_chat_ids)
        self.source_health: dict[str, SourceHealth] = {}
        self.source_health_lock = RLock()
        self.full_text_domain_error_until: dict[str, float] = {}
        self.full_text_queue: dict[str, FullTextQueueItem] = {}
        self.full_text_queue_lock = RLock()
        self.full_text_background_future: Future | None = None
        self.full_text_background_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="full-text-background",
        )
        self.last_run_stats = MonitorRunStats()

    def run_once(self, chat_ids: set[int] | None = None) -> int:
        started = monotonic()
        sent = 0
        users = list(self.db.iter_monitoring_users())
        if chat_ids is not None:
            users = [user for user in users if user.chat_id in chat_ids]
        if not users:
            self.last_run_stats = MonitorRunStats(duration_seconds=0.0)
            return 0
        full_text_cache: dict[str, str] = {}
        full_text_failures: dict[str, int] = {}
        plan_cache: dict[int, object] = {}
        sent_today: dict[int, int] = {}
        source_users = self._source_users(users)
        source_items = list(source_users.values())
        stats = MonitorRunStats(users=len(users), sources_total=len(source_items))
        source_queues = self._source_queues(source_items)
        queue_results = self._fetch_source_queues(source_queues)
        source_fetch_wall_seconds = max(
            (queue_result.stats.fetch_duration_seconds for queue_result in queue_results),
            default=0.0,
        )
        for queue_result in queue_results:
            queue_sent = self._process_source_queue(
                queue_result,
                plan_cache,
                sent_today,
                full_text_cache,
                full_text_failures,
                stats,
            )
            sent += queue_sent
        stats.fetch_duration_seconds = source_fetch_wall_seconds
        sent += self._run_threads_search(users, plan_cache, sent_today)
        sent += self._run_reddit_search(users, plan_cache, sent_today)
        stats.alerts_sent = sent
        stats.duration_seconds = monotonic() - started
        self.last_run_stats = stats
        log.info(
            "Monitor cycle stats: users=%s sources=%s attempted=%s ok=%s failed=%s skipped=%s articles=%s alerts=%s fetch_duration=%.1fs full_text_attempted=%s full_text_ok=%s full_text_failed=%s full_text_skipped=%s full_text_duration=%.1fs duration=%.1fs queues=%s slowest=%s",
            stats.users,
            stats.sources_total,
            stats.sources_attempted,
            stats.sources_succeeded,
            stats.sources_failed,
            stats.sources_skipped,
            stats.articles,
            stats.alerts_sent,
            stats.fetch_duration_seconds,
            stats.full_text_attempted,
            stats.full_text_succeeded,
            stats.full_text_failed,
            stats.full_text_skipped,
            stats.full_text_duration_seconds,
            stats.duration_seconds,
            stats.queue_summary(),
            stats.slowest_summary(),
        )
        return sent

    def _fetch_source_queues(
        self,
        source_queues: list[tuple[str, list[tuple[Source, list]]]],
    ) -> list[SourceQueueFetchResult]:
        if not source_queues:
            return []
        if len(source_queues) == 1:
            return [self._fetch_source_queue(*source_queues[0])]

        fetched: dict[str, SourceQueueFetchResult] = {}
        workers = min(len(source_queues), 3)
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="source-queue") as executor:
            futures = [
                executor.submit(self._fetch_source_queue, queue_name, queue_items)
                for queue_name, queue_items in source_queues
            ]
            for future in as_completed(futures):
                result = future.result()
                fetched[result.queue_name] = result
        return [fetched[queue_name] for queue_name, _queue_items in source_queues if queue_name in fetched]

    def _fetch_source_queue(
        self,
        queue_name: str,
        source_items: list[tuple[Source, list]],
    ) -> SourceQueueFetchResult:
        queue_started = monotonic()
        article_cache, queue_stats = self._fetch_source_articles(source_items)
        queue_stats.duration_seconds = monotonic() - queue_started
        log.info(
            "Source queue fetch stats: queue=%s sources=%s attempted=%s ok=%s failed=%s skipped=%s fetch_duration=%.1fs slowest=%s",
            queue_name,
            len(source_items),
            queue_stats.sources_attempted,
            queue_stats.sources_succeeded,
            queue_stats.sources_failed,
            queue_stats.sources_skipped,
            queue_stats.fetch_duration_seconds,
            queue_stats.slowest_summary(),
        )
        return SourceQueueFetchResult(queue_name, source_items, article_cache, queue_stats)

    def _process_source_queue(
        self,
        queue_result: SourceQueueFetchResult,
        plan_cache: dict[int, object],
        sent_today: dict[int, int],
        full_text_cache: dict[str, str],
        full_text_failures: dict[str, int],
        stats: MonitorRunStats,
    ) -> int:
        queue_name = queue_result.queue_name
        source_items = queue_result.source_items
        article_cache = queue_result.article_cache
        queue_stats = queue_result.stats
        queue_stats.users = stats.users
        self._save_fetched_articles(source_items, article_cache, queue_stats)
        sent = self._send_base_alerts(
            source_items,
            article_cache,
            plan_cache,
            sent_today,
        )
        self._queue_needed_full_texts(
            source_items,
            article_cache,
            plan_cache,
            sent_today,
            full_text_cache,
            full_text_failures,
            queue_stats,
        )
        sent += self._send_full_text_alerts(
            source_items,
            article_cache,
            plan_cache,
            sent_today,
            full_text_cache,
            full_text_failures,
            queue_stats,
        )
        queue_stats.alerts_sent = sent
        self._merge_source_queue_stats(stats, queue_stats)
        stats.queue_durations[queue_name] = queue_stats.duration_seconds
        log.info(
            "Source queue completed: queue=%s duration=%.1fs articles=%s alerts=%s full_text_skipped=%s",
            queue_name,
            queue_stats.duration_seconds,
            queue_stats.articles,
            queue_stats.alerts_sent,
            queue_stats.full_text_skipped,
        )
        return sent

    def _merge_source_queue_stats(self, stats: MonitorRunStats, queue_stats: MonitorRunStats) -> None:
        stats.sources_attempted += queue_stats.sources_attempted
        stats.sources_succeeded += queue_stats.sources_succeeded
        stats.sources_failed += queue_stats.sources_failed
        stats.sources_skipped += queue_stats.sources_skipped
        stats.articles += queue_stats.articles
        stats.alerts_sent += queue_stats.alerts_sent
        stats.full_text_attempted += queue_stats.full_text_attempted
        stats.full_text_succeeded += queue_stats.full_text_succeeded
        stats.full_text_failed += queue_stats.full_text_failed
        stats.full_text_skipped += queue_stats.full_text_skipped
        stats.full_text_duration_seconds += queue_stats.full_text_duration_seconds
        stats.slowest_sources = sorted(
            [*stats.slowest_sources, *queue_stats.slowest_sources],
            key=lambda item: item[1],
            reverse=True,
        )[:5]

    def _source_queues(self, source_items: list[tuple[Source, list]]) -> list[tuple[str, list[tuple[Source, list]]]]:
        queues: dict[str, list[tuple[Source, list]]] = {}
        for item in source_items:
            queues.setdefault(source_queue_key(item[0]), []).append(item)
        ordered_names = [name for name in ("telegram", "rss", "registry") if name in queues]
        ordered_names.extend(sorted(name for name in queues if name not in ordered_names))
        return [(name, queues[name]) for name in ordered_names]

    def _daily_limit_reached(self, chat_id: int, plan: object, sent_today: dict[int, int]) -> bool:
        if chat_id in self.admin_chat_ids:
            return False
        if chat_id not in sent_today:
            sent_today[chat_id] = self.db.sent_today_count(chat_id)
        return sent_today[chat_id] >= plan.alerts_per_day

    def _increment_sent_today(self, chat_id: int, sent_today: dict[int, int]) -> None:
        if chat_id not in sent_today:
            sent_today[chat_id] = self.db.sent_today_count(chat_id)
        sent_today[chat_id] += 1

    def _save_fetched_articles(
        self,
        source_items: list[tuple[Source, list]],
        article_cache: dict[str, list[Article]],
        stats: MonitorRunStats,
    ) -> None:
        for source, _users_for_source in source_items:
            articles = article_cache.get(source.url, [])
            stats.articles += len(articles)
            for article in articles:
                self.db.save_article(
                    article.url,
                    article.source,
                    article.title,
                    article.published_at,
                    article.summary,
                    source.type,
                )

    def _send_base_alerts(
        self,
        source_items: list[tuple[Source, list]],
        article_cache: dict[str, list[Article]],
        plan_cache: dict[int, object],
        sent_today: dict[int, int],
    ) -> int:
        sent = 0
        for source, users_for_source in source_items:
            source_country = normalize_country(source.country)
            for article in article_cache.get(source.url, []):
                base_text = article.text
                for user in users_for_source:
                    if user.chat_id not in plan_cache:
                        plan_cache[user.chat_id] = self.db.get_active_plan(user.chat_id)
                    plan = plan_cache[user.chat_id]
                    if self._daily_limit_reached(user.chat_id, plan, sent_today):
                        continue
                    if has_stop_word(base_text, user.stop_words):
                        continue
                    keywords = [
                        keyword
                        for keyword in user.keywords
                        if keyword.country_code == source_country and not keyword.paused
                    ][: plan.max_keywords]
                    if not keywords or not has_required_plus_word(base_text, user.plus_words):
                        continue
                    for keyword in keywords:
                        if self._daily_limit_reached(user.chat_id, plan, sent_today):
                            break
                        if self.db.already_sent(user.chat_id, keyword.phrase, article.url):
                            continue
                        if not contains_phrase(base_text, keyword.phrase):
                            continue
                        if not self._send_alert(
                            user.chat_id,
                            keyword.phrase,
                            article,
                            silent=keyword.silent,
                            country_code=keyword.country_code,
                            source=source,
                            plan_id=plan.id,
                        ):
                            continue
                        self.db.mark_sent(user.chat_id, keyword.phrase, article.url)
                        sent += 1
                        self._increment_sent_today(user.chat_id, sent_today)
        return sent

    def _send_full_text_alerts(
        self,
        source_items: list[tuple[Source, list]],
        article_cache: dict[str, list[Article]],
        plan_cache: dict[int, object],
        sent_today: dict[int, int],
        full_text_cache: dict[str, str],
        full_text_failures: dict[str, int],
        stats: MonitorRunStats,
    ) -> int:
        sent = 0
        for source, users_for_source in source_items:
            source_country = normalize_country(source.country)
            for article in article_cache.get(source.url, []):
                if article.url not in full_text_cache:
                    continue
                full_text = self._full_text(article, full_text_cache, full_text_failures, stats)
                if not full_text:
                    continue
                base_text = article.text
                text = f"{base_text}\n{full_text}"
                for user in users_for_source:
                    if user.chat_id not in plan_cache:
                        plan_cache[user.chat_id] = self.db.get_active_plan(user.chat_id)
                    plan = plan_cache[user.chat_id]
                    if not user.full_text_enabled or not plan.full_text:
                        continue
                    if self._daily_limit_reached(user.chat_id, plan, sent_today):
                        continue
                    if not allowed_by_filters(text, user.stop_words, user.plus_words):
                        continue
                    base_plus_ok = has_required_plus_word(base_text, user.plus_words)
                    keywords = [
                        keyword
                        for keyword in user.keywords
                        if keyword.country_code == source_country and not keyword.paused
                    ][: plan.max_keywords]
                    for keyword in keywords:
                        if self._daily_limit_reached(user.chat_id, plan, sent_today):
                            break
                        if self.db.already_sent(user.chat_id, keyword.phrase, article.url):
                            continue
                        if base_plus_ok and contains_phrase(base_text, keyword.phrase):
                            continue
                        if not contains_full_text_signal(full_text, keyword.phrase):
                            continue
                        if not self._send_alert(
                            user.chat_id,
                            keyword.phrase,
                            article,
                            silent=keyword.silent,
                            country_code=keyword.country_code,
                            source=source,
                            plan_id=plan.id,
                        ):
                            continue
                        self.db.mark_sent(user.chat_id, keyword.phrase, article.url)
                        sent += 1
                        self._increment_sent_today(user.chat_id, sent_today)
        return sent

    def _queue_needed_full_texts(
        self,
        source_items: list[tuple[Source, list]],
        article_cache: dict[str, list[Article]],
        plan_cache: dict[int, object],
        sent_today: dict[int, int],
        full_text_cache: dict[str, str],
        full_text_failures: dict[str, int],
        stats: MonitorRunStats,
    ) -> None:
        candidates: dict[str, Article] = {}
        for source, users_for_source in source_items:
            source_country = normalize_country(source.country)
            for article in article_cache.get(source.url, []):
                base_text = article.text
                if article.url in candidates or not valid_article_url(article.url):
                    continue
                for user in users_for_source:
                    if user.chat_id not in plan_cache:
                        plan_cache[user.chat_id] = self.db.get_active_plan(user.chat_id)
                    plan = plan_cache[user.chat_id]
                    if not user.full_text_enabled or not plan.full_text:
                        continue
                    if self._daily_limit_reached(user.chat_id, plan, sent_today):
                        continue
                    if has_stop_word(base_text, user.stop_words):
                        continue
                    keywords = [
                        keyword
                        for keyword in user.keywords
                        if keyword.country_code == source_country and not keyword.paused
                    ][: plan.max_keywords]
                    if not keywords:
                        continue
                    base_plus_ok = has_required_plus_word(base_text, user.plus_words)
                    needs_full_text = False
                    for keyword in keywords:
                        if self.db.already_sent(user.chat_id, keyword.phrase, article.url):
                            continue
                        if base_plus_ok and contains_phrase(base_text, keyword.phrase):
                            continue
                        needs_full_text = True
                        break
                    if needs_full_text:
                        candidates[article.url] = article
                        break

        if not candidates:
            return

        queued_now = 0
        cached_count = 0
        for article in candidates.values():
            domain = full_text_domain_key(article.url)
            if self.full_text_domain_error_until.get(domain, 0) > time():
                stats.full_text_skipped += 1
                full_text_cache[article.url] = ""
                continue
            if full_text_failures.get(domain, 0) >= 3:
                stats.full_text_skipped += 1
                full_text_cache[article.url] = ""
                continue
            cached_text = self.db.get_article_full_text(article.url)
            if cached_text is not None:
                full_text_cache[article.url] = cached_text
                cached_count += 1
                continue
            queued_now += self._queue_full_text_article(article)

        scheduled = self._schedule_full_text_background_fetch()
        deferred = self._defer_unfetched_current_full_texts(set(candidates), full_text_cache)
        stats.full_text_skipped += deferred
        log.info(
            "Full text queue: candidates=%s queued_now=%s queue=%s cached=%s fetched=0 failed=0 skipped=%s deferred=%s duration=0.0s workers=background scheduled=%s",
            len(candidates),
            queued_now,
            self._full_text_queue_size(),
            cached_count,
            stats.full_text_skipped,
            deferred,
            scheduled,
        )
        return

    def _schedule_full_text_background_fetch(self) -> bool:
        if self._full_text_queue_size() <= 0:
            return False
        if self.full_text_background_future and not self.full_text_background_future.done():
            return False
        self.full_text_background_future = self.full_text_background_executor.submit(
            self._process_full_text_queue_background_safe
        )
        return True

    def _process_full_text_queue_background_safe(self) -> None:
        try:
            self._process_full_text_queue_background()
        except Exception:
            log.exception("Full text background queue failed")

    def _process_full_text_queue_background(self) -> None:
        full_text_cache: dict[str, str] = {}
        fetch_articles = self._take_full_text_queue_batch(full_text_cache)
        if not fetch_articles:
            return

        started = monotonic()
        workers = max(1, min(self.config.full_text_fetch_workers, len(fetch_articles)))
        domain_limits: dict[str, Semaphore] = {}
        results: list[FullTextFetchResult] = []
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="full-text-fetch") as executor:
            futures = []
            for article in fetch_articles:
                domain = full_text_domain_key(article.url)
                domain_limits.setdefault(domain, Semaphore(2))
                futures.append(executor.submit(self._fetch_one_full_text, article, domain_limits[domain]))
            for future in as_completed(futures):
                results.append(future.result())

        fetched_ok = 0
        failed = 0
        failures_by_domain: dict[str, int] = {}
        for result in results:
            if result.error is None:
                self._remove_full_text_queue_item(result.article.url)
                try:
                    self.db.save_article_full_text(result.article.url, result.text)
                except Exception:
                    log.debug("Failed to save full-text cache %s", result.article.url)
                if result.text:
                    fetched_ok += 1
                continue

            failed += 1
            failures_by_domain[result.domain] = failures_by_domain.get(result.domain, 0) + 1
            if failures_by_domain[result.domain] == 3:
                self.full_text_domain_error_until[result.domain] = time() + FULL_TEXT_DOMAIN_COOLDOWN_SECONDS
                log.warning("Full text for domain %s is temporarily skipped after 3 errors", result.domain)
            else:
                log.debug("Failed to fetch full text %s", result.article.url)
            self._remove_full_text_queue_item(result.article.url)

        duration = monotonic() - started
        log.info(
            "Full text background queue: attempted=%s queue=%s fetched=%s failed=%s duration=%.1fs workers=%s",
            len(fetch_articles),
            self._full_text_queue_size(),
            fetched_ok,
            failed,
            duration,
            workers,
        )

    def _queue_full_text_article(self, article: Article) -> int:
        with self.full_text_queue_lock:
            if article.url in self.full_text_queue:
                item = self.full_text_queue[article.url]
                priority_at = article_priority_timestamp(article)
                if priority_at > item.priority_at:
                    self.full_text_queue[article.url] = FullTextQueueItem(article, item.queued_at, priority_at)
                return 0
            self.full_text_queue[article.url] = FullTextQueueItem(
                article=article,
                queued_at=time(),
                priority_at=article_priority_timestamp(article),
            )
            self._trim_full_text_queue()
            return 1

    def _take_full_text_queue_batch(self, full_text_cache: dict[str, str]) -> list[Article]:
        prefetch_limit = self.config.full_text_prefetch_limit
        if prefetch_limit <= 0:
            return []
        with self.full_text_queue_lock:
            self._trim_full_text_queue()
            selected: list[Article] = []
            for item in sorted(
                self.full_text_queue.values(),
                key=lambda value: (value.priority_at, value.queued_at),
                reverse=True,
            ):
                if item.article.url in full_text_cache:
                    continue
                selected.append(item.article)
                if len(selected) >= prefetch_limit:
                    break
            return selected

    def _trim_full_text_queue(self) -> None:
        with self.full_text_queue_lock:
            if len(self.full_text_queue) <= FULL_TEXT_QUEUE_MAX_SIZE:
                return
            keep_items = sorted(
                self.full_text_queue.values(),
                key=lambda value: (value.priority_at, value.queued_at),
                reverse=True,
            )[:FULL_TEXT_QUEUE_MAX_SIZE]
            self.full_text_queue = {item.article.url: item for item in keep_items}

    def _remove_full_text_queue_item(self, url: str) -> None:
        with self.full_text_queue_lock:
            self.full_text_queue.pop(url, None)

    def _full_text_queue_size(self) -> int:
        with self.full_text_queue_lock:
            return len(self.full_text_queue)

    def _defer_unfetched_current_full_texts(
        self,
        current_urls: set[str],
        full_text_cache: dict[str, str],
    ) -> int:
        deferred = 0
        for url in current_urls:
            if url not in full_text_cache:
                full_text_cache[url] = ""
                deferred += 1
        return deferred

    def _fetch_one_full_text(self, article: Article, domain_limit: Semaphore) -> FullTextFetchResult:
        domain = full_text_domain_key(article.url)
        started = monotonic()
        try:
            with domain_limit:
                text = fetch_full_text(article.url, self.config.source_timeout_seconds)
            return FullTextFetchResult(article, domain, text, monotonic() - started)
        except Exception as exc:
            return FullTextFetchResult(article, domain, duration_seconds=monotonic() - started, error=exc)

    def _fetch_source_articles(
        self,
        source_items: list[tuple[Source, list]],
    ) -> tuple[dict[str, list[Article]], MonitorRunStats]:
        stats = MonitorRunStats()
        fetch_started = monotonic()
        article_cache: dict[str, list[Article]] = {}
        source_groups: dict[str, list[Source]] = {}
        now_ts = time()

        for source, _users_for_source in source_items:
            with self.source_health_lock:
                health = self.source_health.get(source.url)
            if health and health.cooldown_until > now_ts:
                stats.sources_skipped += 1
                continue
            source_groups.setdefault(source_fetch_shard_key(source), []).append(source)

        fetch_groups = split_source_fetch_groups(source_groups, self.config.source_fetch_shard_bucket_size)
        stats.sources_attempted = sum(len(sources) for _shard, sources in fetch_groups)
        if not source_groups:
            stats.fetch_duration_seconds = monotonic() - fetch_started
            return article_cache, stats

        results: list[SourceFetchResult] = []
        shard_workers = max(1, min(self.config.source_fetch_shard_workers, len(fetch_groups)))
        with ThreadPoolExecutor(max_workers=shard_workers, thread_name_prefix="source-shard") as executor:
            futures = [
                executor.submit(self._fetch_source_shard, shard, sources)
                for shard, sources in fetch_groups
            ]
            for future in as_completed(futures):
                shard_result = future.result()
                results.extend(shard_result.results)
                shard_failed = sum(1 for result in shard_result.results if result.error is not None)
                shard_ok = len(shard_result.results) - shard_failed
                slowest = ", ".join(
                    f"{clean_source_display_name(result.source.name)}={result.duration_seconds:.1f}s"
                    for result in sorted(shard_result.results, key=lambda item: item.duration_seconds, reverse=True)[:3]
                ) or "-"
                log.info(
                    "Source fetch shard: shard=%s sources=%s ok=%s failed=%s duration=%.1fs workers=%s slowest=%s",
                    shard_result.shard,
                    len(shard_result.results),
                    shard_ok,
                    shard_failed,
                    shard_result.duration_seconds,
                    shard_result.workers,
                    slowest,
                )

        for result in results:
            cooldown = 0
            slow_cooldown = False
            with self.source_health_lock:
                health = self.source_health.setdefault(result.source.url, SourceHealth())
                health.last_duration_seconds = result.duration_seconds
                if result.error is None:
                    health.successes += 1
                    health.consecutive_failures = 0
                    health.last_error = ""
                    health.cooldown_until = 0.0
                    if (
                        self.config.source_slow_threshold_seconds
                        and self.config.source_slow_cooldown_seconds
                        and result.duration_seconds >= self.config.source_slow_threshold_seconds
                    ):
                        health.cooldown_until = time() + self.config.source_slow_cooldown_seconds
                        slow_cooldown = True
                    article_cache[result.source.url] = result.articles
                    stats.sources_succeeded += 1
                    failure_count = 0
                else:
                    stats.sources_failed += 1
                    health.failures += 1
                    health.consecutive_failures += 1
                    health.last_error = f"{type(result.error).__name__}: {result.error}"
                    cooldown = self._source_error_cooldown_seconds(health.consecutive_failures, result.error)
                    health.cooldown_until = time() + cooldown if cooldown else 0.0
                    failure_count = health.consecutive_failures

            if result.error is None:
                if slow_cooldown:
                    log.info(
                        "Source fetch slow cooldown: source=%s url=%s duration=%.1fs cooldown=%ss",
                        result.source.name,
                        result.source.url,
                        result.duration_seconds,
                        self.config.source_slow_cooldown_seconds,
                    )
                continue

            log.warning(
                "Source fetch failed: source=%s url=%s failures=%s cooldown=%ss duration=%.1fs error=%s",
                result.source.name,
                result.source.url,
                failure_count,
                int(cooldown),
                result.duration_seconds,
                f"{type(result.error).__name__}: {result.error}",
            )

        stats.slowest_sources = sorted(
            (
                (clean_source_display_name(result.source.name), result.duration_seconds)
                for result in results
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:5]
        stats.fetch_duration_seconds = monotonic() - fetch_started
        return article_cache, stats

    def _fetch_source_shard(self, shard: str, sources: list[Source]) -> SourceFetchShardResult:
        started = monotonic()
        workers = max(1, min(self.config.source_fetch_workers_per_shard, len(sources)))
        results: list[SourceFetchResult] = []
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix=f"source-{safe_thread_label(shard)}") as executor:
            futures = [executor.submit(self._fetch_one_source, source) for source in sources]
            for future in as_completed(futures):
                results.append(future.result())
        return SourceFetchShardResult(shard, results, monotonic() - started, workers)

    def _fetch_one_source(self, source: Source) -> SourceFetchResult:
        started = monotonic()
        try:
            articles = fetch_articles(source, self.config.source_timeout_seconds)
            return SourceFetchResult(source, articles, monotonic() - started)
        except Exception as exc:
            return SourceFetchResult(source, duration_seconds=monotonic() - started, error=exc)

    def _source_error_cooldown_seconds(self, consecutive_failures: int, error: BaseException | None = None) -> int:
        if source_error_needs_hard_cooldown(error):
            return self.config.source_error_cooldown_seconds
        if consecutive_failures < self.config.source_error_threshold:
            return self.config.source_error_soft_cooldown_seconds * consecutive_failures
        hard_failure_count = consecutive_failures - self.config.source_error_threshold + 1
        cooldown = self.config.source_error_cooldown_seconds * hard_failure_count
        if self.config.source_error_max_cooldown_seconds:
            cooldown = min(cooldown, self.config.source_error_max_cooldown_seconds)
        return cooldown

    def _run_reddit_search(self, users, plan_cache: dict[int, object], sent_today: dict[int, int]) -> int:
        if not self.reddit.enabled:
            return 0
        eligible: list[tuple[object, object, list[str]]] = []
        search_keys: set[str] = set()
        allowed_plans = set(self.config.reddit_plan_ids)
        for user in users:
            if user.chat_id not in plan_cache:
                plan_cache[user.chat_id] = self.db.get_active_plan(user.chat_id)
            plan = plan_cache[user.chat_id]
            if allowed_plans and plan.id not in allowed_plans:
                continue
            if self._daily_limit_reached(user.chat_id, plan, sent_today):
                continue
            keywords = [keyword for keyword in user.keywords if not keyword.paused][: plan.max_keywords]
            if not keywords:
                continue
            eligible.append((user, plan, keywords))
            search_keys.update(keyword.phrase for keyword in keywords)
        if not eligible:
            return 0

        reddit_cache: dict[str, list[Article]] = {}
        for keyword in sorted(search_keys):
            try:
                reddit_cache[keyword] = [
                    reddit_post_to_article(post)
                    for post in self.reddit.search(
                        keyword,
                        self.config.source_timeout_seconds,
                        recent_hours=self.config.reddit_search_recent_hours,
                        limit=self.config.reddit_search_limit,
                    )
                ]
            except Exception:
                log.exception("Reddit keyword search failed for %s", keyword)
                reddit_cache[keyword] = []

        sent = 0
        for user, plan, keywords in eligible:
            for keyword in keywords:
                for article in reddit_cache.get(keyword.phrase, []):
                    if self._daily_limit_reached(user.chat_id, plan, sent_today):
                        break
                    if self.db.already_sent(user.chat_id, keyword.phrase, article.url):
                        continue
                    if not allowed_by_filters(article.text, user.stop_words, user.plus_words):
                        continue
                    if not contains_phrase(article.text, keyword.phrase):
                        continue
                    self.db.save_article(
                        article.url,
                        article.source,
                        article.title,
                        article.published_at,
                        article.summary,
                        "reddit",
                    )
                    if not self._send_alert(
                        user.chat_id,
                        keyword.phrase,
                        article,
                        silent=keyword.silent,
                        country_code=keyword.country_code,
                        source_type="reddit",
                        plan_id=plan.id,
                    ):
                        continue
                    self.db.mark_sent(user.chat_id, keyword.phrase, article.url)
                    sent += 1
                    self._increment_sent_today(user.chat_id, sent_today)
        return sent

    def _run_threads_search(self, users, plan_cache: dict[int, object], sent_today: dict[int, int]) -> int:
        if not self.threads.enabled:
            return 0
        eligible: list[tuple[object, object, list[str]]] = []
        search_keys: set[tuple[str, int, int, str]] = set()
        allowed_plans = set(self.config.threads_plan_ids)
        for user in users:
            if user.chat_id not in plan_cache:
                plan_cache[user.chat_id] = self.db.get_active_plan(user.chat_id)
            plan = plan_cache[user.chat_id]
            if allowed_plans and plan.id not in allowed_plans:
                continue
            if not user.threads_search_enabled:
                continue
            if self._daily_limit_reached(user.chat_id, plan, sent_today):
                continue
            keywords = [keyword for keyword in user.keywords if not keyword.paused][: plan.max_keywords]
            if not keywords:
                continue
            eligible.append((user, plan, keywords))
            for keyword in keywords:
                search_keys.add((
                    keyword.phrase,
                    user.threads_search_hours,
                    user.threads_result_limit,
                    user.threads_search_type,
                ))
        if not eligible:
            return 0

        sent = 0
        threads_cache: dict[tuple[str, int, int, str], list[Article]] = {}
        for keyword, hours, limit, search_type in sorted(search_keys):
            try:
                threads_cache[(keyword, hours, limit, search_type)] = [
                    threads_post_to_article(post)
                    for post in self.threads.search(
                        keyword,
                        self.config.source_timeout_seconds,
                        recent_hours=hours,
                        limit=limit,
                        search_type=search_type,
                    )
                ]
            except Exception:
                log.exception("Threads keyword search failed for %s", keyword)
                threads_cache[(keyword, hours, limit, search_type)] = []

        for user, plan, keywords in eligible:
            for keyword in keywords:
                cache_key = (keyword.phrase, user.threads_search_hours, user.threads_result_limit, user.threads_search_type)
                for article in threads_cache.get(cache_key, []):
                    if self._daily_limit_reached(user.chat_id, plan, sent_today):
                        break
                    if self.db.already_sent(user.chat_id, keyword.phrase, article.url):
                        continue
                    if not allowed_by_filters(article.text, user.stop_words, user.plus_words):
                        continue
                    if not contains_phrase(article.text, keyword.phrase):
                        continue
                    if not threads_article_allowed(article, user.threads_media_filter, user.threads_link_filter):
                        continue
                    self.db.save_article(
                        article.url,
                        article.source,
                        article.title,
                        article.published_at,
                        article.summary,
                        "threads",
                    )
                    if not self._send_alert(
                        user.chat_id,
                        keyword.phrase,
                        article,
                        silent=keyword.silent,
                        country_code=keyword.country_code,
                        source_type="threads",
                        plan_id=plan.id,
                    ):
                        continue
                    self.db.mark_sent(user.chat_id, keyword.phrase, article.url)
                    sent += 1
                    self._increment_sent_today(user.chat_id, sent_today)
        return sent

    def _source_users(self, users) -> dict[str, tuple[Source, list]]:
        source_users: dict[str, tuple[Source, list]] = {}
        for user in users:
            keyword_countries = {keyword.country_code for keyword in user.keywords if not keyword.paused}
            for source in self.db.get_enabled_sources(user.chat_id, self.sources, keyword_countries):
                if source.url not in source_users:
                    source_users[source.url] = (source, [])
                source_users[source.url][1].append(user)
        return source_users

    def _send_alert(
        self,
        chat_id: int,
        keyword: str,
        article: Article,
        silent: bool = False,
        country_code: str | None = None,
        source: Source | None = None,
        source_type: str = "",
        plan_id: str = "",
    ) -> bool:
        silent = silent or self.db.keyword_is_silent(chat_id, keyword, country_code)
        settings = self.db.get_user_settings(chat_id)
        template = (
            template_text(settings.language_code, "alert_template")
            if self.config.require_onboarding
            else self.config.alert_template
        )
        published_date, published_time = display_date_time(article.published_at)
        text = template.format(
            keyword=escape(keyword),
            source=escape(article.source),
            title=escape(article.title),
            published_at=escape(display_datetime_line(article.published_at)),
            published_date=escape(published_date),
            published_time=escape(published_time),
            url=escape(article.url),
        )
        if settings.importance_rating_enabled and plan_id in {"pro", "business"}:
            importance = calculate_importance(
                keyword=keyword,
                title=article.title,
                summary=article.summary,
                published_at=article.published_at,
                source_type=source_type or (source.type if source else ""),
                source=source,
            )
            text += "\n\n" + format_importance_block(importance, settings.language_code)
        log.info("Sending alert chat_id=%s keyword=%s silent=%s", chat_id, keyword, silent)
        try:
            self.telegram.send_message(chat_id, text, disable_web_page_preview=False, disable_notification=silent)
        except Exception:
            log.exception("Failed to send Telegram alert chat_id=%s keyword=%s", chat_id, keyword)
            return False
        return True

    def _full_text(
        self,
        article: Article,
        cache: dict[str, str],
        failures: dict[str, int],
        stats: MonitorRunStats,
    ) -> str:
        if article.url.startswith("https://t.me/"):
            stats.full_text_skipped += 1
            return ""
        if not valid_article_url(article.url):
            stats.full_text_skipped += 1
            return ""
        domain = full_text_domain_key(article.url)
        if self.full_text_domain_error_until.get(domain, 0) > time():
            stats.full_text_skipped += 1
            return ""
        if failures.get(domain, 0) >= 3:
            stats.full_text_skipped += 1
            return ""
        if article.url not in cache:
            cached_text = self.db.get_article_full_text(article.url)
            if cached_text is not None:
                cache[article.url] = cached_text
                return cache[article.url]
            stats.full_text_attempted += 1
            started = monotonic()
            try:
                cache[article.url] = fetch_full_text(
                    article.url,
                    self.config.source_timeout_seconds,
                )
                try:
                    self.db.save_article_full_text(article.url, cache[article.url])
                except Exception:
                    log.debug("Не вдалося зберегти кеш повного тексту %s", article.url)
                if cache[article.url]:
                    stats.full_text_succeeded += 1
            except Exception:
                stats.full_text_failed += 1
                failures[domain] = failures.get(domain, 0) + 1
                if failures[domain] == 3:
                    self.full_text_domain_error_until[domain] = time() + FULL_TEXT_DOMAIN_COOLDOWN_SECONDS
                    log.warning("Повний текст для домену %s тимчасово пропущено після 3 помилок", domain)
                else:
                    log.debug("Не вдалося прочитати повний текст %s", article.url)
                cache[article.url] = ""
            finally:
                stats.full_text_duration_seconds += monotonic() - started
        return cache[article.url]


def has_stop_word(text: str, stop_words: tuple[str, ...]) -> bool:
    return any(contains_phrase(text, word) for word in stop_words)


def has_required_plus_word(text: str, plus_words: tuple[str, ...]) -> bool:
    return not plus_words or any(contains_phrase(text, word) for word in plus_words)


def contains_full_text_signal(text: str, phrase: str) -> bool:
    if not contains_phrase(text, phrase):
        return False
    if not is_domain_like_keyword(phrase):
        return True
    return any(
        not is_media_credit_context(text, match.start(), match.end())
        for match in re.finditer(re.escape(phrase), text, flags=re.IGNORECASE)
    )


def is_domain_like_keyword(value: str) -> bool:
    return (
        re.fullmatch(
            r"[a-z0-9][a-z0-9.-]*\.[a-z]{2,}",
            value.strip(),
            flags=re.IGNORECASE,
        )
        is not None
    )


def is_media_credit_context(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 120) : min(len(text), end + 120)].lower()
    left = max(
        text.rfind(".", 0, start),
        text.rfind("!", 0, start),
        text.rfind("?", 0, start),
        text.rfind("\n", 0, start),
    )
    right_candidates = [
        pos
        for pos in (
            text.find(".", end),
            text.find("!", end),
            text.find("?", end),
            text.find("\n", end),
        )
        if pos >= 0
    ]
    right = min(right_candidates) if right_candidates else min(len(text), end + 160)
    sentence = text[left + 1 : right].lower()
    tail = text[right + 1 : min(len(text), right + 80)].lower()
    credit_markers = (
        "\u0444\u043e\u0442\u043e",
        "\u043a\u043e\u043b\u0430\u0436",
        "\u0456\u043b\u044e\u0441\u0442\u0440\u0430\u0446",
        "\u0438\u043b\u043b\u044e\u0441\u0442\u0440\u0430\u0446",
        "\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u043d",
        "\u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d",
        "\u0441\u043a\u0440\u0438\u043d\u0448\u043e\u0442",
        "photo",
        "image",
        "collage",
        "credit",
    )
    if any(marker in sentence for marker in credit_markers):
        return True
    if any(marker in window for marker in credit_markers):
        return True
    return len(sentence) <= 140 and any(marker in tail for marker in ("\u043a\u043e\u043b\u0430\u0436", "collage"))


def full_text_domain_key(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    parts = domain.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in {"com.ua", "net.ua", "org.ua"}:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


def article_priority_timestamp(article: Article) -> float:
    value = (article.published_at or "").strip()
    if value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except ValueError:
            pass
    return time()


def source_fetch_shard_key(source: Source) -> str:
    country = normalize_country(source.country)
    source_type = str(source.type or "rss").strip().lower()
    if source_type in {"telegram", "telegram_paid"}:
        kind = "telegram"
    elif source_type in {"registry", "prozorro", "prozorro_plan", "prozorro_sale", "rada_bills"}:
        kind = "registry"
    else:
        kind = "rss"
    return f"{country}:{kind}"


def source_queue_key(source: Source) -> str:
    source_type = str(source.type or "rss").strip().lower()
    if source_type in {"telegram", "telegram_paid"}:
        return "telegram"
    if source_type in {"registry", "prozorro", "prozorro_plan", "prozorro_sale", "rada_bills"}:
        return "registry"
    return "rss"


def split_source_fetch_groups(
    source_groups: dict[str, list[Source]],
    bucket_size: int,
) -> list[tuple[str, list[Source]]]:
    groups: list[tuple[str, list[Source]]] = []
    bucket_size = max(1, bucket_size)
    for shard, sources in sorted(source_groups.items()):
        if len(sources) <= bucket_size:
            groups.append((shard, sources))
            continue
        for index, start in enumerate(range(0, len(sources), bucket_size), start=1):
            groups.append((f"{shard}#{index}", sources[start : start + bucket_size]))
    return groups


def source_error_needs_hard_cooldown(error: BaseException | None) -> bool:
    if error is None:
        return False
    if isinstance(error, requests.exceptions.SSLError):
        return True
    if isinstance(error, requests.exceptions.HTTPError):
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
        return status_code in {403, 404, 410, 428, 429}
    if isinstance(error, requests.exceptions.Timeout):
        return "Response body read exceeded" in str(error)
    return isinstance(error, ValueError) and "Response body exceeded" in str(error)


def safe_thread_label(value: str) -> str:
    label = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip())[:24].strip("-")
    return label or "sources"


def fetch_articles(source: Source, timeout: int) -> list[Article]:
    if source.type in {"rss", "registry"}:
        return fetch_rss(source, timeout)
    if source.type in {"telegram", "telegram_paid"}:
        return fetch_telegram_channel(source, timeout)
    if source.type == "prozorro":
        return fetch_prozorro_tenders(source, timeout)
    if source.type == "prozorro_plan":
        return fetch_prozorro_plans(source, timeout)
    if source.type == "prozorro_sale":
        return fetch_prozorro_sale_procedures(source, timeout)
    if source.type == "rada_bills":
        return fetch_rada_bills(source, timeout)
    log.warning("Непідтримуваний тип джерела %s для %s", source.type, source.name)
    return []


def threads_post_to_article(post: ThreadsPost) -> Article:
    return Article(
        source=post.source,
        title=post.title,
        url=post.url,
        published_at=post.published_at,
        summary=post.summary,
        hidden_links=join_search_parts(post.media_type, post.link_url),
    )


def reddit_post_to_article(post: RedditPost) -> Article:
    return Article(
        source=post.source,
        title=post.title,
        url=post.url,
        published_at=post.published_at,
        summary=post.summary,
        hidden_links=join_search_parts(f"score:{post.score}", f"comments:{post.comments}"),
    )


def threads_article_allowed(article: Article, media_filter: str, link_filter: str) -> bool:
    meta = f"{article.hidden_links}\n{article.summary}"
    has_media = any(marker in article.hidden_links.upper().split() for marker in ("IMAGE", "VIDEO", "CAROUSEL_ALBUM"))
    has_link = bool(re.search(r"https?://", meta))
    if media_filter == "media" and not has_media:
        return False
    if media_filter == "no_media" and has_media:
        return False
    if link_filter == "link" and not has_link:
        return False
    if link_filter == "no_link" and has_link:
        return False
    return True


def fetch_prozorro_tenders(source: Source, timeout: int) -> list[Article]:
    response = requests.get(
        source.url,
        timeout=timeout,
        headers={
            "User-Agent": "MediaMonitorBot/0.1 (+local Telegram monitoring bot)",
            "Accept": "application/json",
        },
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("data", []) if isinstance(payload, dict) else []
    articles: list[Article] = []

    for item in items[:ARTICLE_LIMIT_PER_SOURCE]:
        if not isinstance(item, dict):
            continue
        tender_uuid = str(item.get("id") or "").strip()
        if not tender_uuid:
            continue
        detail_url = f"{PROZORRO_API_BASE}/tenders/{tender_uuid}"
        try:
            detail_response = requests.get(
                detail_url,
                timeout=timeout,
                headers={
                    "User-Agent": "MediaMonitorBot/0.1 (+local Telegram monitoring bot)",
                    "Accept": "application/json",
                },
            )
            detail_response.raise_for_status()
            detail_payload = detail_response.json()
        except Exception:
            log.debug("Не вдалося отримати деталі Prozorro %s", tender_uuid)
            continue
        tender = detail_payload.get("data", {}) if isinstance(detail_payload, dict) else {}
        if not isinstance(tender, dict):
            continue
        article = prozorro_tender_to_article(
            tender,
            source,
            fallback_date=str(item.get("dateModified") or ""),
            detail_url=detail_url,
        )
        if article:
            articles.append(article)
    return articles


def fetch_prozorro_plans(source: Source, timeout: int) -> list[Article]:
    response = requests.get(
        source.url,
        timeout=timeout,
        headers={
            "User-Agent": "MediaMonitorBot/0.1 (+local Telegram monitoring bot)",
            "Accept": "application/json",
        },
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("data", []) if isinstance(payload, dict) else []
    articles: list[Article] = []

    for item in items[:ARTICLE_LIMIT_PER_SOURCE]:
        if not isinstance(item, dict):
            continue
        plan_uuid = str(item.get("id") or "").strip()
        if not plan_uuid:
            continue
        detail_url = f"{PROZORRO_API_BASE}/plans/{plan_uuid}"
        try:
            detail_response = requests.get(
                detail_url,
                timeout=timeout,
                headers={
                    "User-Agent": "MediaMonitorBot/0.1 (+local Telegram monitoring bot)",
                    "Accept": "application/json",
                },
            )
            detail_response.raise_for_status()
            detail_payload = detail_response.json()
        except Exception:
            log.debug("Не вдалося отримати деталі плану Prozorro %s", plan_uuid)
            continue
        plan = detail_payload.get("data", {}) if isinstance(detail_payload, dict) else {}
        if not isinstance(plan, dict):
            continue
        article = prozorro_plan_to_article(
            plan,
            source,
            fallback_date=str(item.get("dateModified") or ""),
            detail_url=detail_url,
        )
        if article:
            articles.append(article)
    return articles


def fetch_prozorro_sale_procedures(source: Source, timeout: int) -> list[Article]:
    url = prozorro_sale_recent_url(source.url)
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": "MediaMonitorBot/0.1 (+local Telegram monitoring bot)",
            "Accept": "application/json",
        },
    )
    response.raise_for_status()
    payload = response.json()
    items = payload if isinstance(payload, list) else payload.get("data", []) if isinstance(payload, dict) else []
    articles: list[Article] = []
    for item in items[:ARTICLE_LIMIT_PER_SOURCE]:
        if not isinstance(item, dict):
            continue
        article = prozorro_sale_procedure_to_article(item, source)
        if article:
            articles.append(article)
    return articles


def fetch_rada_bills(source: Source, timeout: int) -> list[Article]:
    response = requests.get(
        source.url,
        timeout=timeout,
        headers={
            "User-Agent": "MediaMonitorBot/0.1 (+local Telegram monitoring bot)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    response.raise_for_status()
    html = response.content.decode("cp1251", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    articles: list[Article] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = str(link.get("href") or "")
        if "webproc4_1" not in href:
            continue
        row = link.find_parent("tr")
        if row is None:
            continue
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
        if len(cells) < 3:
            continue
        number = cells[0].strip()
        date_text = cells[1].strip()
        title = cells[2].strip()
        if not number or not title or number in seen:
            continue
        seen.add(number)
        url = urljoin(source.url, href)
        authors = "; ".join(part for part in cells[3:] if part)
        articles.append(
            Article(
                source=clean_source_display_name(source.name),
                title=f"{number}: {title}",
                url=url,
                published_at=date_text,
                summary=join_search_parts(f"Автори/ініціатори: {authors}" if authors else ""),
                hidden_links=join_search_parts(number, authors),
            )
        )
        if len(articles) >= ARTICLE_LIMIT_PER_SOURCE:
            break
    return articles


def prozorro_sale_recent_url(url: str) -> str:
    if "/byDateModified/" not in url:
        return url
    since = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(timespec="seconds").replace("+00:00", "Z")
    return re.sub(r"/byDateModified/[^?]+", f"/byDateModified/{since}", url, count=1)


def prozorro_plan_to_article(
    plan: dict[str, Any],
    source: Source,
    *,
    fallback_date: str,
    detail_url: str,
) -> Article | None:
    budget = plan.get("budget") if isinstance(plan.get("budget"), dict) else {}
    classification = plan.get("classification") if isinstance(plan.get("classification"), dict) else {}
    plan_id = strip_html(str(plan.get("planID") or "")).strip()
    title = strip_html(str(budget.get("description") or classification.get("description") or plan_id or "")).strip()
    if not title:
        return None

    procuring_entity = plan.get("procuringEntity") if isinstance(plan.get("procuringEntity"), dict) else {}
    buyer = party_label(procuring_entity)
    buyer_region = address_label(procuring_entity.get("address") if isinstance(procuring_entity, dict) else {})
    value = money_label(budget)
    method = ""
    tender = plan.get("tender") if isinstance(plan.get("tender"), dict) else {}
    if tender:
        method = strip_html(str(tender.get("procurementMethodType") or tender.get("procurementMethod") or "")).strip()
    published_at = str(
        plan.get("dateModified")
        or plan.get("datePublished")
        or plan.get("dateCreated")
        or fallback_date
        or ""
    )
    classification_text = join_search_parts(
        strip_html(str(classification.get("id") or "")).strip(),
        strip_html(str(classification.get("description") or "")).strip(),
    )
    public_url = f"{PROZORRO_PUBLIC_PLAN_BASE}{plan_id}" if plan_id else detail_url
    summary = join_search_parts(
        f"Замовник: {buyer}" if buyer else "",
        f"Регіон: {buyer_region}" if buyer_region else "",
        f"Очікувана вартість: {value}" if value else "",
        f"Процедура: {method}" if method else "",
        f"Класифікація: {classification_text}" if classification_text else "",
    )
    return Article(
        source=clean_source_display_name(source.name),
        title=title,
        url=public_url,
        published_at=published_at,
        summary=summary,
        hidden_links=join_search_parts(plan_id, buyer, buyer_region, classification_text),
    )


def prozorro_sale_procedure_to_article(procedure: dict[str, Any], source: Source) -> Article | None:
    auction_id = localized_text(procedure.get("auctionId") or procedure.get("lotId") or procedure.get("_id"))
    title = localized_text(procedure.get("title")).strip() or auction_id
    if not title:
        return None

    date_modified = localized_text(
        procedure.get("dateModified")
        or procedure.get("_meta", {}).get("systemDateModified")
        or procedure.get("datePublished")
    )
    selling_entity = procedure.get("sellingEntity") if isinstance(procedure.get("sellingEntity"), dict) else {}
    seller = party_label(selling_entity)
    seller_address = address_label(selling_entity.get("address") if isinstance(selling_entity, dict) else {})
    value = money_label(procedure.get("value"))
    status = localized_text(procedure.get("status"))
    selling_method = localized_text(procedure.get("sellingMethod") or procedure.get("saleType"))
    description = localized_text(procedure.get("description"))
    auction_url = localized_text(procedure.get("auctionUrl"))
    public_url = auction_url or (f"{PROZORRO_SALE_PUBLIC_BASE}{auction_id}" if auction_id else source.url)

    item_parts: list[str] = []
    classification_parts: list[str] = []
    for item in procedure.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        item_parts.append(localized_text(item.get("description")))
        item_parts.append(address_label(item.get("address") if isinstance(item.get("address"), dict) else {}))
        for classification in item.get("additionalClassifications", []) or []:
            if isinstance(classification, dict):
                classification_parts.append(
                    join_search_parts(
                        localized_text(classification.get("id")),
                        localized_text(classification.get("description")),
                    )
                )

    summary = join_search_parts(
        description,
        f"Організатор: {seller}" if seller else "",
        f"Регіон: {seller_address}" if seller_address else "",
        f"Вартість: {value}" if value else "",
        f"Статус: {status}" if status else "",
        f"Тип продажу: {selling_method}" if selling_method else "",
        f"Об'єкт: {'; '.join(unique_limited(item_parts, 5))}" if item_parts else "",
    )
    hidden_links = join_search_parts(
        auction_id,
        localized_text(procedure.get("_id")),
        localized_text(procedure.get("archiveId")),
        " ".join(unique_limited(classification_parts, 8)),
        public_url,
    )
    return Article(
        source=clean_source_display_name(source.name),
        title=title,
        url=public_url,
        published_at=date_modified,
        summary=summary,
        hidden_links=hidden_links,
    )


def prozorro_tender_to_article(
    tender: dict[str, Any],
    source: Source,
    *,
    fallback_date: str,
    detail_url: str,
) -> Article | None:
    title = strip_html(str(tender.get("title") or "")).strip()
    tender_id = str(tender.get("tenderID") or "").strip()
    if not title and tender_id:
        title = tender_id
    if not title:
        return None

    procuring_entity = tender.get("procuringEntity") if isinstance(tender.get("procuringEntity"), dict) else {}
    buyer = party_label(procuring_entity)
    buyer_address = procuring_entity.get("address", {}) if isinstance(procuring_entity, dict) else {}
    buyer_region = address_label(buyer_address)
    value = money_label(tender.get("value"))
    status = strip_html(str(tender.get("status") or "")).strip()
    procedure = strip_html(str(tender.get("procurementMethodType") or tender.get("procurementMethod") or "")).strip()
    category = strip_html(str(tender.get("mainProcurementCategory") or "")).strip()
    published_at = str(
        tender.get("dateModified")
        or tender.get("date")
        or tender.get("dateCreated")
        or fallback_date
        or ""
    )
    public_url = f"{PROZORRO_PUBLIC_TENDER_BASE}{tender_id}" if tender_id else detail_url

    item_parts: list[str] = []
    classification_parts: list[str] = []
    for item in tender.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        item_description = strip_html(str(item.get("description") or "")).strip()
        if item_description:
            item_parts.append(item_description)
        classification = item.get("classification")
        if isinstance(classification, dict):
            classification_parts.append(
                join_search_parts(
                    str(classification.get("id") or ""),
                    str(classification.get("description") or ""),
                )
            )
        delivery_address = item.get("deliveryAddress")
        delivery_label = address_label(delivery_address) if isinstance(delivery_address, dict) else ""
        if delivery_label:
            item_parts.append(delivery_label)

    supplier_parts: list[str] = []
    for award in tender.get("awards", []) or []:
        if not isinstance(award, dict):
            continue
        for supplier in award.get("suppliers", []) or []:
            if isinstance(supplier, dict):
                supplier_parts.append(party_label(supplier))

    item_parts = unique_limited(item_parts, 5)
    classification_parts = unique_limited(classification_parts, 8)
    supplier_parts = unique_limited([part for part in supplier_parts if part], 5)

    summary = join_search_parts(
        str(tender.get("description") or ""),
        f"Замовник: {buyer}" if buyer else "",
        f"Регіон: {buyer_region}" if buyer_region else "",
        f"Очікувана вартість: {value}" if value else "",
        f"Статус: {status}" if status else "",
        f"Процедура: {procedure}" if procedure else "",
        f"Категорія: {category}" if category else "",
        f"Предмет закупівлі: {'; '.join(item_parts)}" if item_parts else "",
        f"Постачальники: {'; '.join(supplier_parts)}" if supplier_parts else "",
    )
    hidden_links = join_search_parts(
        tender_id,
        str(tender.get("id") or ""),
        " ".join(classification_parts),
        public_url,
        detail_url,
    )
    return Article(
        source=clean_source_display_name(source.name),
        title=title,
        url=public_url,
        published_at=published_at,
        summary=summary,
        hidden_links=hidden_links,
    )


def party_label(value: dict[str, Any] | None) -> str:
    if not isinstance(value, dict):
        return ""
    identifier = value.get("identifier") if isinstance(value.get("identifier"), dict) else {}
    return join_search_parts(
        localized_text(value.get("name")),
        str(identifier.get("id") or ""),
        localized_text(identifier.get("legalName")),
    )


def address_label(value: dict[str, Any] | None) -> str:
    if not isinstance(value, dict):
        return ""
    return join_search_parts(
        localized_text(value.get("region")),
        localized_text(value.get("locality")),
        localized_text(value.get("streetAddress")),
    )


def localized_text(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("uk_UA", "uk", "en_US", "en", "ru_RU", "ru"):
            text = value.get(key)
            if text:
                return strip_html(str(text)).strip()
        for text in value.values():
            if text:
                return strip_html(str(text)).strip()
        return ""
    return strip_html(str(value or "")).strip()


def money_label(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    amount = value.get("amount")
    currency = value.get("currency") or ""
    if amount is None:
        return ""
    return join_search_parts(str(amount), str(currency))


def unique_limited(values: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = strip_html(str(value or "")).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def fetch_rss(source: Source, timeout: int) -> list[Article]:
    response = requests.get(
        source.url,
        timeout=timeout,
        stream=True,
        headers={
            "User-Agent": "MediaMonitorBot/0.1 (+local Telegram monitoring bot)",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    with response:
        response.raise_for_status()
        body = limited_response_body(
            response,
            wall_timeout_seconds=max(3.0, float(timeout)),
            max_bytes=RSS_RESPONSE_MAX_BYTES,
        )
    parsed = feedparser.parse(body)
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
                source=clean_source_display_name(source.name),
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
                source=clean_source_display_name(source.name),
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


def limited_response_body(
    response: requests.Response,
    *,
    wall_timeout_seconds: float,
    max_bytes: int,
) -> bytes:
    started = monotonic()
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=RSS_RESPONSE_CHUNK_SIZE):
        elapsed = monotonic() - started
        if elapsed > wall_timeout_seconds:
            raise requests.exceptions.Timeout(
                f"Response body read exceeded {wall_timeout_seconds:.1f}s for {response.url}"
            )
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"Response body exceeded {max_bytes} bytes for {response.url}")
        chunks.append(chunk)
    return b"".join(chunks)


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
            return f"https://telegram.me/s/{parts[1]}"
        if parts:
            return f"https://telegram.me/s/{parts[0]}"
    username = raw.lstrip("@")
    return f"https://telegram.me/s/{username}"

