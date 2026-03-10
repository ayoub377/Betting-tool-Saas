import asyncio
import json
import logging
import os
from typing import List, Optional
import re

import shin
from fastapi import APIRouter, HTTPException, Depends, Query
import requests
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

# from app.core.auth import has_access
from app.core.config import redis_client, rate_limit_dependency
# from app.models.odds import MatchData, Outcome, H2HMarket, Bookmaker
from dotenv import load_dotenv
from app.services.flashscore_scraper.flashscore_scraper import FlashScoreScraper
from app.services.odds_tracker.odds_tracker import (
    register_match, is_already_tracked,
    get_all_tracked_ids, get_match_meta,
    get_odds_history,unregister_match,
)
from app.services.odds_tracker.odds_scheduler import start_tracking_job, scheduler, stop_tracking_job
from app.core.config import SCRAPE_INTERVAL_SECONDS
from app.services.odds_tracker.odds_tracker import store_odds_snapshot
from app.models.database import SessionLocal
from app.services.odds_tracker.snapshot_persistence import (
    get_match_snapshots as db_get_snapshots,
    get_match_meta_from_db,
)

load_dotenv()
router = APIRouter()


# league = ''
# API_KEY = os.getenv("ODDS_API_KEY")
def get_redis():
    return redis_client


# Cache expiry time in seconds (30 minutes)
CACHE_EXPIRY = 30 * 60

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


