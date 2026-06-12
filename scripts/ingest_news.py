from app.db.session import SessionLocal
from app.ingestion.news_ingestor import NewsIngestor


def main() -> None:
    with SessionLocal() as db:
        count = NewsIngestor(db).ingest()
    print(f"Inserted {count} news articles.")


if __name__ == "__main__":
    main()
