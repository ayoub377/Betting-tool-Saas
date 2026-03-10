"""
Tests for enriched snapshots that include sharp bookmaker odds.
Verifies backward compatibility and the new sharp_odds field.
"""
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.odds_models import Base, TrackedMatch, OddsSnapshot
from app.services.odds_tracker.snapshot_persistence import (
    persist_snapshot,
    persist_match,
    get_match_snapshots,
    get_match_meta_from_db,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestSharpOddsInSnapshot:
    def test_persist_snapshot_with_sharp_odds(self, db_session):
        """Snapshot with sharp_odds should round-trip through the DB."""
        sharp = {
            "pinnacle": {"home": 2.50, "draw": 3.20, "away": 2.80},
            "betfair_ex_eu": {"home": 2.55, "draw": 3.15, "away": 2.85},
        }
        persist_snapshot(db_session, "SHARP1", {
            "timestamp": "2026-03-10T14:00:00+00:00",
            "home": 2.45,
            "draw": 3.10,
            "away": 2.95,
            "bookmaker": "Bet365",
            "sharp_odds": sharp,
        })

        rows = get_match_snapshots(db_session, "SHARP1")
        assert len(rows) == 1
        assert rows[0]["home"] == pytest.approx(2.45)
        assert rows[0]["sharp_odds"] is not None
        assert rows[0]["sharp_odds"]["pinnacle"]["home"] == pytest.approx(2.50)
        assert rows[0]["sharp_odds"]["betfair_ex_eu"]["away"] == pytest.approx(2.85)

    def test_persist_snapshot_without_sharp_odds_backward_compat(self, db_session):
        """Old-style snapshot (no sharp_odds) should still work fine."""
        persist_snapshot(db_session, "LEGACY1", {
            "timestamp": "2026-03-10T14:00:00+00:00",
            "home": 2.45,
            "draw": 3.10,
            "away": 2.95,
            "bookmaker": "Bet365",
        })

        rows = get_match_snapshots(db_session, "LEGACY1")
        assert len(rows) == 1
        assert rows[0]["home"] == pytest.approx(2.45)
        assert rows[0]["sharp_odds"] is None

    def test_mixed_snapshots_some_with_sharp(self, db_session):
        """Some snapshots have sharp_odds, others don't."""
        persist_snapshot(db_session, "MIX1", {
            "timestamp": "2026-03-10T14:00:00+00:00",
            "home": 2.00, "draw": 3.00, "away": 4.00, "bookmaker": "X",
        })
        persist_snapshot(db_session, "MIX1", {
            "timestamp": "2026-03-10T14:20:00+00:00",
            "home": 2.10, "draw": 3.00, "away": 3.90, "bookmaker": "X",
            "sharp_odds": {"pinnacle": {"home": 2.15, "draw": 3.10, "away": 3.80}},
        })

        rows = get_match_snapshots(db_session, "MIX1")
        assert len(rows) == 2
        assert rows[0]["sharp_odds"] is None
        assert rows[1]["sharp_odds"]["pinnacle"]["home"] == pytest.approx(2.15)


class TestTrackedMatchWithOddsApiFields:
    def test_persist_match_with_odds_api_event_id(self, db_session):
        """Match metadata should store the Odds API event mapping."""
        persist_match(db_session, "MAPPED1", {
            "match_id": "MAPPED1",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "status": "tracking",
            "odds_api_event_id": "event_002",
            "odds_api_sport_key": "soccer_epl",
        })

        meta = get_match_meta_from_db(db_session, "MAPPED1")
        assert meta["odds_api_event_id"] == "event_002"
        assert meta["odds_api_sport_key"] == "soccer_epl"

    def test_persist_match_without_odds_api_fields(self, db_session):
        """Existing matches without Odds API fields still work."""
        persist_match(db_session, "NOMATCH1", {
            "match_id": "NOMATCH1",
            "home_team": "Team A",
            "away_team": "Team B",
            "status": "tracking",
        })

        meta = get_match_meta_from_db(db_session, "NOMATCH1")
        assert meta["odds_api_event_id"] is None
        assert meta["odds_api_sport_key"] is None


class TestFullFlowWithSharpOdds:
    def test_full_tracking_lifecycle(self, db_session):
        """Simulate: register → snapshots with sharp → complete → retrieve."""
        persist_match(db_session, "FULL_SHARP", {
            "match_id": "FULL_SHARP",
            "home_team": "Barcelona",
            "away_team": "Real Madrid",
            "status": "tracking",
            "odds_api_event_id": "ev_999",
            "odds_api_sport_key": "soccer_spain_la_liga",
        })

        for i in range(3):
            sharp = {
                "pinnacle": {"home": 1.80 + i * 0.05, "draw": 3.40, "away": 4.20 - i * 0.10},
            } if i > 0 else None  # first snapshot has no sharp odds

            snapshot = {
                "timestamp": f"2026-03-10T{12 + i}:00:00+00:00",
                "home": 1.75 + i * 0.05,
                "draw": 3.30,
                "away": 4.30 - i * 0.10,
                "bookmaker": "Bet365",
            }
            if sharp:
                snapshot["sharp_odds"] = sharp

            persist_snapshot(db_session, "FULL_SHARP", snapshot)

        history = get_match_snapshots(db_session, "FULL_SHARP")
        meta = get_match_meta_from_db(db_session, "FULL_SHARP")

        assert len(history) == 3
        assert history[0]["sharp_odds"] is None
        assert history[1]["sharp_odds"]["pinnacle"]["home"] == pytest.approx(1.85)
        assert history[2]["sharp_odds"]["pinnacle"]["away"] == pytest.approx(4.00)
        assert meta["odds_api_event_id"] == "ev_999"
        assert meta["odds_api_sport_key"] == "soccer_spain_la_liga"