# Fetch data from API
# async def fetch_api_data(name):
#     cache_key = f"odds_api:{name}"
#     cached_data = await redis_client.get(cache_key)
#     if cached_data:
#         # If cached data exists, return it
#         return json.loads(cached_data)
#
#     url = f"https://api.the-odds-api.com/v4/sports/{name}/odds?apiKey={API_KEY}&regions=eu&markets=h2h,spreads&oddsFormat=decimal"
#     try:
#         response = requests.get(url, timeout=15)
#     except requests.RequestException as e:
#         raise HTTPException(status_code=502, detail=f"Failed to reach Odds API: {str(e)}")
#     data = response.json()
#     if response.status_code == 200:
#         # Store the data in the cache with an expiry time
#         await redis_client.setex(cache_key, CACHE_EXPIRY, json.dumps(data))
#
#         return data  # Parse JSON response and return list of matches
#     else:
#         raise HTTPException(status_code=500, detail="Failed to fetch data from the Odds API.")
#
#
# # extract h2h data
# # def extract_bookmaker_data(matches: List[dict], selected_bookmakers=None) -> List[MatchData]:
# #     if selected_bookmakers is None:
# #         selected_bookmakers = ["pinnacle"]
# #     elif "pinnacle" not in selected_bookmakers:
# #         selected_bookmakers.append("pinnacle")  # Ensure Pinnacle is included
# #
# #     match_data_list = []
# #
# #     for match in matches:
# #         if "home_team" not in match or "away_team" not in match or "commence_time" not in match:
# #             continue
# #
# #         bookmakers = []
# #
# #         for bookmaker in match.get("bookmakers", []):
# #             if bookmaker["key"] in selected_bookmakers:
# #                 h2h_markets = [
# #                     H2HMarket(
# #                         key=market["key"],
# #                         outcomes=[
# #                             Outcome(name=outcome["name"], price=outcome["price"])
# #                             for outcome in market.get("outcomes", [])
# #                         ],
# #                     )
# #                     for market in bookmaker.get("markets", [])
# #                     if market["key"] == "h2h"
# #                 ]
# #
# #                 if h2h_markets:
# #                     bookmakers.append(Bookmaker(name=bookmaker["key"], markets=h2h_markets))
# #
# #         if bookmakers:
# #             match_data_list.append(
# #                 MatchData(
# #                     home_team=match["home_team"],
# #                     away_team=match["away_team"],
# #                     commence_time=match["commence_time"],
# #                     bookmakers=bookmakers,
# #                 )
# #             )
# #
# #     return match_data_list
#
# # Filter matches by start time
#
# def extract_bookmaker_data(matches: List[dict], selected_bookmakers: Optional[List[str]] = None) -> List[MatchData]:
#     # Normalize bookmaker names (case insensitive) and ensure Pinnacle is included
#     selected_bookmakers = set(bookmaker.lower() for bookmaker in (selected_bookmakers or ["Pinnacle"]))
#     selected_bookmakers.add("pinnacle")  # Always ensure Pinnacle is included
#     match_data_list = []
#
#     for match in matches:
#         # Ensure required match fields exist
#         if not all(key in match for key in ["home_team", "away_team", "commence_time"]):
#             continue
#
#         bookmakers = []
#
#         for bookmaker in match.get("bookmakers", []):
#             if bookmaker["title"].lower() in selected_bookmakers:  # Match bookmaker keys (case insensitive)
#                 h2h_markets = [
#                     H2HMarket(
#                         key=market["key"],
#                         outcomes=[
#                             Outcome(name=outcome["name"], price=outcome["price"])
#                             for outcome in market.get("outcomes", [])
#                         ],
#                     )
#                     for market in bookmaker.get("markets", [])
#                     if market["key"] == "h2h"
#                 ]
#
#                 if h2h_markets:
#                     bookmakers.append(Bookmaker(name=bookmaker["key"], markets=h2h_markets))
#
#         if bookmakers:
#             match_data_list.append(
#                 MatchData(
#                     home_team=match["home_team"],
#                     away_team=match["away_team"],
#                     commence_time=match["commence_time"],
#                     bookmakers=bookmakers,
#                 )
#             )
#
#     return match_data_list
#
#
# def filter_matches_by_hour(matches):
#     current_time = datetime.utcnow() + timedelta(hours=1)  # UTC+1 time
#     cutoff_time = current_time + timedelta(hours=1)
#
#     filtered_matches = [
#         match for match in matches if datetime.fromisoformat(match["commence_time"][:-1]) <= cutoff_time
#     ]
#     return filtered_matches
#
#
# def filter_matches_by_day(matches):
#     current_time = datetime.utcnow() + timedelta(hours=1)  # UTC+1 time
#     start_of_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
#     end_of_day = start_of_day + timedelta(days=1)
#
#     filtered_matches = [
#         match for match in matches if start_of_day <= datetime.fromisoformat(match["commence_time"][:-1]) < end_of_day
#     ]
#     return filtered_matches
#
#
# # Store data
# def store_data(bookmaker_data):
#     with open("odds_data.json", "w") as file:
#         json.dump(bookmaker_data, file, indent=4)
#
#
# # calculate no vig pinnacle odds
# import json
#
#
# def remove_vig(bookmaker_data):
#     bookmaker_data = [json.loads(match) for match in bookmaker_data]
#
#     for match in bookmaker_data:
#         pinnacle_markets = next(
#             (bookmaker["markets"] for bookmaker in match["bookmakers"] if bookmaker["name"] == "pinnacle"),
#             None
#         )
#
#         if pinnacle_markets:
#             for market in pinnacle_markets:
#                 if market.get("outcomes"):
#                     outcomes = market["outcomes"]
#
#                     odds = [outcome["price"] for outcome in outcomes]
#                     implied_probs = shin.calculate_implied_probabilities(odds)
#
#                     for outcome, prob in zip(outcomes, implied_probs):
#                         outcome["no_vig_price"] = round(1 / prob, 2)
#
#     return bookmaker_data
#
#
# # calculate EV
# def calculate_ev(odds: float, fair_odds: float) -> float:
#     if fair_odds <= 0:
#         return 0
#     implied_prob = 1 / fair_odds
#     stake = 100  # Assume a default stake for EV calculation
#     payout = stake * odds
#     ev = (implied_prob * payout) - ((1 - implied_prob) * stake)
#     return ev
#
#
# # Main function
# async def main(name, all_matches, bookmakers):
#     matches = await fetch_api_data(name)
#
#     if all_matches is False:
#         filtered_matches = filter_matches_by_hour(matches)
#         h2h_filtered_matches = extract_bookmaker_data(filtered_matches, bookmakers)
#         serialized_filtered_matches = [match.model_dump_json() for match in h2h_filtered_matches]
#         store_data(serialized_filtered_matches)
#         no_vig_data = remove_vig(serialized_filtered_matches)
#         return no_vig_data
#     else:
#         filtered_matches = filter_matches_by_day(matches)
#         h2h_filtered_matches = extract_bookmaker_data(filtered_matches, bookmakers)
#         print(h2h_filtered_matches)
#         serialized_filtered_matches = [match.model_dump_json() for match in h2h_filtered_matches]
#         store_data(serialized_filtered_matches)
#         no_vig_data = remove_vig(serialized_filtered_matches)
#
#         return no_vig_data
#
#
# async def fetch_odds_for_match(competition_name, match_id):
#     # Fetch new odds data
#     matches = await fetch_api_data(competition_name)
#     match = next((m for m in matches if m["id"] == match_id), None)
#     if match:
#         h2h_filtered_match = extract_bookmaker_data([match])
#         no_vig_data = remove_vig([h2h_filtered_match[0].model_dump_json()])
#         return no_vig_data
#     return {}

