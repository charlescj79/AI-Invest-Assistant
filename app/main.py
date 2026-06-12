from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import advice, backtests, health, market, news, portfolios, symbols, system
from app.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.logging import configure_logging
from app.scheduler.scheduler import build_scheduler

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler = None
    if settings.scheduler_enabled:
        scheduler = build_scheduler()
        scheduler.start()
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, lifespan=lifespan)


app.include_router(health.router)
app.include_router(symbols.router)
app.include_router(market.router)
app.include_router(news.router)
app.include_router(backtests.router)
app.include_router(advice.router)
app.include_router(portfolios.router)
app.include_router(system.router)
