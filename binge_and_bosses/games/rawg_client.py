import requests
from django.conf import settings

BASE_URL = "https://api.rawg.io/api/games"

#search rawg by name of game and return first 5 results; default to none 
def search_game(game_name):
    try:
        response = requests.get(BASE_URL, params={"key": settings.RAWG_API_KEY, "search": game_name, "page_size": 5}, timeout=10)
        response.raise_for_status()
        return response.json().get("results", [])
    except requests.exceptions.RequestException
    return None

#rawg returns game details by game id, so we need the id to get deets 
def get_game_details(game_id):
    try:
        response = requests.get(f"{BASE_URL}/{game_id}", params={"key": settings.RAWG_API_KEY}, timeout=10)
        response.raise_for_status
        return response.json().get("results", [])
    except requests.exceptions.RequestException:
        return None