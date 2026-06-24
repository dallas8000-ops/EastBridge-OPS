import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

import feedparser
import httpx
from bs4 import BeautifulSoup

from .base import FetchedItem

logger = logging.getLogger(__name__)

USER_AGENT = "EastBridge-Ops-Intelligence/1.0 (+https://github.com/eastbridge; compliance monitoring)"


def _http_get(url: str, timeout: float = 30.0) -> str:
    with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value[:19], fmt[: len(value[:19]) + 2] if "T" in fmt else fmt)
        except ValueError:
            continue
    return None


def fetch_rss(feed_url: str, max_items: int = 20) -> list[FetchedItem]:
    """Fetch items from an RSS or Atom feed."""
    try:
        raw = _http_get(feed_url)
        parsed = feedparser.parse(raw)
    except httpx.HTTPError:
        parsed = feedparser.parse(
            feed_url,
            agent=USER_AGENT,
            request_headers={"User-Agent": USER_AGENT},
        )

    if not parsed.entries:
        detail = parsed.bozo_exception if parsed.bozo else "no entries"
        raise ValueError(f"RSS parse error for {feed_url}: {detail}")

    items: list[FetchedItem] = []
    for entry in parsed.entries[:max_items]:
        external_id = entry.get("id") or entry.get("link") or entry.get("title", "")
        if not external_id:
            continue

        content = ""
        if entry.get("content"):
            content = entry.content[0].get("value", "")
        content = content or entry.get("summary", "") or entry.get("description", "")
        content = BeautifulSoup(content, "lxml").get_text(separator="\n", strip=True)

        published = _parse_date(entry.get("published") or entry.get("updated"))
        items.append(
            FetchedItem(
                external_id=external_id[:512],
                title=(entry.get("title") or "Untitled")[:500],
                url=entry.get("link") or feed_url,
                content=content or entry.get("title", ""),
                published_at=published.date() if published else None,
            )
        )
    return items


def fetch_html_list(
    list_url: str,
    link_selector: str = "a",
    max_items: int = 15,
    base_url: str | None = None,
) -> list[FetchedItem]:
    """Fetch notice titles and pages from an HTML listing page."""
    html = _http_get(list_url)
    soup = BeautifulSoup(html, "lxml")
    base = base_url or list_url
    seen_urls: set[str] = set()
    items: list[FetchedItem] = []

    for anchor in soup.select(link_selector):
        href = anchor.get("href")
        title = anchor.get_text(strip=True)
        if not href or not title or len(title) < 10:
            continue

        url = urljoin(base, href)
        if url in seen_urls or url == list_url:
            continue
        seen_urls.add(url)

        try:
            page_html = _http_get(url)
            page_soup = BeautifulSoup(page_html, "lxml")
            for tag in page_soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            main = page_soup.find("article") or page_soup.find("main") or page_soup.body
            content = main.get_text(separator="\n", strip=True)[:8000] if main else title
        except httpx.HTTPError as exc:
            logger.warning("Failed to fetch %s: %s", url, exc)
            content = title

        items.append(
            FetchedItem(
                external_id=url[:512],
                title=title[:500],
                url=url,
                content=content,
                published_at=None,
            )
        )
        if len(items) >= max_items:
            break

    return items
