# api_logic.py
"""Core logic and FastAPI router for finding sports betting arbitrage opportunities.
This version has been refactored to use asynchronous requests and includes a daily user request limit.
"""
import os
from typing import Iterable, Generator, List, Dict, Any, Set, Optional
import time

import firebase_admin
import httpx  # Using httpx for asynchronous requests
import asyncio
import logging
from enum import Enum
from datetime import date

from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import credentials, auth
from firebase_admin.exceptions import FirebaseError
from pydantic import BaseModel, Field

from app.core.shared_dependencies import get_configured_api_key

# --- Basic Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants ---
BASE_URL = "https://api.the-odds-api.com/v4"
DAILY_REQUEST_LIMIT = 5

# --- In-Memory Request Tracking (for demonstration) ---
# In a production environment, replace this with a persistent database like Redis or Firestore.
USER_REQUESTS_DB: Dict[str, Dict[str, Any]] = {}  # e.g., { "user_id": {"count": 4, "date": "2025-06-17"} }


# --- Custom Exceptions ---
class APIException(RuntimeError):
    """Custom exception for API related errors."""

    def __init__(self, message: str, response: httpx.Response = None):
        super().__init__(message)
        try:
            self.response_content = response.json() if response and response.content else None
        except Exception:
            self.response_content = response.text if response else None
        self.status_code = response.status_code if response else None

    def __str__(self):
        if self.response_content and isinstance(self.response_content, dict) and 'message' in self.response_content:
            return f"('{self.args[0]}', '{self.response_content['message']}')"
        return f"('{self.args[0]}')"


class AuthenticationException(APIException):
    """Exception for authentication failures with The Odds API."""
    pass


class RateLimitException(APIException):
    """Exception for when API rate limits are exceeded."""
    pass


try:
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
except Exception as e:
    # This will prevent the app from starting if Firebase is not configured correctly.
    print(f"Failed to initialize Firebase Admin SDK: {e}")
    # In a real app, you might want to handle this more gracefully or exit.
    # For now, we'll let it raise the error.
    raise
# -----------------------------

# Instantiate the security scheme
security = HTTPBearer()


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    A robust dependency to verify a Firebase ID token and return the user's UID.

    This function replaces the insecure placeholder. It correctly validates the
    token using the Firebase Admin SDK, handles specific authentication errors,
    and returns the authenticated user's unique ID.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # The core of the logic: verify the token using the Firebase Admin SDK.
        # This function checks the token's signature, expiration, and issuer.
        decoded_token = auth.verify_id_token(token)

        # Extract the user ID (uid) from the decoded token.
        uid = decoded_token.get("uid")

        if not uid:
            # This is an important check. A valid token from Firebase Auth
            # should always contain a 'uid'.
            raise HTTPException(status_code=401, detail="User ID not found in token.")

        return uid

    # Handle specific, common errors from Firebase for better client feedback.
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="The provided Firebase token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="The provided Firebase token is invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Handle the base FirebaseError as a fallback.
    except FirebaseError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Firebase authentication error: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # A generic catch-all for any other unexpected errors.
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during authentication."
        )


async def rate_limit_user(user_id: str = Depends(get_current_user_id)):
    """
    Dependency that enforces the daily request limit.
    This runs for any endpoint that includes it as a dependency.
    """
    today = date.today()
    user_data = USER_REQUESTS_DB.get(user_id)

    if not user_data or user_data["date"] != today:
        # User's first request of the day or a new user
        USER_REQUESTS_DB[user_id] = {"count": 1, "date": today}
        logging.info(f"User {user_id} made their first request today. Count: 1.")
    elif user_data["count"] >= DAILY_REQUEST_LIMIT:
        logging.warning(f"User {user_id} has exceeded their daily limit of {DAILY_REQUEST_LIMIT} requests.")
        raise HTTPException(
            status_code=429,
            detail=f"You have exceeded your daily limit of {DAILY_REQUEST_LIMIT} requests. Please try again tomorrow."
        )
    else:
        # Increment the user's request count for today
        user_data["count"] += 1
        logging.info(f"User {user_id} request count updated to {user_data['count']}.")


# --- Core Logic Functions (Async) ---

def handle_faulty_response(response: httpx.Response):
    """Handles non-2xx responses from the API."""
    if response.status_code == 401:
        raise AuthenticationException("Failed to authenticate with The Odds API. Is the API key valid?", response)
    elif response.status_code == 429:
        raise RateLimitException("Encountered API rate limit.", response)
    else:
        raise APIException(f"Unknown issue arose while trying to access the API. Status: {response.status_code}",
                           response)


