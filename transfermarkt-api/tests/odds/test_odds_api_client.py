"""
Tests for the Odds API client service.
All HTTP calls are mocked — no real API key needed.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.odds_api.odds_api_client import (
    find_event,
    fetch_sharp_odds,
    extract_sharp_odds_from_event,
    SHARP_BOOKMAKERS,
    SOCCER_SPORT_KEYS,
)


# ── Sample API responses ─────────────────────────────────────────

SAMPLE_EVENTS_RESPONSE = [
    {
        "id": "event_001",
        "sport_key": "soccer_epl",
        "home_team": "Manchester United",
        "away_team": "Liverpool",
        "commence_time": "2026-03-10T20:00:00Z",
        "bookmakers": [],
    },
    {
        "id": "event_002",
        "sport_key": "soccer_epl",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "commence_time": "2026-03-10T17:30:00Z",
        "bookmakers": [],
    },
]

SAMPLE_EVENT_ODDS_RESPONSE = {
    "id": "event_001",
    "sport_key": "soccer_epl",
    "home_team": "Manchester United",
    "away_team": "Liverpool",
    "commence_time": "2026-03-10T20:00:00Z",
    "bookmakers": [
        {
            "key": "pinnacle",
            "title": "Pinnacle",
            "markets": [
                {
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Manchester United", "price": 2.50},
                        {"name": "Liverpool", "price": 2.80},
                        {"name": "Draw", "price": 3.40},
                    ],
                }
            ],
        },
        {
            "key": "betfair_ex_eu",
            "title": "Betfair Exchange",
            "markets": [
                {
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Manchester United", "price": 2.55},
                        {"name": "Liverpool", "price": 2.75},
                        {"name": "Draw", "price": 3.50},
                    ],
                }
            ],
        },
        {
            "key": "bet365",
            "title": "Bet365",
            "markets": [
                {
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Manchester United", "price": 2.40},
                        {"name": "Liverpool", "price": 2.90},
                        {"name": "Draw", "price": 3.30},
                    ],
                }
            ],
        },
    ],
}


# ── Constants ─────────────────────────────────────────────────────

class TestConstants:
    def test_sharp_bookmakers_includes_pinnacle(self):
        assert "pinnacle" in SHARP_BOOKMAKERS

    def test_sharp_bookmakers_includes_betfair(self):
        assert "betfair_ex_eu" in SHARP_BOOKMAKERS

    def test_sharp_bookmakers_includes_betonline(self):
        assert "betonlineag" in SHARP_BOOKMAKERS

    def test_soccer_sport_keys_not_empty(self):
        assert len(SOCCER_SPORT_KEYS) > 0

    def test_soccer_sport_keys_includes_epl(self):
        assert "soccer_epl" in SOCCER_SPORT_KEYS


# ── extract_sharp_odds_from_event ─────────────────────────────────

class TestExtractSharpOdds:
    def test_extracts_pinnacle_and_betfair(self):
        result = extract_sharp_odds_from_event(
            SAMPLE_EVENT_ODDS_RESPONSE,
            home_team="Manchester United",
            away_team="Liverpool",
        )
        assert "pinnacle" in result
        assert "betfair_ex_eu" in result
        # bet365 is NOT sharp — should be excluded
        assert "bet365" not in result

    def test_pinnacle_odds_correct(self):
        result = extract_sharp_odds_from_event(
            SAMPLE_EVENT_ODDS_RESPONSE,
            home_team="Manchester United",
            away_team="Liverpool",
        )
        pinnacle = result["pinnacle"]
        assert pinnacle["home"] == pytest.approx(2.50)
        assert pinnacle["away"] == pytest.approx(2.80)
        assert pinnacle["draw"] == pytest.approx(3.40)

    def test_betfair_odds_correct(self):
        result = extract_sharp_odds_from_event(
            SAMPLE_EVENT_ODDS_RESPONSE,
            home_team="Manchester United",
            away_team="Liverpool",
        )
        betfair = result["betfair_ex_eu"]
        assert betfair["home"] == pytest.approx(2.55)
        assert betfair["away"] == pytest.approx(2.75)
        assert betfair["draw"] == pytest.approx(3.50)

    def test_returns_empty_when_no_sharp_bookmakers(self):
        event_no_sharp = {
            "id": "event_001",
            "bookmakers": [
                {
                    "key": "bet365",
                    "title": "Bet365",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Team A", "price": 2.0},
                                {"name": "Team B", "price": 3.0},
                                {"name": "Draw", "price": 3.5},
                            ],
                        }
                    ],
                }
            ],
        }
        result = extract_sharp_odds_from_event(event_no_sharp, "Team A", "Team B")
        assert result == {}

    def test_returns_empty_when_no_bookmakers(self):
        event_empty = {"id": "event_001", "bookmakers": []}
        result = extract_sharp_odds_from_event(event_empty, "A", "B")
        assert result == {}

    def test_handles_missing_h2h_market(self):
        event = {
            "id": "event_001",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "title": "Pinnacle",
                    "markets": [
                        {
                            "key": "spreads",
                            "outcomes": [
                                {"name": "Team A", "price": 1.90},
                                {"name": "Team B", "price": 1.90},
                            ],
                        }
                    ],
                }
            ],
        }
        result = extract_sharp_odds_from_event(event, "Team A", "Team B")
        assert result == {}


# ── find_event ───────────────────────────────────────────────────

class TestFindEvent:
    @patch("app.services.odds_api.odds_api_client.httpx")
    def test_finds_exact_match(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_EVENTS_RESPONSE
        mock_httpx.get.return_value = mock_response

        result = find_event("fake_key", "Manchester United", "Liverpool", sport_key="soccer_epl")
        assert result is not None
        event_id, sport_key = result
        assert event_id == "event_001"
        assert sport_key == "soccer_epl"

    @patch("app.services.odds_api.odds_api_client.httpx")
    def test_finds_fuzzy_match(self, mock_httpx):
        """Should match even with slightly different casing/spacing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_EVENTS_RESPONSE
        mock_httpx.get.return_value = mock_response

        result = find_event("fake_key", "manchester united", "liverpool", sport_key="soccer_epl")
        assert result is not None
        assert result[0] == "event_001"

    @patch("app.services.odds_api.odds_api_client.httpx")
    def test_returns_none_when_no_match(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_EVENTS_RESPONSE
        mock_httpx.get.return_value = mock_response

        result = find_event("fake_key", "FC Barcelona", "Real Madrid", sport_key="soccer_epl")
        assert result is None

    @patch("app.services.odds_api.odds_api_client.httpx")
    def test_searches_multiple_leagues_when_no_sport_key(self, mock_httpx):
        """When sport_key is None, should search across SOCCER_SPORT_KEYS."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # First league returns nothing, second returns the match
        mock_response.json.side_effect = [
            [],  # first league empty
            SAMPLE_EVENTS_RESPONSE,  # second league has the match
        ]
        mock_httpx.get.return_value = mock_response

        result = find_event("fake_key", "Arsenal", "Chelsea")
        assert result is not None
        assert result[0] == "event_002"

    @patch("app.services.odds_api.odds_api_client.httpx")
    def test_handles_api_error_gracefully(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Server Error"}
        mock_httpx.get.return_value = mock_response

        result = find_event("fake_key", "Manchester United", "Liverpool", sport_key="soccer_epl")
        assert result is None


# ── fetch_sharp_odds ─────────────────────────────────────────────

class TestFetchSharpOdds:
    @patch("app.services.odds_api.odds_api_client.httpx")
    def test_returns_sharp_odds_dict(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_EVENT_ODDS_RESPONSE
        mock_httpx.get.return_value = mock_response

        result = fetch_sharp_odds(
            "fake_key", "soccer_epl", "event_001",
            "Manchester United", "Liverpool",
        )
        assert "pinnacle" in result
        assert "betfair_ex_eu" in result
        assert "bet365" not in result

    @patch("app.services.odds_api.odds_api_client.httpx")
    def test_returns_empty_on_api_error(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Unauthorized"}
        mock_httpx.get.return_value = mock_response

        result = fetch_sharp_odds(
            "fake_key", "soccer_epl", "event_001",
            "Team A", "Team B",
        )
        assert result == {}

    @patch("app.services.odds_api.odds_api_client.httpx")
    def test_returns_empty_on_exception(self, mock_httpx):
        mock_httpx.get.side_effect = Exception("Network error")

        result = fetch_sharp_odds(
            "fake_key", "soccer_epl", "event_001",
            "Team A", "Team B",
        )
        assert result == {}
