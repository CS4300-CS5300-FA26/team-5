from .models import Game
from .rawg_client import get_game_details


def get_or_import(rawg_id):
    """Return our Game for this RAWG id, saving it from RAWG the first time."""
    game = Game.objects.filter(rawg_id=rawg_id).first()
    if game:
        return game

    data = get_game_details(rawg_id)
    if data is None:
        return None

    game, _ = Game.objects.get_or_create(
        rawg_id=rawg_id,
        defaults={
            "game_title": data.get("name", ""),
            "game_description": data.get("description_raw") or "",
            "game_rating": data.get("rating") or 0,
            "game_release": data.get("released"),
            "game_image": data.get("background_image") or "",
            "game_genre": ", ".join(g["name"] for g in data.get("genres", [])),
        },
    )
    return game