"""
    Game data from IGDB (igdb.com). Twitch issues the access token: we cache it until shortly
    before it expires, and get a new one if IGDB rejects it. Both functions return games in our
    own shape (see _game), or None when IGDB or Twitch can't be reached.
"""
import hashlib
from datetime import datetime, timezone
from http import HTTPStatus

import requests
from django.conf import settings
from django.core.cache import cache

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
API_URL = "https://api.igdb.com/v4/games"
COVER_URL = "https://images.igdb.com/igdb/image/upload/t_cover_big/{}.jpg"
TOKEN_CACHE_KEY = "igdb_access_token"
FIELDS = "name,summary,first_release_date,total_rating,cover.image_id,genres.name,platforms.name"
# Main games, standalone expansions, remakes, remasters, expanded games and ports.
# Leaves out mods, DLC, bundles and alternate editions (version_parent), which crowd out the real game.
RELEASES_ONLY = "where game_type = (0,4,8,9,10,11) & version_parent = null"


def search_game(game_name):
    """The 5 best-known games matching the title. IGDB ranks matches by text alone, which can put a
    fan game or an obscure namesake first, so we fetch 20 and sort them by how many ratings they have."""
    title = game_name.replace("\\", "\\\\").replace('"', '\\"')
    cache_key = search_cache_key(game_name)

    games_search = cache.get(cache_key)

    if games_search is None:
        games = _query(f'search "{title}"; fields {FIELDS},total_rating_count; {RELEASES_ONLY}; limit 20;')
        if games is None:
            return None
        games.sort(key=lambda game: game.get("total_rating_count", 0), reverse=True)
        game_search_result = [_game(game) for game in games[:5]]
        cache.set(cache_key,game_search_result,timeout=3600)
        return game_search_result

    return games_search



def search_cache_key(game_name):
    """IGDB matches titles regardless of case, so "Hollow Knight" and "hollow knight " share one entry.
    The hash keeps the key short and free of spaces, whatever the user typed."""
    normalized = game_name.strip().lower()
    return f"SearchGame_{hashlib.sha256(normalized.encode()).hexdigest()}"


def get_game_details(game_id):
    """One game by its IGDB id, or None if there's no such game."""
    cache_key = f"GameDetails_{int(game_id)}"

    # Get info from cache
    specific_game_detail = cache.get(cache_key)

    # If none then generate set a new cache and return it
    if specific_game_detail is None:
        games = _query(f"fields {FIELDS}; where id = {int(game_id)};")
        specific_game_detail = _game(games[0]) if games else None
        cache.set(cache_key,specific_game_detail,timeout=3600)
        return specific_game_detail

    # If not just return specific_game_detail
    return specific_game_detail



def _query(body):
    try:
        response = _post(body, _token())
        if response.status_code == HTTPStatus.UNAUTHORIZED:   # the token was revoked or expired early
            response = _post(body, _token(refresh=True))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None


def _post(body, token):
    return requests.post(API_URL, data=body, timeout=10, headers={
        "Client-ID": settings.IGDB_CLIENT_ID,
        "Authorization": f"Bearer {token}",
    })


def _token(refresh=False):
    token = None if refresh else cache.get(TOKEN_CACHE_KEY)
    if token is None:
        response = requests.post(TOKEN_URL, timeout=10, params={
            "client_id": settings.IGDB_CLIENT_ID,
            "client_secret": settings.IGDB_CLIENT_SECRET,
            "grant_type": "client_credentials",
        })
        response.raise_for_status()
        data = response.json()
        token = data["access_token"]
        cache.set(TOKEN_CACHE_KEY, token, data["expires_in"] - 60)
    return token


def _game(data):
    released = data.get("first_release_date")
    rating = data.get("total_rating")
    cover = data.get("cover")
    return {
        "id": data["id"],
        "name": data.get("name", ""),
        "summary": data.get("summary", ""),
        "released": datetime.fromtimestamp(released, timezone.utc).date().isoformat() if released else None,
        "rating": round(rating / 20, 2) if rating is not None else None,   # IGDB rates 0-100; we use 0-5
        "cover": COVER_URL.format(cover["image_id"]) if cover else "",
        "genres": [genre["name"] for genre in data.get("genres", [])],
        "platforms": [platform["name"] for platform in data.get("platforms", [])],
    }
