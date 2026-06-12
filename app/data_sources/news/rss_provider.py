from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from app.config import get_settings
from app.data_sources.base import NewsItem, NewsProvider


class RSSNewsProvider(NewsProvider):
    source = "rss"

    def __init__(self, feeds: list[str] | None = None) -> None:
        self.feeds = feeds or get_settings().news_feed_urls

    def fetch_latest(self, query: str | None = None) -> list[NewsItem]:
        items: list[NewsItem] = []
        query_lower = query.lower() if query else None
        for feed_url in self.feeds:
            parsed = feedparser.parse(feed_url)
            source = parsed.feed.get("title", feed_url)
            for entry in parsed.entries:
                title = entry.get("title", "").strip()
                summary = entry.get("summary")
                text = " ".join(part for part in [title, summary] if part)
                if query_lower and query_lower not in text.lower():
                    continue
                url = entry.get("link")
                if not title or not url:
                    continue
                items.append(
                    NewsItem(
                        title=title,
                        url=url,
                        source=source,
                        published_at=_parse_published(entry),
                        raw_text=summary,
                        summary=summary,
                    )
                )
        return items

    def fetch_by_symbol(self, symbol: str) -> list[NewsItem]:
        return self.fetch_latest(query=symbol)


def _parse_published(entry) -> datetime | None:
    value = entry.get("published") or entry.get("updated")
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
