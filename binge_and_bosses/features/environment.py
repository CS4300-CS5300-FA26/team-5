"""
    Behave hooks. Scenarios tagged @fake_igdb get fake IGDB answers, so they never call the real API.
    Steps read the fake games from context.fake_games (context.fake_game is the first one), and can
    change the answers through the mocks context.search_game and context.get_game_details.
"""
import copy
from unittest.mock import Mock, patch

FAKE_GAMES = [
    {
        "id": 1020,
        "name": "Grand Theft Auto V",
        "summary": "An open-world crime game.",
        "released": "2013-09-17",
        "rating": 4.47,
        "cover": "",
        "genres": ["Shooter", "Adventure"],
        "platforms": ["PC (Microsoft Windows)"],
    },
    {
        "id": 1561,
        "name": "Pokemon Red",
        "summary": "Explore Kanto and catch Pokemon.",
        "released": "1996-02-27",
        "rating": 4.2,
        "cover": "https://images.igdb.com/igdb/image/upload/t_cover_big/pokemon-red.jpg",
        "genres": ["Role-playing (RPG)", "Turn-based strategy (TBS)"],
        "platforms": ["Game Boy"],
    },
    {
        "id": 1511,
        "name": "Pokemon Blue",
        "summary": "Explore Kanto and catch Pokemon.",
        "released": "1996-02-27",
        "rating": 4.2,
        "cover": "https://images.igdb.com/igdb/image/upload/t_cover_big/pokemon-blue.jpg",
        "genres": ["Role-playing (RPG)", "Turn-based strategy (TBS)"],
        "platforms": ["Game Boy"],
    },
]


def before_scenario(context, scenario):
    if "fake_igdb" not in scenario.effective_tags:
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
    # Patch every place that imported an IGDB function
    for target, fake in [
        ("games.views.search_game", context.search_game),
        ("games.catalog.get_game_details", context.get_game_details),
    ]:
        patcher = patch(target, fake)
        patcher.start()
        context.add_cleanup(patcher.stop)
