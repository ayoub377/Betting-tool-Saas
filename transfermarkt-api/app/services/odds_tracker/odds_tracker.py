import json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# Redis key helpers — single place to change key shapes
def match_meta_key(match_id: str) -> str:
    return f"tracked_match:{match_id}"


def odds_history_key(match_id: str) -> str:
    return f"odds_history:{match_id}"


TRACKED_INDEX_KEY = "tracked_matches_index"


async def store_odds_snapshot(redis_client, match_id: str, odds: dict):
    """Append one odds snapshot to the match history list."""
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "home": odds.get("home"),
        "draw": odds.get("draw"),
        "away": odds.get("away"),
        "bookmaker": odds.get("bookmaker"),
    }
    await redis_client.rpush(odds_history_key(match_id), json.dumps(snapshot))
    logger.info("Stored odds snapshot for %s: %s", match_id, snapshot)


async def get_odds_history(redis_client, match_id: str) -> list[dict]:
    """Return full odds history for a match, oldest first."""
    raw_entries = await redis_client.lrange(odds_history_key(match_id), 0, -1)
    return [json.loads(entry) for entry in raw_entries]


async def get_match_meta(redis_client, match_id: str) -> Optional[dict]:
    raw = await redis_client.get(match_meta_key(match_id))
    return json.loads(raw) if raw else None


async def get_all_tracked_ids(redis_client) -> list[str]:
    members = await redis_client.smembers(TRACKED_INDEX_KEY)
    return [m.decode() if isinstance(m, bytes) else m for m in members]


async def is_already_tracked(redis_client, match_id: str) -> bool:
    return await redis_client.sismember(TRACKED_INDEX_KEY, match_id)


async def register_match(redis_client, match_id: str, meta: dict):
    """Persist match metadata and add to the tracking index."""
    await redis_client.set(match_meta_key(match_id), json.dumps(meta))
    await redis_client.sadd(TRACKED_INDEX_KEY, match_id)
    logger.info("Registered match %s for tracking: %s", match_id, meta)


async def unregister_match(redis_client, match_id: str):
    """Remove match from active tracking index (keep history intact)."""
    await redis_client.srem(TRACKED_INDEX_KEY, match_id)
    # Update status in meta
    raw = await redis_client.get(match_meta_key(match_id))
    if raw:
        meta = json.loads(raw)
        meta["status"] = "completed"
        await redis_client.set(match_meta_key(match_id), json.dumps(meta))
    logger.info("Unregistered match %s — tracking complete.", match_id)
