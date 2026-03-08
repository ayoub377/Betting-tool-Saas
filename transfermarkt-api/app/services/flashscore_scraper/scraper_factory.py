from app.models.sport import SportType
from app.services.flashscore_scraper.flashscore_scraper import FlashScoreScraper
from app.services.flashscore_scraper.tennis_scraper import TennisFlashScoreScraper

_SCRAPER_REGISTRY = {
    SportType.FOOTBALL: FlashScoreScraper,
    SportType.TENNIS: TennisFlashScoreScraper,
}


def get_scraper(sport: SportType, **kwargs):
    """Factory function to get the appropriate scraper for a sport."""
    cls = _SCRAPER_REGISTRY.get(sport)
    if not cls:
        raise ValueError(f"No scraper registered for sport: {sport}")
    return cls(**kwargs)
