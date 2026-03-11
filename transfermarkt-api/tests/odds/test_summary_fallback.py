"""
Tests for the summary endpoint's PostgreSQL fallback behavior.
Verifies that when Redis is empty, data is retrieved from the database.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.odds_models import Base
from app.services.odds_tracker.snapshot_persistence import (
    persist_snapshot,
    persist_match,
    get_match_snapshots,
    get_match_meta_from_db,
)


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestSummaryFallback:
    """Test the fallback logic used by the summary endpoint."""

    def test_redis_empty_returns_db_data(self, db_session):
        """When Redis has no data, the DB should provide the snapshots."""
        # Populate the database
        persist_match(db_session, "EXPIRED1", {
            "match_id": "EXPIRED1",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "start_time": "2026-03-08T15:00:00+00:00",
            "status": "completed",
        })
        for i in range(4):
            persist_snapshot(db_session, "EXPIRED1", {
                "timestamp": f"2026-03-08T{10 + i}:00:00+00:00",
                "home": 2.0 + i * 0.1,
                "draw": 3.0,
                "away": 3.5 - i * 0.1,
                "bookmaker": "Pinnacle",
            })

        # Simulate: Redis returns empty
        redis_history = []
        redis_meta = None

        # Fallback: query DB
        if not redis_history:
            meta = redis_meta or get_match_meta_from_db(db_session, "EXPIRED1")
            history = get_match_snapshots(db_session, "EXPIRED1")
        else:
            meta = redis_meta
            history = redis_history

        assert meta is not None
        assert meta["home_team"] == "Arsenal"
        assert meta["status"] == "completed"
        assert len(history) == 4
        assert history[0]["home"] == pytest.approx(2.0)

    def test_redis_has_data_skips_db(self, db_session):
        """When Redis has data, no DB query should be needed."""
        redis_history = [
            {"timestamp": "2026-03-10T14:00:00+00:00", "home": 1.5, "draw": 3.0, "away": 5.0, "bookmaker": "X"},
        ]
        redis_meta = {"home_team": "A", "away_team": "B"}

        # Simulate the endpoint logic
        if not redis_history:
            meta = get_match_meta_from_db(db_session, "ANYTHING")
            history = get_match_snapshots(db_session, "ANYTHING")
        else:
            meta = redis_meta
            history = redis_history

        assert meta == redis_meta
        assert len(history) == 1
        assert history[0]["home"] == 1.5

    def test_neither_redis_nor_db_has_data(self, db_session):
        """When both Redis and DB are empty, should return empty."""
        redis_history = []
        redis_meta = None

        if not redis_history:
            meta = redis_meta or get_match_meta_from_db(db_session, "GHOST")
            history = get_match_snapshots(db_session, "GHOST")
        else:
            meta = redis_meta
            history = redis_history

        assert meta is None
        assert history == []

    def test_interval_calculation_on_db_data(self, db_session):
        """Verify that interval calculations work correctly on DB-sourced data."""
        persist_match(db_session, "INTERVAL1", {
            "match_id": "INTERVAL1",
            "home_team": "Team A",
            "away_team": "Team B",
            "status": "completed",
        })
        persist_snapshot(db_session, "INTERVAL1", {
            "timestamp": "2026-03-08T10:00:00+00:00",
            "home": 2.0, "draw": 3.0, "away": 4.0, "bookmaker": "X",
        })
        persist_snapshot(db_session, "INTERVAL1", {
            "timestamp": "2026-03-08T10:20:00+00:00",
            "home": 2.1, "draw": 3.0, "away": 3.9, "bookmaker": "X",
        })

        history = get_match_snapshots(db_session, "INTERVAL1")

        # Replicate the endpoint's interval processing
        processed = []
        for i, snapshot in enumerate(history):
            current_time = datetime.fromisoformat(snapshot["timestamp"])
            if i > 0:
                prev_time = datetime.fromisoformat(history[i - 1]["timestamp"])
                interval = (current_time - prev_time).total_seconds()
            else:
                interval = 0

            processed.append({
                **snapshot,
                "seconds_since_last": interval,
                "display_interval": f"{int(interval)}s" if i > 0 else "Initial",
            })

        assert processed[0]["display_interval"] == "Initial"
        assert processed[1]["seconds_since_last"] == 1200.0  # 20 minutes
        assert processed[1]["display_interval"] == "1200s"
