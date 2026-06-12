from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


def _create_engine():
    url = get_settings().database_url
    if url == "sqlite://":
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url)


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
