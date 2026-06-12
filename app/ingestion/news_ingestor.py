from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_sources.registry import get_news_provider
from app.db.models import Asset, NewsArticle, NewsAssetLink
from app.ingestion.dedupe import news_dedupe_hash
from app.ingestion.normalize import normalize_symbol


class NewsIngestor:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ingest(self, feeds: list[str] | None = None, symbols: list[str] | None = None) -> int:
        provider = get_news_provider(feeds=feeds)
        items = provider.fetch_latest()
        normalized_symbols = [normalize_symbol(symbol) for symbol in symbols or []]
        if not normalized_symbols:
            normalized_symbols = [asset.symbol for asset in self.db.scalars(select(Asset).where(Asset.is_active))]

        inserted = 0
        for item in items:
            dedupe_hash = news_dedupe_hash(item.title, item.url)
            exists = self.db.scalar(select(NewsArticle).where(NewsArticle.dedupe_hash == dedupe_hash))
            if exists is not None:
                continue
            article = NewsArticle(
                title=item.title,
                url=item.url,
                source=item.source,
                published_at=item.published_at,
                raw_text=item.raw_text,
                summary=item.summary,
                dedupe_hash=dedupe_hash,
            )
            self.db.add(article)
            self.db.flush()
            self._link_symbols(article, normalized_symbols)
            inserted += 1
        self.db.commit()
        return inserted

    def _link_symbols(self, article: NewsArticle, symbols: list[str]) -> None:
        haystack = f"{article.title} {article.raw_text or ''}".upper()
        for symbol in symbols:
            if symbol not in haystack:
                continue
            asset = self.db.scalar(select(Asset).where(Asset.symbol == symbol))
            if asset is None:
                continue
            self.db.add(
                NewsAssetLink(
                    news_id=article.id,
                    asset_id=asset.id,
                    relevance=0.5,
                    reason=f"Symbol {symbol} appears in headline or summary.",
                )
            )
