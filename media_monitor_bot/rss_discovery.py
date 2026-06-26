from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import brotli
import feedparser
import requests
from bs4 import BeautifulSoup


USER_AGENT = "Mozilla/5.0 (compatible; MonitorioBot/1.0; RSS discovery)"
FEED_TYPES = {
    "application/rss+xml",
    "application/atom+xml",
    "application/feed+json",
    "application/rdf+xml",
    "text/xml",
    "application/xml",
}
COMMON_FEED_PATHS = (
    "/rss",
    "/rss.xml",
    "/feed",
    "/feed/",
    "/feed.xml",
    "/atom.xml",
    "/index.xml",
)


@dataclass(frozen=True)
class DiscoveredFeed:
    url: str
    title: str


class RssDiscoveryError(Exception):
    pass


def discover_rss_feed(value: str, timeout: int = 15) -> DiscoveredFeed:
    url = normalize_site_url(value)
    if not url:
        raise RssDiscoveryError("invalid_url")

    candidates = [url]
    try:
        html = fetch_text(url, timeout)
    except requests.RequestException as exc:
        raise RssDiscoveryError("read_failed") from exc

    parsed_direct = parse_feed(html, url)
    if parsed_direct:
        return parsed_direct

    candidates.extend(find_alternate_feeds(html, url))
    candidates.extend(common_feed_candidates(url))

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            text = html if candidate == url else fetch_text(candidate, timeout)
        except requests.RequestException:
            continue
        feed = parse_feed(text, candidate)
        if feed:
            return feed

    raise RssDiscoveryError("feed_not_found")


def normalize_site_url(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        raw = "https:" + raw
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return raw


def fetch_text(url: str, timeout: int) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
        },
    )
    response.raise_for_status()
    body = response_body(response)
    encoding = response.encoding or response.apparent_encoding or "utf-8"
    return body.decode(encoding, errors="replace")


def parse_feed(text: str, url: str) -> DiscoveredFeed | None:
    parsed = feedparser.parse(text)
    if not parsed.entries:
        return None
    title = str(parsed.feed.get("title") or source_name_from_url(url)).strip()
    return DiscoveredFeed(url=url, title=title[:80] or source_name_from_url(url))


def find_alternate_feeds(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    feeds: list[str] = []
    for link in soup.select("link[href]"):
        rel = " ".join(link.get("rel") or []).lower()
        content_type = str(link.get("type") or "").split(";", 1)[0].strip().lower()
        title = str(link.get("title") or "").lower()
        if "alternate" not in rel and "feed" not in rel:
            continue
        if content_type not in FEED_TYPES and "rss" not in title and "atom" not in title:
            continue
        href = str(link.get("href") or "").strip()
        if href:
            feeds.append(urljoin(base_url, href))
    return feeds


def common_feed_candidates(site_url: str) -> list[str]:
    parsed = urlparse(site_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    return [urljoin(root, path) for path in COMMON_FEED_PATHS]


def response_body(response: requests.Response) -> bytes:
    content = response.content
    if response.headers.get("Content-Encoding", "").lower() == "br" and not content.lstrip().startswith(b"<"):
        try:
            return brotli.decompress(content)
        except brotli.error:
            return content
    return content


def source_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc or "My source"
