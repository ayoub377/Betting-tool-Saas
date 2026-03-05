# import json
# import uuid
# from datetime import datetime
# import requests
# from app.models.database import SessionLocal
# from app.models.team import Team, Player
#
# import logging
# from sqlalchemy.orm import Session
#
import json
import logging
import os
from app.core.config import redis_client

# # Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
#
#


import httpx


async def fetch_club_id(club_name: str):
    """
    Fetches a club ID.
    1. Checks cache (if enabled).
    2. If cache miss or bypassed, calls an external API to search for the club.
    3. Uses the ID of the VERY FIRST club in the API's "results" list, if available.
    Returns a dictionary like {"id": "club_id_string"} or None.
    """
    # --- CONFIGURATION FOR TESTING ---
    BYPASS_CACHE_FOR_TESTING = False  # << Set to True to disable caching, False to enable
    # --- END CONFIGURATION ---

    cache_key = f"club_id:{club_name}"

    if not BYPASS_CACHE_FOR_TESTING:
        try:
            print(f"Attempting to retrieve from cache for '{club_name}' with key: {cache_key}")
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                # Handle both bytes and string types from Redis
                if isinstance(cached_data, bytes):
                    cached_id_str = cached_data.decode('utf-8')
                else:
                    cached_id_str = str(cached_data)
                print(f"Cache hit for '{club_name}'. Club ID: {cached_id_str}")
                return {"id": cached_id_str}
            else:
                print(f"Cache miss for '{club_name}'.")
        except Exception as e:
            print(f"Redis error while GETTING cache for '{club_name}': {e}. Proceeding to API call.")
    else:
        print(f"INFO: Cache is BYPASSED for testing for '{club_name}'.")

    # If cache is bypassed or it's a cache miss, proceed to fetch from API
    print(f"Fetching club ID for '{club_name}' from API.")
    base_url = os.getenv("INTERNAL_API_URL", "http://localhost:9000") + "/api/clubs"
    club_id_to_return_str = None

    try:
        async with httpx.AsyncClient(proxies=None) as client:
            response = await client.get(f"{base_url}/search/{club_name}")
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses

            club_search_data = response.json()
            api_results_list = club_search_data.get("results", [])

            if api_results_list:  # Check if the list of results is not empty
                print(f"API search for '{club_name}' returned {len(api_results_list)} results. Using the first item.")

                first_club_data = api_results_list[0]  # Get the first club from the list
                api_club_id = first_club_data.get("id")
                api_club_name_for_log = first_club_data.get("name", "N/A")  # For logging purposes

                if api_club_id is not None:
                    club_id_to_return_str = str(api_club_id)  # Ensure it's a string
                    print(
                        f"Using FIRST item from API results for '{club_name}': Name='{api_club_name_for_log}', ID='{club_id_to_return_str}'.")
                else:
                    print(f"The first item in API results for '{club_name}' has no 'id' field. Data: {first_club_data}")
                    # club_id_to_return_str remains None
            else:
                print(f"No results returned by API for club search: '{club_name}'.")
                # club_id_to_return_str remains None

            # Cache the result if an ID was determined AND caching is not bypassed
            if club_id_to_return_str and not BYPASS_CACHE_FOR_TESTING:
                try:
                    await redis_client.set(cache_key, club_id_to_return_str, ex=86400)  # Cache for 24 hours
                    print(f"Cached ID '{club_id_to_return_str}' for '{club_name}'.")
                except Exception as e:
                    print(f"Redis error while SETTING cache for '{club_name}' (ID: {club_id_to_return_str}): {e}")
            elif club_id_to_return_str and BYPASS_CACHE_FOR_TESTING:
                print(f"INFO: Caching SKIPPED for '{club_name}' (ID: {club_id_to_return_str}) due to bypass flag.")

            if club_id_to_return_str:
                return {"id": club_id_to_return_str}

    except httpx.HTTPStatusError as http_err:
        error_message = f"HTTP error for '{club_name}': {http_err.request.url} - Status {http_err.response.status_code}"
        try:
            error_detail = http_err.response.json()
            error_message += f" - Detail: {error_detail}"
        except ValueError:
            error_message += f" - Content (text): {http_err.response.text[:200]}..."
        print(error_message)
    except httpx.RequestError as req_err:
        print(f"Request error for '{club_name}': {req_err.request.url} - {req_err}")
        # Try alternative search terms if the full name fails
        if ' ' in club_name:
            # Try with just the first word
            first_word = club_name.split(' ')[0]
            print(f"Trying alternative search with first word: '{first_word}'")
            try:
                async with httpx.AsyncClient(proxies=None) as client:
                    alt_response = await client.get(f"{base_url}/search/{first_word}")
                    alt_response.raise_for_status()
                    alt_club_search_data = alt_response.json()
                    alt_api_results_list = alt_club_search_data.get("results", [])
                    
                    if alt_api_results_list:
                        # Find the best match
                        for club in alt_api_results_list:
                            club_name_lower = club.get("name", "").lower()
                            if club_name.lower() in club_name_lower:
                                club_id_to_return_str = str(club.get("id"))
                                print(f"Found alternative match: '{club.get('name')}' (ID: {club_id_to_return_str})")
                                
                                # Cache the result
                                if not BYPASS_CACHE_FOR_TESTING:
                                    try:
                                        await redis_client.set(cache_key, club_id_to_return_str, ex=86400)
                                        print(f"Cached alternative ID '{club_id_to_return_str}' for '{club_name}'.")
                                    except Exception as e:
                                        print(f"Redis error while SETTING cache for '{club_name}' (ID: {club_id_to_return_str}): {e}")
                                
                                return {"id": club_id_to_return_str}
            except Exception as alt_e:
                print(f"Alternative search also failed: {alt_e}")
    except json.JSONDecodeError as json_err:  # If response.json() fails
        print(f"JSON decode error for '{club_name}': {json_err}. Response text might not be valid JSON.")
    except Exception as e:  # Catch any other unexpected errors
        print(f"An unexpected error occurred while fetching club ID for '{club_name}': {e}")

    print(f"Could not determine club ID for '{club_name}'. Returning None.")
    return None
