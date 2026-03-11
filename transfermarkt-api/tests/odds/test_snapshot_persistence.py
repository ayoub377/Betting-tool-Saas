"""
Tests for odds snapshot persistence to PostgreSQL.
Uses SQLite in-memory so no external DB is needed.
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.odds_models import Base, TrackedMatch, OddsSnapshot
from app.services.odds_tracker.snapshot_persistence import (
    persist_snapshot,
    persist_match,
    update_match_status,
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


# ── persist_match ────────────────────────────────────────────────

class TestPersistMatch:
    def test_persist_new_match(self, db_session):
        meta = {
            "match_id": "ABC12345",
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "start_time": "2026-03-10T21:00:00+00:00",
            "start_time_raw": "10.03.2026 21:00",
            "status": "tracking",
            "tracked_since": "2026-03-10T14:00:00+00:00",
        }
        persist_match(db_session, "ABC12345", meta)

        row = db_session.query(TrackedMatch).filter_by(match_id="ABC12345").first()
        assert row is not None
        assert row.home_team == "Manchester United"
        assert row.away_team == "Liverpool"
        assert row.status == "tracking"
        assert row.start_time == "2026-03-10T21:00:00+00:00"

    def test_persist_match_is_idempotent(self, db_session):
        """Calling persist_match twice with the same match_id should not duplicate."""
        meta = {
            "match_id": "ABC12345",
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "start_time": "2026-03-10T21:00:00+00:00",
            "status": "tracking",
            "tracked_since": "2026-03-10T14:00:00+00:00",
        }
        persist_match(db_session, "ABC12345", meta)
        persist_match(db_session, "ABC12345", meta)

        count = db_session.query(TrackedMatch).filter_by(match_id="ABC12345").count()
        assert count == 1

    def test_persist_multiple_matches(self, db_session):
        for mid in ("MATCH001", "MATCH002", "MATCH003"):
            persist_match(db_session, mid, {
                "match_id": mid,
                "home_team": f"Home {mid}",
                "away_team": f"Away {mid}",
                "status": "tracking",
            })
        assert db_session.query(TrackedMatch).count() == 3


# ── persist_snapshot ─────────────────────────────────────────────

class TestPersistSnapshot:
    def test_persist_single_snapshot(self, db_session):
        snapshot = {
            "timestamp": "2026-03-10T14:30:00+00:00",
            "home": 2.45,
            "draw": 3.10,
            "away": 2.95,
            "bookmaker": "Pinnacle",
        }
        persist_snapshot(db_session, "ABC12345", snapshot)

        row = db_session.query(OddsSnapshot).filter_by(match_id="ABC12345").first()
        assert row is not None
        assert row.home == 2.45
        assert row.draw == 3.10
        assert row.away == 2.95
        assert row.bookmaker == "Pinnacle"

    def test_persist_multiple_snapshots_ordered(self, db_session):
        """Snapshots should be retrievable in insertion order."""
        for i in range(5):
            persist_snapshot(db_session, "ABC12345", {
                "timestamp": f"2026-03-10T14:{30 + i}:00+00:00",
                "home": 2.40 + i * 0.01,
                "draw": 3.10,
                "away": 2.95,
                "bookmaker": "Pinnacle",
            })
        rows = (
            db_session.query(OddsSnapshot)
            .filter_by(match_id="ABC12345")
            .order_by(OddsSnapshot.id)
            .all()
        )
        assert len(rows) == 5
        assert rows[0].home == pytest.approx(2.40)
        assert rows[4].home == pytest.approx(2.44)

    def test_snapshots_isolated_per_match(self, db_session):
        """Snapshots for different matches should not interfere."""
        persist_snapshot(db_session, "MATCH_A", {
            "timestamp": "2026-03-10T14:00:00+00:00",
            "home": 1.50, "draw": 3.00, "away": 5.00, "bookmaker": "Bet365",
        })
        persist_snapshot(db_session, "MATCH_B", {
            "timestamp": "2026-03-10T14:00:00+00:00",
            "home": 2.00, "draw": 3.20, "away": 3.50, "bookmaker": "Pinnacle",
        })

        a_count = db_session.query(OddsSnapshot).filter_by(match_id="MATCH_A").count()
        b_count = db_session.query(OddsSnapshot).filter_by(match_id="MATCH_B").count()
        assert a_count == 1
        assert b_count == 1


# ── update_match_status ──────────────────────────────────────────

class TestUpdateMatchStatus:
    def test_update_status_to_completed(self, db_session):
        persist_match(db_session, "ABC12345", {
            "match_id": "ABC12345",
            "home_team": "Team A",
            "away_team": "Team B",
            "status": "tracking",
        })
        update_match_status(db_session, "ABC12345", "completed")

        row = db_session.query(TrackedMatch).filter_by(match_id="ABC12345").first()
        assert row.status == "completed"

    def test_update_nonexistent_match_is_noop(self, db_session):
        """Should not raise when match doesn't exist."""
        update_match_status(db_session, "GHOST", "completed")
        assert db_session.query(TrackedMatch).filter_by(match_id="GHOST").first() is None


