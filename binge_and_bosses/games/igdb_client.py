"""
    Game data from IGDB (igdb.com). Twitch issues the access token: we cache it until shortly
    before it expires, and get a new one if IGDB rejects it. Both functions return games in our
    own shape (see _game), or None when IGDB or Twitch can't be reached.
"""
from datetime import datetime, timezone
from http import HTTPStatus

import requests
from django.conf import settings
from django.core.cache import cache

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
BASE_URL = "https://api.igdb.com/v4/"
API_URL = BASE_URL + "games"
COVER_URL = "https://images.igdb.com/igdb/image/upload/t_cover_big/{}.jpg"
TOKEN_CACHE_KEY = "igdb_access_token"
FIELDS = "name,summary,first_release_date,total_rating,cover.image_id,genres.name,platforms.name"
# Main games, standalone expansions, remakes, remasters, expanded games and ports.
# Leaves out mods, DLC, bundles and alternate editions (version_parent), which crowd out the real game.
RELEASES = "game_type = (0,4,8,9,10,11) & version_parent = null"
RELEASES_ONLY = f"where {RELEASES}"
# The kinds of names search by description can filter on, each an IGDB endpoint and a /games field
VOCABULARY = ("genres", "themes", "game_modes", "platforms")
# A game must have all of these it is asked for (any one of them if none has all); platforms only need one
ALL_OF = ("genres", "themes", "game_modes")


def search_game(game_name):
    """The 5 best-known games matching the title. IGDB ranks matches by text alone, which can put a
    fan game or an obscure namesake first, so we fetch 20 and sort them by how many ratings they have."""
    title = game_name.replace("\\", "\\\\").replace('"', '\\"')
    cache_key = f"SearchGame_{game_name}"

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



def vocabulary():
    """IGDB's genre, theme, game mode and platform names, as {kind: {name: id}}, or None if IGDB fails."""
    names = cache.get("igdb_vocabulary")
    if names is None:
        names = {}
        for kind in VOCABULARY:
            rows = _query("fields name; limit 500;", kind)
            if rows is None:
                return None
            names[kind] = {row["name"]: row["id"] for row in rows}
        cache.set("igdb_vocabulary", names, timeout=24 * 3600)
    return names


def similar_games(title):
    """IDs IGDB lists as similar to the best-known game with this title: [] if there's none, None if IGDB fails."""
    matches = search_game(title)
    if not matches:
        return matches
    rows = _query(f"fields similar_games; where id = {int(matches[0]['id'])};")
    if rows is None:
        return None
    return rows[0].get("similar_games", []) if rows else []


def find_games(filters):
    """Up to 10 of the best-known games that match filters: lists of IGDB ids for each VOCABULARY kind,
    'ids' (only these games, or None for any) and 'released_after'/'released_before' years (or None)."""
    games = _find(filters, all_of=True)
    if games == [] and any(len(filters[kind]) > 1 for kind in ALL_OF):
        games = _find(filters, all_of=False)
    return games


def _find(filters, all_of):
    conditions = [RELEASES]
    for kind in VOCABULARY:
        if filters[kind]:
            ids = ",".join(str(int(i)) for i in filters[kind])
            conditions.append(f"{kind} = [{ids}]" if all_of and kind in ALL_OF else f"{kind} = ({ids})")
    if filters["ids"] is not None:
        conditions.append(f"id = ({','.join(str(int(i)) for i in filters['ids'])})")
    if filters["released_after"]:
        conditions.append(f"first_release_date >= {_new_year(filters['released_after'])}")
    if filters["released_before"]:
        conditions.append(f"first_release_date < {_new_year(filters['released_before'] + 1)}")
    games = _query(f"fields {FIELDS}; where {' & '.join(conditions)}; sort total_rating_count desc; limit 10;")
    return None if games is None else [_game(game) for game in games]


def _new_year(year):
    return int(datetime(int(year), 1, 1, tzinfo=timezone.utc).timestamp())


def _query(body, endpoint="games"):
    try:
        response = _post(body, _token(), endpoint)
        if response.status_code == HTTPStatus.UNAUTHORIZED:   # the token was revoked or expired early
            response = _post(body, _token(refresh=True), endpoint)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None


def _post(body, token, endpoint="games"):
    return requests.post(BASE_URL + endpoint, data=body, timeout=10, headers={
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