#
# # Function to fetch data from each endpoint
# def fetch_club_data(club_id):
#     base_url = "http://127.0.0.1:9000/clubs"  # Adjusted base URL to point to the actual endpoint
#
#     # Fetch data from the endpoints
#     try:
#         profile_response = requests.get(f"{base_url}/{club_id}/profile")
#         stadium_response = requests.get(f"{base_url}/{club_id}/stadium")
#         players_response = requests.get(f"{base_url}/{club_id}/players")
#         staffs_response = requests.get(f"{base_url}/{club_id}/staffs")
#
#         # Check if responses are successful
#         profile_response.raise_for_status()
#         stadium_response.raise_for_status()
#         players_response.raise_for_status()
#         staffs_response.raise_for_status()
#
#         # Parse the JSON responses
#         club_profile = profile_response.json()  # Ensure we call .json() on a successful response
#         club_stadium = stadium_response.json()
#         club_players = players_response.json()
#         club_staffs = staffs_response.json()
#
#         return {
#             "profile": club_profile,
#             "stadium": club_stadium,
#             "players": club_players,
#             "staffs": club_staffs,
#         }
#
#     except requests.exceptions.HTTPError as http_err:
#         print(f"HTTP error occurred: {http_err}")
#     except requests.exceptions.RequestException as req_err:
#         print(f"Request error occurred: {req_err}")
#     except ValueError as json_err:
#         print(f"JSON decode error: {json_err}")
#
#     return None  # Return None if there was an error
#
#

async def fetch_club_players_data(club_id):
    base_url = os.getenv("INTERNAL_API_URL", "http://localhost:9000") + "/api/clubs"  # Adjusted base URL to point to the actual endpoint

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/{club_id}/players", timeout=15)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except httpx.RequestError as req_err:
        print(f"Request error occurred: {req_err}")
    except ValueError as json_err:
        print(f"JSON decode error: {json_err}")

    return None  # Return None if there was an error


