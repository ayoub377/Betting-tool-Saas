"""
Persistence layer for odds snapshots and match metadata.
Writes to PostgreSQL (or any SQLAlchemy-supported DB) for long-term storage.
"""
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.odds_models import TrackedMatch, OddsSnapshot

logger = logging.getLogger(__name__)


def persist_match(session: Session, match_id: str, meta: dict):
    """Insert or ignore match metadata. Idempotent — skips if already exists."""
    existing = session.query(TrackedMatch).filter_by(match_id=match_id).first()
    if existing:
        return
    row = TrackedMatch(
        match_id=match_id,
        home_team=meta.get("home_team"),
        away_team=meta.get("away_team"),
        start_time=meta.get("start_time"),
        start_time_raw=meta.get("start_time_raw"),
        status=meta.get("status", "tracking"),
        tracked_since=meta.get("tracked_since"),
        odds_api_event_id=meta.get("odds_api_event_id"),
        odds_api_sport_key=meta.get("odds_api_sport_key"),
    )
    session.add(row)
    session.commit()
    logger.info("Persisted match %s to database.", match_id)


def persist_snapshot(session: Session, match_id: str, snapshot: dict):
    """Append a single odds snapshot row."""
    sharp_odds_raw = snapshot.get("sharp_odds")
    sharp_odds_json = json.dumps(sharp_odds_raw) if sharp_odds_raw else None

    row = OddsSnapshot(
        match_id=match_id,
        timestamp=snapshot.get("timestamp"),
        home=snapshot.get("home"),
        draw=snapshot.get("draw"),
        away=snapshot.get("away"),
        bookmaker=snapshot.get("bookmaker"),
        sharp_odds=sharp_odds_json,
    )
    session.add(row)
    session.commit()
    logger.debug("Persisted snapshot for match %s.", match_id)


def update_match_status(session: Session, match_id: str, status: str):
    """Update the status field of a tracked match."""
    row = session.query(TrackedMatch).filter_by(match_id=match_id).first()
    if row:
        row.status = status
        session.commit()
        logger.info("Updated match %s status to '%s'.", match_id, status)


def get_match_snapshots(session: Session, match_id: str) -> list[dict]:
    """Return all snapshots for a match, ordered by insertion order."""
    rows = (
        session.query(OddsSnapshot)
        .filter_by(match_id=match_id)
        .order_by(OddsSnapshot.id)
        .all()
    )
    return [
        {
            "timestamp": r.timestamp,
            "home": r.home,
            "draw": r.draw,
            "away": r.away,
            "bookmaker": r.bookmaker,
            "sharp_odds": json.loads(r.sharp_odds) if r.sharp_odds else None,
        }
        for r in rows
    ]


def get_match_meta_from_db(session: Session, match_id: str) -> Optional[dict]:
    """Return match metadata as a dict, or None if not found."""
    row = session.query(TrackedMatch).filter_by(match_id=match_id).first()
    if not row:
        return None
    return {
        "match_id": row.match_id,
        "home_team": row.home_team,
        "away_team": row.away_team,
        "start_time": row.start_time,
        "start_time_raw": row.start_time_raw,
        "status": row.status,
        "tracked_since": row.tracked_since,
        "odds_api_event_id": row.odds_api_event_id,
        "odds_api_sport_key": row.odds_api_sport_key,
    }