async def get_sports(key: str, client: httpx.AsyncClient) -> Set[str]:
    """Fetches the list of available sports from The Odds API asynchronously."""
    url = f"{BASE_URL}/sports/"
    params = {"apiKey": key}
    try:
        response = await client.get(url, params=params, timeout=10)
        if response.status_code != 200:
            handle_faulty_response(response)
        return {item["key"] for item in response.json()}
    except httpx.RequestError as req_err:
        raise APIException(f"Request failed: {req_err}")
    except (ValueError, KeyError) as e:
        raise APIException(f"Failed to parse sports data from API: {e}", response)


async def get_data_for_sport(key: str, sport: str, region: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetches odds data for a specific sport and region asynchronously."""
    url = f"{BASE_URL}/sports/{sport}/odds/"
    params = {"apiKey": key, "regions": region, "oddsFormat": "decimal", "dateFormat": "unix"}
    try:
        response = await client.get(url, params=params, timeout=15)
        if response.status_code != 200:
            handle_faulty_response(response)

        data = response.json()
        if not isinstance(data, list):
            logging.warning(f"API returned non-list data for sport {sport}, region {region}: {data}")
            return []
        return data
    except httpx.RequestError as req_err:
        raise APIException(f"Request failed for sport {sport}: {req_err}")
    except ValueError as e:
        raise APIException(f"Failed to parse odds data for sport {sport}: {e}", response)


def process_match_data(matches: Iterable[Dict[str, Any]], include_started_matches: bool = True) -> Generator[
    Dict[str, Any], None, None]:
    """Extracts relevant information from matches and calculates implied odds. (This function remains synchronous as it's CPU-bound)."""
    for match in matches:
        try:
            start_time = int(match["commence_time"])
            if not include_started_matches and start_time < time.time():
                continue

            best_odd_per_outcome = {}
            if not match.get("bookmakers"): continue

            for bookmaker in match["bookmakers"]:
                bookie_name = bookmaker.get("title", "Unknown Bookmaker")
                if not bookmaker.get("markets"): continue

                market = bookmaker["markets"][0]  # Assuming H2H
                if not market.get("outcomes"): continue

                for outcome in market["outcomes"]:
                    outcome_name = outcome.get("name")
                    try:
                        odd = float(outcome.get("price"))
                    except (ValueError, TypeError):
                        continue

                    if outcome_name not in best_odd_per_outcome or odd > best_odd_per_outcome[outcome_name][1]:
                        best_odd_per_outcome[outcome_name] = (bookie_name, odd)

            if len(best_odd_per_outcome) < 2: continue

            total_implied_odds = sum(1 / details[1] for details in best_odd_per_outcome.values() if details[1] > 0)

            match_name = f"{match.get('home_team', 'N/A')} vs. {match.get('away_team', 'N/A')}"
            time_to_start_hours = (start_time - time.time()) / 3600

            yield {
                "match_id": match.get("id", "N/A"),
                "match_name": match_name,
                "match_start_time_unix": start_time,
                "match_start_time_iso": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(start_time)),
                "hours_to_start": round(time_to_start_hours, 2),
                "sport_key": match.get("sport_key", "N/A"),
                "sport_title": match.get("sport_title", "N/A"),
                "best_outcome_odds": best_odd_per_outcome,
                "total_implied_odds": round(total_implied_odds, 5),
            }
        except (KeyError, TypeError, ValueError) as e:
            logging.warning(
                f"Skipping a match due to processing error: {e} in match ID: {match.get('id', 'Unknown ID')}")
            continue


async def get_all_odds_data(api_key: str, sports_keys: Set[str], region: str, client: httpx.AsyncClient) -> List[
    Dict[str, Any]]:
    """Fetches and combines odds data for all specified sports concurrently."""
    tasks = [get_data_for_sport(api_key, sport_key, region, client) for sport_key in sports_keys]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_matches_data = []
    for i, res in enumerate(results):
        sport_key_list = list(sports_keys)
        # Check if index is valid
        if i < len(sport_key_list):
            sport_key = sport_key_list[i]
            if isinstance(res, Exception):
                logging.error(f"Could not fetch data for sport {sport_key}: {res}")
            elif isinstance(res, list):
                all_matches_data.extend(res)
        else:
            logging.error(f"Result index {i} out of bounds for sports_keys list.")

    return all_matches_data


async def find_arbitrage_opportunities_logic(
        api_key: str,
        region: str,
        profit_margin_cutoff: float,
        client: httpx.AsyncClient,
        sports_to_check: Optional[Set[str]] = None,
        include_started: bool = False
) -> List[Dict[str, Any]]:
    """Main async logic function to find arbitrage opportunities."""
    logging.info(f"Starting arbitrage search for region: {region}, cutoff: {profit_margin_cutoff * 100:.2f}%")

    sports_to_use: Set[str]
    if not sports_to_check:
        try:
            logging.info("Fetching available sports...")
            sports_to_use = await get_sports(key=api_key, client=client)
            if not sports_to_use:
                logging.warning("No sports found or API key issue.")
                return []
            logging.info(f"Found {len(sports_to_use)} sports.")
        except APIException as e:
            logging.error(f"Critical error fetching sports: {e}")
            raise
    else:
        sports_to_use = sports_to_check
        logging.info(f"Using provided sports list: {sports_to_use}")

    logging.info("Fetching all odds data concurrently...")
    all_odds_data = await get_all_odds_data(api_key, sports_to_use, region, client)

    if not all_odds_data:
        logging.info("No odds data fetched. Exiting.")
        return []
    logging.info(f"Total matches/events fetched: {len(all_odds_data)}")

    logging.info("Processing fetched data to identify opportunities...")
    processed_results = process_match_data(all_odds_data, include_started_matches=include_started)

    arbitrage_opportunities = [
        arb for arb in processed_results
        if 0 < arb["total_implied_odds"] < (1.0 - profit_margin_cutoff)
    ]
    logging.info(f"Found {len(arbitrage_opportunities)} arbitrage opportunities meeting the criteria.")
    return arbitrage_opportunities


# --- FastAPI Router Definition ---
router = APIRouter()


# --- Pydantic Models for Arbitrage Router ---
class ArbitrageOpportunityModel(BaseModel):
    match_id: str
    match_name: str
    match_start_time_unix: int
    match_start_time_iso: str
    hours_to_start: float
    sport_key: str
    sport_title: str
    best_outcome_odds: Dict[str, List[Any]]
    total_implied_odds: float
    profit_margin_percentage: float = Field(...,
                                            description="Calculated profit margin as a percentage (e.g., 1.5 for 1.5%)")


class ArbitrageResponseModel(BaseModel):
    message: str
    opportunities_count: int
    opportunities: List[ArbitrageOpportunityModel]


class RegionModel(str, Enum):
    eu = "eu"
    us = "us"
    au = "au"
    uk = "uk"


# --- Arbitrage Endpoints ---
@router.get(
    "/",
    summary="Find Arbitrage Opportunities",
    response_model=ArbitrageResponseModel,
    tags=["Arbitrage Operations"],
    dependencies=[Depends(rate_limit_user)]  # This applies the rate limit to the endpoint
)
async def find_arbitrage_endpoint(
        api_key: str = Depends(get_configured_api_key),
        region: RegionModel = Query(RegionModel.eu, description="The region to search for odds (eu, us, au, uk)."),
        cutoff: float = Query(0.0, ge=0.0, lt=1.0, description="Minimum profit margin cutoff (e.g., 0.01 for 1%)."),
        sports: Optional[str] = Query(None,
                                      description="Comma-separated list of sport keys (e.g., 'soccer_epl,basketball_nba'). If empty, all sports are checked."),
        include_started_matches: bool = Query(False,
                                              description="Whether to include matches that have already started.")
):
    """
    Identifies sports betting arbitrage opportunities by fetching odds data asynchronously.
    An authentication token is required, and requests are limited to 5 per user per day.
    """
    try:
        sports_set = set(s.strip() for s in sports.split(',')) if sports and sports.strip() else None

        async with httpx.AsyncClient() as client:
            raw_opportunities = await find_arbitrage_opportunities_logic(
                api_key=api_key,
                region=region.value,
                profit_margin_cutoff=cutoff,
                sports_to_check=sports_set,
                include_started=include_started_matches,
                client=client
            )

        formatted_opportunities = []
        for opp in raw_opportunities:
            if opp.get("total_implied_odds", 0) > 0:
                profit_margin = (1.0 - opp["total_implied_odds"]) * 100
            else:
                profit_margin = -float('inf')

            formatted_opportunities.append(
                ArbitrageOpportunityModel(
                    **opp,
                    profit_margin_percentage=round(profit_margin, 2)
                )
            )

        # Sort opportunities by highest profit margin
        formatted_opportunities.sort(key=lambda x: x.profit_margin_percentage, reverse=True)

        count = len(formatted_opportunities)
        message = f"{count} arbitrage opportunities found." if count > 0 else "No arbitrage opportunities found matching your criteria."

        return ArbitrageResponseModel(
            message=message,
            opportunities_count=count,
            opportunities=formatted_opportunities
        )
    except AuthenticationException as e:
        raise HTTPException(status_code=401,
                            detail={"type": "AuthenticationError", "message": str(e), "details": e.response_content})
    except RateLimitException as e:
        raise HTTPException(status_code=429,
                            detail={"type": "RateLimitError", "message": str(e), "details": e.response_content})
    except APIException as e:
        status_code = e.status_code if e.status_code and e.status_code >= 400 else 502
        raise HTTPException(status_code=status_code,
                            detail={"type": "UpstreamAPIError", "message": str(e), "details": e.response_content})
    except Exception as e:
        logging.error(f"An unexpected internal server error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"type": "InternalServerError",
                                                     "message": "An unexpected error occurred on the server."})
