from sqlalchemy import Column, Integer, String, Float, Text, Index
from app.models.team import Base


class TrackedMatch(Base):
    __tablename__ = "tracked_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String(50), unique=True, index=True, nullable=False)
    home_team = Column(String(255))
    away_team = Column(String(255))
    start_time = Column(String(100))
    start_time_raw = Column(String(100))
    status = Column(String(50), default="tracking")
    tracked_since = Column(String(100))
    # Odds API event mapping (populated when ODDS_API_KEY is set)
    odds_api_event_id = Column(String(100), nullable=True)
    odds_api_sport_key = Column(String(100), nullable=True)


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(String(100), nullable=False)
    home = Column(Float)
    draw = Column(Float)
    away = Column(Float)
    bookmaker = Column(String(255))
    # JSON-encoded sharp bookmaker odds (nullable for backward compat)
    sharp_odds = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_odds_snapshots_match_id_id", "match_id", "id"),
    )
