from apscheduler.schedulers.background import BackgroundScheduler

from app.scheduler.jobs import generate_daily_brief_job, ingest_market_job, ingest_news_job


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="America/New_York")
    scheduler.add_job(ingest_news_job, "cron", hour=8, minute=0, id="ingest_news")
    scheduler.add_job(ingest_market_job, "cron", hour=16, minute=30, id="ingest_market")
    scheduler.add_job(generate_daily_brief_job, "cron", hour=18, minute=0, id="daily_brief")
    return scheduler
