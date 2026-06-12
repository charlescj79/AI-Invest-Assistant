from datetime import date, timedelta

from app.db.session import SessionLocal
from app.ingestion.market_ingestor import MarketIngestor


def main() -> None:
    end = date.today()
    start = end - timedelta(days=365 * 2)
    symbols = ["SPY", "QQQ"]
    with SessionLocal() as db:
        count = MarketIngestor(db).ingest(symbols=symbols, start=start, end=end)
    print(f"Upserted {count} market rows.")


if __name__ == "__main__":
    main()