_FLASHSCORE_ID_RE = re.compile(r'^[A-Za-z0-9]{8,}$')


class TrackRequest(BaseModel):
    home_team: Optional[str] = None
    match_id: Optional[str] = None
    sport_key: Optional[str] = None  # e.g. "soccer_epl" — helps Odds API event lookup

    @field_validator("match_id", mode="before")
    @classmethod
    def sanitize_match_id(cls, v):
        """Treat empty / Swagger-default / non-FlashScore-format values as absent."""
        if not v or not _FLASHSCORE_ID_RE.match(str(v).strip()):
            return None
        return str(v).strip()

    def validate_inputs(self):
        """Raises ValueError with a clear message if inputs are unusable."""
        if not self.home_team and not self.match_id:
            raise ValueError("Provide either 'home_team' or 'match_id'.")


@router.post("/track")
async def track_match(body: TrackRequest, redis_client=Depends(get_redis)):
    logger.info("=== /odds/track called with body: %s", body)

    try:
        body.validate_inputs()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    loop = asyncio.get_event_loop()
    scraper = FlashScoreScraper(persist_outputs=False)
    match_id = body.match_id

    # ------------------------------------------------------------------
    # Step 1 — Resolve match_id from team name if not provided directly
    # ------------------------------------------------------------------
    if not match_id:
        logger.info("Step 1: Resolving match_id from home_team='%s'", body.home_team)
        try:
            match_id = await loop.run_in_executor(
                None, scraper.get_team_id_by_name, body.home_team
            )
            logger.info("Step 1 complete: resolved match_id='%s'", match_id)
        except Exception as e:
            logger.error("Step 1 FAILED: %s", e, exc_info=True)
            raise HTTPException(status_code=404, detail=f"Could not resolve team name: {e}")

        if not match_id:
            raise HTTPException(
                status_code=404,
                detail=f"No upcoming match found for team '{body.home_team}'."
            )
    else:
        logger.info("Step 1: Using provided match_id='%s' directly.", match_id)

    # ------------------------------------------------------------------
    # Step 2 — Already tracked?
    # ------------------------------------------------------------------
    if await is_already_tracked(redis_client, match_id):
        meta = await get_match_meta(redis_client, match_id)
        logger.info("Step 2: Already tracked, returning early.")
        return {"match_id": match_id, "status": "already_tracked", "meta": meta}

    # ------------------------------------------------------------------
    # Step 3 — Scrape match info
    # ------------------------------------------------------------------
    logger.info("Step 3: Fetching match info for match_id='%s'", match_id)
    try:
        match_info = await loop.run_in_executor(None, scraper.get_match_info, match_id)
        logger.info("Step 3 complete: match_info=%s", match_info)
    except Exception as e:
        logger.error("Step 3 FAILED: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not fetch match info: {e}")

    # Reject if match info came back empty — means the match_id is invalid
    if match_info.get("home_team") == "unknown" and match_info.get("start_time") is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"match_id '{match_id}' returned no data from FlashScore. "
                "Check the ID is correct and the match exists."
            )
        )

    # ------------------------------------------------------------------
    # Step 4 — Scrape initial odds snapshot
    # ------------------------------------------------------------------
    logger.info("Step 4: Fetching initial odds for match_id='%s'", match_id)
    try:
        initial_odds = await loop.run_in_executor(
            None,
            scraper.get_odds_by_match_id,  # ← uses the new direct method
            match_id
        )
        logger.info("Step 4 complete: initial_odds=%s", initial_odds)
    except Exception as e:
        logger.warning("Step 4 WARNING: %s — continuing without initial odds.", e)
        initial_odds = {}

    # ------------------------------------------------------------------
    # Step 5 — Register in Redis + resolve Odds API event
    # ------------------------------------------------------------------
    home_team = match_info.get("home_team", body.home_team or "unknown")
    away_team = match_info.get("away_team", "unknown")

    meta = {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "start_time": match_info.get("start_time"),
        "start_time_raw": match_info.get("start_time_raw"),
        "status": "tracking",
        "tracked_since": datetime.now(timezone.utc).isoformat(),
    }

    # Try to resolve matching Odds API event (optional — needs ODDS_API_KEY)
    odds_api_key = os.getenv("ODDS_API_KEY")
    if odds_api_key:
        try:
            from app.services.odds_api.odds_api_client import find_event
            result = await loop.run_in_executor(
                None, find_event, odds_api_key, home_team, away_team, body.sport_key,
            )
            if result:
                meta["odds_api_event_id"] = result[0]
                meta["odds_api_sport_key"] = result[1]
                logger.info("Step 5: Mapped to Odds API event %s (%s)", result[0], result[1])
            else:
                logger.info("Step 5: No matching Odds API event found.")
        except Exception as e:
            logger.warning("Step 5: Odds API lookup failed: %s", e)

    await register_match(redis_client, match_id, meta)
    logger.info("Step 5 complete: meta stored.")

    # ------------------------------------------------------------------
    # Step 6 — Store initial odds snapshot (with sharp odds if available)
    # ------------------------------------------------------------------
    initial_sharp_odds = None
    if initial_odds.get("home") is not None:
        if odds_api_key and meta.get("odds_api_event_id"):
            try:
                from app.services.odds_api.odds_api_client import fetch_sharp_odds
                initial_sharp_odds = await loop.run_in_executor(
                    None, fetch_sharp_odds,
                    odds_api_key, meta["odds_api_sport_key"],
                    meta["odds_api_event_id"], home_team, away_team,
                )
            except Exception as e:
                logger.warning("Step 6: Sharp odds fetch failed: %s", e)

        await store_odds_snapshot(
            redis_client, match_id, initial_odds,
            sharp_odds=initial_sharp_odds or None,
        )
        logger.info("Step 6: Initial snapshot stored.")
    else:
        logger.info("Step 6: No valid initial odds yet.")

    # ------------------------------------------------------------------
    # Step 7 — Start scheduler
    # ------------------------------------------------------------------
    start_tracking_job(match_id, scraper, redis_client)
    logger.info("Step 7: Scheduler job registered.")

    return {
        "match_id": match_id,
        "status": "tracking_started",
        "meta": meta,
        "message": f"Tracking odds every {SCRAPE_INTERVAL_SECONDS}s until 2min before kickoff.",
    }

