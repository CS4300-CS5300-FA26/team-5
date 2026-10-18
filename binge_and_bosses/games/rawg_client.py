import requests
from django.conf import settings

BASE_URL = "https://api.rawg.io/api/games"

def search_game(game_name):
    try:
        response = requests.get(BASE_URL, params={"key": settings.RAWG_API_KEY, "search": game_name, "page_size": 5}, timeout=10)
        response.raise_for_status()
        return response.json().get("results", [])
    except requests.exceptions.RequestException
    return None

