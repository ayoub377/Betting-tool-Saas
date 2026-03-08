from app.services.flashscore_scraper.flashscore_scraper import FlashScoreScraper
from app.services.flashscore_scraper.tennis_scraper import TennisFlashScoreScraper
from app.services.flashscore_scraper.scraper_factory import get_scraper

__all__ = ["FlashScoreScraper", "TennisFlashScoreScraper", "get_scraper"]