# ── get_match_snapshots ──────────────────────────────────────────

class TestGetMatchSnapshots:
    def test_returns_empty_for_unknown_match(self, db_session):
        result = get_match_snapshots(db_session, "UNKNOWN")
        assert result == []

    def test_returns_snapshots_as_dicts(self, db_session):
        for i in range(3):
            persist_snapshot(db_session, "ABC12345", {
                "timestamp": f"2026-03-10T14:{30 + i}:00+00:00",
                "home": 2.40 + i * 0.05,
                "draw": 3.10,
                "away": 2.95,
                "bookmaker": "Pinnacle",
            })

        result = get_match_snapshots(db_session, "ABC12345")
        assert len(result) == 3
        # Should be dicts, not ORM objects
        assert isinstance(result[0], dict)
        assert "timestamp" in result[0]
        assert "home" in result[0]
        assert "draw" in result[0]
        assert "away" in result[0]
        assert "bookmaker" in result[0]

    def test_snapshots_in_chronological_order(self, db_session):
        timestamps = [
            "2026-03-10T14:50:00+00:00",
            "2026-03-10T14:30:00+00:00",
            "2026-03-10T14:40:00+00:00",
        ]
        for ts in timestamps:
            persist_snapshot(db_session, "ABC12345", {
                "timestamp": ts, "home": 2.0, "draw": 3.0, "away": 4.0, "bookmaker": "X",
            })

        result = get_match_snapshots(db_session, "ABC12345")
        # Should be ordered by insertion order (id)
        assert result[0]["timestamp"] == timestamps[0]
        assert result[1]["timestamp"] == timestamps[1]
        assert result[2]["timestamp"] == timestamps[2]


# ── get_match_meta_from_db ───────────────────────────────────────

class TestGetMatchMetaFromDb:
    def test_returns_none_for_unknown_match(self, db_session):
        result = get_match_meta_from_db(db_session, "UNKNOWN")
        assert result is None

    def test_returns_meta_dict(self, db_session):
        persist_match(db_session, "ABC12345", {
            "match_id": "ABC12345",
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "start_time": "2026-03-10T21:00:00+00:00",
            "start_time_raw": "10.03.2026 21:00",
            "status": "tracking",
            "tracked_since": "2026-03-10T14:00:00+00:00",
        })
        result = get_match_meta_from_db(db_session, "ABC12345")
        assert result is not None
        assert result["match_id"] == "ABC12345"
        assert result["home_team"] == "Manchester United"
        assert result["away_team"] == "Liverpool"
        assert result["status"] == "tracking"
        assert result["start_time"] == "2026-03-10T21:00:00+00:00"


# ── Full flow: persist + retrieve ────────────────────────────────

class TestFullFlow:
    def test_persist_match_then_snapshots_then_retrieve(self, db_session):
        """Simulates the real workflow: register match, store snapshots, retrieve."""
        meta = {
            "match_id": "FULLFLOW1",
            "home_team": "Barcelona",
            "away_team": "Real Madrid",
            "start_time": "2026-03-10T20:00:00+00:00",
            "status": "tracking",
            "tracked_since": "2026-03-10T12:00:00+00:00",
        }
        persist_match(db_session, "FULLFLOW1", meta)

        # Simulate 3 scrape cycles
        for i in range(3):
            persist_snapshot(db_session, "FULLFLOW1", {
                "timestamp": f"2026-03-10T{12 + i}:00:00+00:00",
                "home": 1.80 + i * 0.05,
                "draw": 3.40,
                "away": 4.20 - i * 0.10,
                "bookmaker": "Pinnacle",
            })

        # Mark completed
        update_match_status(db_session, "FULLFLOW1", "completed")

        # Retrieve (simulates Redis-gone scenario)
        db_meta = get_match_meta_from_db(db_session, "FULLFLOW1")
        db_history = get_match_snapshots(db_session, "FULLFLOW1")

        assert db_meta["status"] == "completed"
        assert db_meta["home_team"] == "Barcelona"
        assert len(db_history) == 3
        assert db_history[0]["home"] == pytest.approx(1.80)
        assert db_history[2]["home"] == pytest.approx(1.90)

    def test_retrieve_after_status_change(self, db_session):
        """After unregistering, meta should reflect completed status."""
        persist_match(db_session, "STATUS1", {
            "match_id": "STATUS1",
            "home_team": "A",
            "away_team": "B",
            "status": "tracking",
        })

        meta = get_match_meta_from_db(db_session, "STATUS1")
        assert meta["status"] == "tracking"

        update_match_status(db_session, "STATUS1", "completed")
        meta = get_match_meta_from_db(db_session, "STATUS1")
        assert meta["status"] == "completed"