@router.get("/tracked")
async def list_tracked_matches(redis_client=Depends(get_redis)):
    """Return all currently tracked match IDs with their metadata."""
    match_ids = await get_all_tracked_ids(redis_client)

    if not match_ids:
        return {"tracked_matches": [], "count": 0}

    matches = []
    for match_id in match_ids:
        meta = await get_match_meta(redis_client, match_id)
        matches.append({
            "match_id": match_id,
            "meta": meta,
            # Convenience: is the scheduler job still active?
            "job_active": scheduler.get_job(f"odds_scrape_{match_id}") is not None,
        })

    return {"tracked_matches": matches, "count": len(matches)}


@router.get("/history/{match_id}")
async def stream_odds_history(
        match_id: str,
        redis_client=Depends(get_redis),
        poll_interval: int = Query(default=10, ge=5, le=60,
                                   description="How often (seconds) to check for new snapshots"),
):
    """
    Stream odds history for a tracked match as Server-Sent Events.

    - Immediately sends all existing snapshots on connect.
    - Then polls Redis for new snapshots and pushes them as they arrive.
    - Sends keepalive every poll_interval seconds when no new data.
    - Closes automatically when tracking stops (match completed/removed).
    """
    meta = await get_match_meta(redis_client, match_id)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"Match {match_id} is not tracked. Start tracking via POST /odds/track."
        )

    async def event_stream():
        # --- 1. Send match metadata as first event ---
        yield f"data: {json.dumps({'type': 'meta', 'data': meta})}\n\n"

        # --- 2. Replay full existing history ---
        history = await get_odds_history(redis_client, match_id)
        last_sent_count = len(history)

        for snapshot in history:
            yield f"data: {json.dumps({'type': 'snapshot', 'data': snapshot})}\n\n"

        yield f"data: {json.dumps({'type': 'history_complete', 'count': last_sent_count})}\n\n"

        # --- 3. Poll for new snapshots ---
        import asyncio
        while True:
            await asyncio.sleep(poll_interval)

            current_meta = await get_match_meta(redis_client, match_id)

            # Tracking ended — send final event and close
            if not current_meta or current_meta.get("status") == "completed":
                yield f"data: {json.dumps({'type': 'tracking_ended', 'match_id': match_id})}\n\n"
                break

            history = await get_odds_history(redis_client, match_id)
            new_snapshots = history[last_sent_count:]

            if new_snapshots:
                for snapshot in new_snapshots:
                    yield f"data: {json.dumps({'type': 'snapshot', 'data': snapshot})}\n\n"
                last_sent_count = len(history)
            else:
                # Keepalive so the connection doesn't time out
                yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering for SSE
        }
    )


