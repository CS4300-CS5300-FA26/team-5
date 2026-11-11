from datetime import date

from .igdb_client import get_game_details
from .models import Game


def get_or_import(igdb_id):
    """Return our Game for this IGDB id, saving it from IGDB the first time."""
    game = Game.objects.filter(igdb_id=igdb_id).first()
    if game:
        return game

    data = get_game_details(igdb_id)
    if data is None:
        return None

    game, _ = Game.objects.get_or_create(
        igdb_id=igdb_id,
        defaults={
            "game_title": data["name"],
            "game_description": data["summary"],
            "game_rating": data["rating"] or 0,
            "game_release": date.fromisoformat(data["released"]) if data["released"] else None,
            "game_image": data["cover"],
            "game_genre": ", ".join(data["genres"]),
            "game_platforms": ", ".join(data["platforms"]),
        },
    )
    return game