#
#
# def populate_team(session: Session, team_data: dict, stadium_data: dict, staff_data: dict) -> Team:
#     try:
#         new_team = Team(
#             id=team_data['id'],
#             name=team_data['name'],
#             total_value=parse_market_value(team_data['currentMarketValue']),
#             average_attendance=int(stadium_data['average_attendance'].replace(',', '')),
#             stadium_seats=int(team_data["stadiumSeats"]),
#             coach_name=staff_data.get('name', None),
#             assigned_date=datetime.strptime(staff_data.get('appointed', None), '%b %d, %Y') if staff_data.get(
#                 'appointed') else None,
#             end_contract=datetime.strptime(staff_data.get('contract_expires', None), '%d.%m.%Y') if staff_data.get(
#                 'contract_expires') else None,
#         )
#
#         session.add(new_team)
#         session.commit()
#         return new_team
#
#     except Exception as e:
#         logger.error(f"Error adding team {team_data['name']}: {e}")
#         session.rollback()
#
#
# # def populate_players(session: Session, players_data: list, team_id: int):
# #     for player in players_data:
# #         # Create a new Player instance
# #         new_player = Player(
# #             PlayerId=player['id'],
# #             name=player['name'],
# #             position=player['position'],
# #             marketvalue=parse_market_value(player.get('marketValue', 0)),
# #             status=player.get("status", "No Status"),
# #             age=int(player['age']),
# #             teamid=team_id  # Foreign key reference to Team
# #         )
# #
# #         # Add the new player instance to the session
# #         session.add(new_player)
# #
# #     # Commit the players to the database
# #     session.commit()
# #
# #
# # def populate_team_and_players(json_data: dict):
# #     session = SessionLocal()
# #
# #     try:
# #         # Extract data from JSON
# #         team_data = json_data['profile']
# #         stadium_data = json_data['stadium']
# #         staff_data = json_data['staffs']
# #         players_data = json_data['players']['players']
# #         new_team = populate_team(session, team_data, stadium_data, staff_data)
# #
# #         # Populate players
# #         if isinstance(players_data, list):
# #             populate_players(session, players_data, new_team.id)
# #         else:
# #             logger.error(f"Invalid players data format: {players_data}")
# #
# #     except Exception as e:
# #         session.rollback()  # Rollback in case of error
# #         logger.error(f"Error populating data: {e}")
# #     finally:
# #         session.close()  # Ensure session is closed after operation
# #
# #
# # # # Read club names from the text file and process each one
# # # with open('./clubs', 'r', encoding='utf-8') as file:
# # #     for line in file:
# # #         club_name = line.strip()  # Remove any leading/trailing whitespace
# # #
# # #         if not club_name:  # Skip empty lines if any exist in the file
# # #             continue
# # #
# # #         print(f"Processing {club_name}...")
# # #
# # #         club_search = fetch_club_id(club_name)
# # #
# # #         if club_search is not None:
# # #             id__ = club_search.get('id')
# # #             data = fetch_club_data(id__)
# # #
# # #             if data is not None:
# # #                 populate_team_and_players(data)
# # #             else:
# # #                 print(f"No data found for {club_name}.")
# #
# #
# # def get_players_from_clubs(club_name1, club_name2):
# #     # Fetch club IDs
# #     club1_id = fetch_club_id(club_name1)
# #     club2_id = fetch_club_id(club_name2)
# #
# #     if not club1_id or not club2_id:
# #         print("Could not fetch one or both club IDs.")
# #         return None
# #
# #     # Fetch players data
# #     players_club1 = fetch_club_players_data(club1_id["id"])
# #     players_club2 = fetch_club_players_data(club2_id["id"])
# #
# #     filtered_players = {
# #         club_name1: [],
# #         club_name2: []
# #     }
# #
# #     # Process players for club 1
# #     if isinstance(players_club1, dict):
# #         players_list = players_club1["players"]
# #         if isinstance(players_list, dict):  # Ensure it's a list
# #             players_list = players_list.get('players')
# #             print(len(players_list))
# #             for player in players_list:
# #                 if isinstance(player, dict) and 'status' in player:
# #                     filtered_players[club_name1].append(player)
# #         else:
# #             print(f"Expected 'players' to be a list for {club_name1}: {players_list}")
# #
# #     # Process players for club 2
# #     if isinstance(players_club2, dict):
# #         players_list = players_club2["players"]
# #         if isinstance(players_list, dict):  # Ensure it's a list
# #             players_list = players_list.get('players')
# #             for player in players_list:
# #                 if isinstance(player, dict) and 'status' in player:
# #                     filtered_players[club_name2].append(player)
# #
# #         else:
# #             print(f"Expected 'players' to be a list for {club_name2}: {players_list}")
# #
# #     return filtered_players
# #
#
# # Example usage
#
#
# data = get_players_from_clubs('pohang', 'vissel')
#
# print(data)
