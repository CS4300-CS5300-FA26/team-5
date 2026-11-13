"""
    Behave hooks. Scenarios tagged @fake_rawg get fake RAWG answers, so they never call the real API.
    Steps read the fake games from context.fake_games (context.fake_game is the first one), and can
    change the answers through the mocks context.search_game and context.get_game_details.
"""
import copy
from unittest.mock import Mock, patch

FAKE_GAMES = [
    {
        "id": 3498,
        "name": "Grand Theft Auto V",
        "description_raw": "An open-world crime game.",
        "rating": 4.47,
        "released": "2013-09-17",
        "background_image": "",
        "genres": [{"name": "Action"}],
        "platforms": [{"platform": {"name": "PC"}}],
    },
    {
        "id": 1,
        "name": "Pokemon Red",
        "description_raw": "Explore Kanto and catch Pokemon.",
        "rating": 4.2,
        "released": "1996-02-27",
        "background_image": "https://example.com/pokemon-red.jpg",
        "genres": [{"name": "Adventure"}, {"name": "RPG"}],
        "platforms": [{"platform": {"name": "Game Boy"}}],
    },
    {
        "id": 2,
        "name": "Pokemon Blue",
        "description_raw": "Explore Kanto and catch Pokemon.",
        "rating": 4.2,
        "released": "1996-02-27",
        "background_image": "https://example.com/pokemon-blue.jpg",
        "genres": [{"name": "Adventure"}, {"name": "RPG"}],
        "platforms": [{"platform": {"name": "Game Boy"}}],
    },
]


def before_scenario(context, scenario):
    if "fake_rawg" not in scenario.effective_tags:
        return
    # A copy per scenario, so a step that edits a game can't leak into the next scenario
    context.fake_games = copy.deepcopy(FAKE_GAMES)
    context.fake_game = context.fake_games[0]

    def search(query):
        return [game for game in context.fake_games if query.lower() in game["name"].lower()]

    def details(game_id):
        return next((game for game in context.fake_games if game["id"] == int(game_id)), None)

    context.search_game = Mock(side_effect=search)
    context.get_game_details = Mock(side_effect=details)
    # Patch every place that imported a RAWG function
    for target, fake in [
        ("games.views.search_game", context.search_game),
        ("games.catalog.get_game_details", context.get_game_details),
    ]:
        patcher = patch(target, fake)
        patcher.start()
        context.add_cleanup(patcher.stop)
