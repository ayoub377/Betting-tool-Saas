import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.odds_tracker.odds_tracker import (
    store_odds_snapshot, get_match_meta,
    unregister_match, TRACKED_INDEX_KEY
)
from app.core.config import SCRAPE_INTERVAL_SECONDS, STOP_BEFORE_KICKOFF_SECONDS

logger = logging.getLogger(__name__)

# Single shared scheduler instance — imported by the FastAPI app
scheduler = AsyncIOScheduler()

io_executor = ThreadPoolExecutor(max_workers=50)


def make_scrape_job(match_id: str, scraper, redis_client):
    """
    Returns an async function used as the APScheduler job.
    Captures match_id, scraper, and redis_client in closure.
    """

    async def scrape_job():
        logger.info("Running scheduled odds scrape for match %s", match_id)

        meta = await get_match_meta(redis_client, match_id)
        if meta:
            start_time_str = meta.get("start_time")
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str)
                time_until_start = start_time - datetime.now(timezone.utc)
                if time_until_start <= timedelta(seconds=STOP_BEFORE_KICKOFF_SECONDS):
                    logger.info("Match %s starts in %s — stopping tracker.", match_id, time_until_start)
                    await unregister_match(redis_client, match_id)
                    scheduler.remove_job(job_id(match_id))
                    return

        try:
            loop = asyncio.get_event_loop()
            odds = await loop.run_in_executor(
                io_executor,
                scraper.get_odds_by_match_id,
                match_id
            )
            if odds.get("home") is not None:
                await store_odds_snapshot(redis_client, match_id, odds)
            else:
                logger.warning("No valid odds returned for match %s", match_id)
        except Exception as e:
            logger.error("Scrape job failed for match %s: %s", match_id, e, exc_info=True)

    return scrape_job


def job_id(match_id: str) -> str:
    return f"odds_scrape_{match_id}"


def start_tracking_job(match_id: str, scraper, redis_client, initial_delay: float = 0):
    """
    Schedules a job.
    initial_delay: seconds to wait before the very first execution (useful for restarts).
    """
    run_time = datetime.now(timezone.utc) + timedelta(seconds=initial_delay)

    scheduler.add_job(
        make_scrape_job(match_id, scraper, redis_client),
        trigger=IntervalTrigger(seconds=SCRAPE_INTERVAL_SECONDS),
        id=job_id(match_id),
        replace_existing=True,
        next_run_time=run_time,
    )
    logger.info("Match %s scheduled (Start delay: %.1fs)", match_id, initial_delay)


def stop_tracking_job(match_id: str):
    jid = job_id(match_id)
    if scheduler.get_job(jid):
        scheduler.remove_job(jid)
        logger.info("Removed tracking job for match %s.", match_id)
