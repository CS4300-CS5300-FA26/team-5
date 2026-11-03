from unittest.mock import patch

FAKE_GAME = {
    "id": 3498,
    "name": "Grand Theft Auto V",
    "description_raw": "An open-world crime game.",
    "rating": 4.47,
    "released": "2013-09-17",
    "background_image": "",
    "genres": [{"name": "Action"}],
    "platforms": [{"platform": {"name": "PC"}}],
}


def fake_get_game_details(game_id):
    return FAKE_GAME if int(game_id) == FAKE_GAME["id"] else None


def before_scenario(context, scenario):
    if "fake_rawg" not in scenario.effective_tags:
        return
    context.fake_game = FAKE_GAME
    # Patch both places that imported get_game_details
    for target in ("games.views.get_game_details", "games.catalog.get_game_details"):
        patcher = patch(target, side_effect=fake_get_game_details)
        patcher.start()
        context.add_cleanup(patcher.stop)