@router.get("/history/{match_id}/summary")
async def get_match_history_summary(match_id: str, redis_client=Depends(get_redis)):
    # 1. Try Redis first (fast, real-time data)
    meta = await get_match_meta(redis_client, match_id)
    history = await get_odds_history(redis_client, match_id)

    # 2. Fallback to PostgreSQL when Redis data is gone
    if not history:
        logger.info("Redis empty for %s — falling back to PostgreSQL.", match_id)
        session = SessionLocal()
        try:
            if not meta:
                meta = get_match_meta_from_db(session, match_id)
            history = db_get_snapshots(session, match_id)
        finally:
            session.close()

    if not meta and not history:
        return {"match_id": match_id, "history": [], "message": "No snapshots recorded yet."}

    if not meta:
        meta = {}

    processed_history = []

    for i, snapshot in enumerate(history):
        current_time = datetime.fromisoformat(snapshot["timestamp"])

        # Calculate interval since the previous snapshot
        if i > 0:
            prev_time = datetime.fromisoformat(history[i - 1]["timestamp"])
            interval_seconds = (current_time - prev_time).total_seconds()
        else:
            interval_seconds = 0  # First entry has no previous interval

        # Add the interval data to the snapshot object
        snapshot_with_interval = {
            **snapshot,
            "seconds_since_last": interval_seconds,
            "display_interval": f"{int(interval_seconds)}s" if i > 0 else "Initial"
        }
        processed_history.append(snapshot_with_interval)

    return {
        "match": f"{meta.get('home_team', 'unknown')} vs {meta.get('away_team', 'unknown')}",
        "start_time": meta.get("start_time"),
        "total_snapshots": len(processed_history),
        "history": processed_history
    }

# odds.py — add this route after /tracked

@router.delete("/untrack/{match_id}")
async def untrack_match(match_id: str, redis_client=Depends(get_redis)):
    """
    Stop tracking a match and remove it from the scheduler.
    History is preserved in Redis — only active tracking stops.
    """
    meta = await get_match_meta(redis_client, match_id)

    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"Match '{match_id}' is not tracked."
        )

    # Stop the scheduler job
    stop_tracking_job(match_id)

    # Remove from Redis tracking index + mark as completed
    await unregister_match(redis_client, match_id)

    logger.info("Manually untracked match %s", match_id)

    return {
        "match_id": match_id,
        "status": "untracked",
        "message": f"Match {match_id} removed from tracking. History preserved.",
    }


@router.delete("/untrack/all")
async def untrack_all_matches(redis_client=Depends(get_redis)):
    """
    Stop tracking ALL matches at once. Useful for cleanup.
    History is preserved — only active tracking stops.
    """
    match_ids = await get_all_tracked_ids(redis_client)

    if not match_ids:
        return {"status": "nothing_to_untrack", "count": 0}

    removed = []
    failed = []

    for match_id in match_ids:
        try:
            stop_tracking_job(match_id)
            await unregister_match(redis_client, match_id)
            removed.append(match_id)
            logger.info("Untracked match %s", match_id)
        except Exception as e:
            logger.error("Failed to untrack match %s: %s", match_id, e)
            failed.append({"match_id": match_id, "error": str(e)})

    return {
        "status": "done",
        "removed": removed,
        "failed": failed,
        "count_removed": len(removed),
    }

# @router.get("/{home_team}")
# async def get_odds(home_team: str):
#     try:
#         scraper = FlashScoreScraper(persist_outputs=False)
#         odds_data = scraper.get_odds_by_match_name(home_team)
#         if odds_data:
#             return odds_data
#         else:
#             raise HTTPException(status_code=404, detail=f"No odds found for team {home_team}")
#     except Exception as e:
#         logging.error(f"ERROR: Failed to fetch odds for {home_team}: {type(e).__name__} - {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to fetch odds: {str(e)}")
