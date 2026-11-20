"""Search by description: the IGDB queries it adds, the model call, and the search page in describe mode."""
import json
from unittest.mock import Mock, patch

import openai
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from . import describe, igdb_client
from .models import Catalog, Game

VOCABULARY = {
    "genres": {"Role-playing (RPG)": 12, "Simulator": 13, "Strategy": 15},
    "themes": {"Fantasy": 17, "Horror": 19},
    "game_modes": {"Single player": 1, "Co-operative": 3},
    "platforms": {"Nintendo Switch": 130, "PC (Microsoft Windows)": 6},
}
NOTHING_WANTED = {
    "genres": [], "themes": [], "game_modes": [], "platforms": [],
    "like_title": None, "released_after": None, "released_before": None,
}
NO_FILTERS = {"genres": [], "themes": [], "game_modes": [], "platforms": [],
              "ids": None, "released_after": None, "released_before": None}
# A cache of our own, so tests need no Redis and never clear the running app's cache
LOCAL_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
STARDEW = {"id": 17000, "name": "Stardew Valley", "first_release_date": 1456444800}


@override_settings(CACHES=LOCAL_CACHE)
class IgdbDescribeQueryTests(TestCase):
    """igdb_client.py: the vocabulary, similar games and filtered queries that search by description uses."""

    def setUp(self):
        cache.clear()
        patcher = patch("games.igdb_client._query", side_effect=self.fake_query)
        self.query = patcher.start()
        self.addCleanup(patcher.stop)
        self.answers = {}

    def fake_query(self, body, endpoint="games"):
        return self.answers[endpoint].pop(0)   # each endpoint answers from its own list, in order

    def bodies(self):
        return [c.args[0] for c in self.query.call_args_list]

    def test_vocabulary_maps_igdb_names_to_ids_and_is_cached(self):
        self.answers = {"genres": [[{"id": 12, "name": "Role-playing (RPG)"}]],
                        "themes": [[{"id": 17, "name": "Fantasy"}]],
                        "game_modes": [[{"id": 3, "name": "Co-operative"}]],
                        "platforms": [[{"id": 130, "name": "Nintendo Switch"}]]}

        first = igdb_client.vocabulary()
        second = igdb_client.vocabulary()

        self.assertEqual(first["genres"], {"Role-playing (RPG)": 12})
        self.assertEqual(first["platforms"], {"Nintendo Switch": 130})
        self.assertEqual(second, first)
        self.assertEqual(self.query.call_count, 4)

    def test_vocabulary_is_none_when_igdb_fails(self):
        self.query.side_effect = lambda body, endpoint="games": None

        self.assertIsNone(igdb_client.vocabulary())

    def test_similar_games_uses_the_best_known_match(self):
        with patch("games.igdb_client.search_game", return_value=[{"id": 17000}, {"id": 5}]):
            self.answers = {"games": [[{"id": 17000, "similar_games": [1, 2, 3]}]]}

            self.assertEqual(igdb_client.similar_games("Stardew Valley"), [1, 2, 3])
        self.assertIn("where id = 17000;", self.bodies()[0])

    def test_similar_games_is_empty_for_an_unknown_title_and_none_on_failure(self):
        with patch("games.igdb_client.search_game", return_value=[]):
            self.assertEqual(igdb_client.similar_games("no such game"), [])
        with patch("games.igdb_client.search_game", return_value=None):
            self.assertIsNone(igdb_client.similar_games("Stardew Valley"))

    def test_find_games_needs_every_genre_and_any_platform(self):
        self.answers = {"games": [[STARDEW]]}

        games = igdb_client.find_games({"genres": [13, 12], "themes": [], "game_modes": [3], "platforms": [130, 6],
                                        "ids": [17000, 4], "released_after": 2016, "released_before": 2016})

        body = self.bodies()[0]
        self.assertIn("genres = [13,12]", body)
        self.assertIn("game_modes = [3]", body)
        self.assertIn("platforms = (130,6)", body)
        self.assertIn("id = (17000,4)", body)
        self.assertIn("first_release_date >= 1451606400", body)   # 2016-01-01 UTC
        self.assertIn("first_release_date < 1483228800", body)    # 2017-01-01 UTC
        self.assertIn("version_parent = null", body)
        self.assertIn("sort total_rating_count desc;", body)
        self.assertNotIn("themes", body)
        self.assertEqual([game["name"] for game in games], ["Stardew Valley"])

    def test_find_games_accepts_any_genre_when_no_game_has_all_of_them(self):
        self.answers = {"games": [[], [STARDEW]]}

        games = igdb_client.find_games({**NO_FILTERS, "genres": [13, 12]})

        self.assertIn("genres = (13,12)", self.bodies()[1])
        self.assertEqual([game["name"] for game in games], ["Stardew Valley"])

    def test_find_games_is_none_when_igdb_fails(self):
        self.answers = {"games": [None]}

        self.assertIsNone(igdb_client.find_games({**NO_FILTERS, "genres": [13]}))


@override_settings(OPENAI_API_KEY="test-key", OPENAI_MODEL="test-model", CACHES=LOCAL_CACHE)
class DescribeTests(TestCase):
    """describe.py: the model turns a description into IGDB names, and the code turns those into a search."""

    def setUp(self):
        cache.clear()
        self.wanted = {**NOTHING_WANTED, "genres": ["Simulator"], "platforms": ["Nintendo Switch"]}
        patcher = patch("games.describe.OpenAI")
        self.openai = patcher.start()
        self.addCleanup(patcher.stop)
        self.create = self.openai.return_value.responses.create
        self.create.side_effect = lambda **kwargs: Mock(output_text=json.dumps(self.wanted))
        for name, value in [("vocabulary", VOCABULARY), ("find_games", [{"id": 17000, "name": "Stardew Valley"}]),
                            ("similar_games", [17000, 4])]:
            fake = patch(f"games.describe.igdb_client.{name}", return_value=value)
            setattr(self, name, fake.start())
            self.addCleanup(fake.stop)

    def test_model_gets_the_description_and_only_igdb_names_to_choose_from(self):
        describe.search_by_description("a cozy farming game")

        kwargs = self.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "test-model")
        self.assertEqual(kwargs["input"], "a cozy farming game")
        schema = kwargs["text"]["format"]["schema"]
        allowed = {kind: schema["properties"][kind]["items"]["enum"] for kind in ("genres", "platforms")}
        self.assertTrue(kwargs["text"]["format"]["strict"])
        self.assertEqual(allowed["genres"], ["Role-playing (RPG)", "Simulator", "Strategy"])
        self.assertEqual(allowed["platforms"], ["Nintendo Switch", "PC (Microsoft Windows)"])
        self.assertEqual(sorted(schema["required"]), sorted(NOTHING_WANTED))

    def test_names_become_ids_and_labels(self):
        games, labels = describe.search_by_description("a cozy farming game on Switch")

        filters = self.find_games.call_args.args[0]
        self.assertEqual(filters["genres"], [13])
        self.assertEqual(filters["platforms"], [130])
        self.assertIsNone(filters["ids"])
        self.assertEqual(games, [{"id": 17000, "name": "Stardew Valley"}])
        self.assertEqual(labels, ["Simulator", "Nintendo Switch"])

    def test_a_named_game_limits_results_to_similar_games(self):
        self.wanted.update(like_title="Stardew Valley", released_after=2018, released_before=2020)

        _, labels = describe.search_by_description("like Stardew Valley but newer")

        self.similar_games.assert_called_once_with("Stardew Valley")
        filters = self.find_games.call_args.args[0]
        self.assertEqual(filters["ids"], [17000, 4])
        self.assertEqual((filters["released_after"], filters["released_before"]), (2018, 2020))
        self.assertIn("Like Stardew Valley", labels)
        self.assertIn("2018–2020", labels)

    def test_a_named_game_without_similar_games_is_ignored(self):
        self.wanted["like_title"] = "Obscure Game"
        self.similar_games.return_value = []

        describe.search_by_description("like Obscure Game")

        self.assertIsNone(self.find_games.call_args.args[0]["ids"])

    def test_names_igdb_does_not_know_are_dropped(self):
        self.wanted["genres"] = ["Simulator", "Made up"]

        _, labels = describe.search_by_description("a farming game")

        self.assertEqual(self.find_games.call_args.args[0]["genres"], [13])
        self.assertNotIn("Made up", labels)

    def test_a_description_with_nothing_to_search_for_finds_nothing(self):
        self.wanted = dict(NOTHING_WANTED)

        self.assertEqual(describe.search_by_description("hello"), ([], []))
        self.find_games.assert_not_called()

    def test_the_same_description_is_answered_from_the_cache(self):
        describe.search_by_description("a cozy farming game")
        describe.search_by_description("A cozy farming game ")

        self.assertEqual(self.create.call_count, 1)

    def test_failures_return_none(self):
        self.create.side_effect = openai.APIConnectionError(request=Mock())
        self.assertIsNone(describe.search_by_description("a farming game"))

        self.create.side_effect = lambda **kwargs: Mock(output_text="not json")
        self.assertIsNone(describe.search_by_description("a farming game"))

        self.create.side_effect = lambda **kwargs: Mock(output_text=json.dumps(self.wanted))
        self.vocabulary.return_value = None
        self.assertIsNone(describe.search_by_description("a farming game"))

    @override_settings(OPENAI_API_KEY="")
    def test_without_an_api_key_nothing_is_sent(self):
        self.assertIsNone(describe.search_by_description("a farming game"))
        self.openai.assert_not_called()


@patch("games.views.search_by_description")
class DescribeSearchPageTests(TestCase):
    """The search page in describe mode: results, what the search looked for, and links that keep the mode."""

    RESULTS = [{"id": 17000, "name": "Stardew Valley", "released": "2016-02-26", "cover": ""}]

    def page(self, query="a cozy farming game", mode="describe"):
        response = self.client.get(reverse("game_search"), {"q": query, "mode": mode})
        self.assertEqual(response.status_code, 200)
        return BeautifulSoup(response.content, "html.parser").select_one("main")

    def test_results_and_what_the_search_looked_for(self, mock_describe):
        mock_describe.return_value = (self.RESULTS, ["Simulator", "Nintendo Switch"])

        page = self.page()

        mock_describe.assert_called_once_with("a cozy farming game")
        self.assertIn("Stardew Valley", page.select_one("article").get_text())
        self.assertEqual([pill.get_text() for pill in page.select(".search-wanted .pill")],
                         ["Simulator", "Nintendo Switch"])
        self.assertTrue(page.select_one('input[name="mode"][value="describe"]').has_attr("checked"))
        link = page.select_one("article h2 a")["href"]
        self.assertIn("mode=describe", link)

    def test_title_mode_does_not_call_the_model(self, mock_describe):
        with patch("games.views.search_game", return_value=[]):
            page = self.page(query="Stardew", mode="title")

        mock_describe.assert_not_called()
        self.assertTrue(page.select_one('input[name="mode"][value="title"]').has_attr("checked"))

    def test_failure_shows_the_error(self, mock_describe):
        mock_describe.return_value = None

        self.assertIn("Could not load games. Try again.", self.page().select_one('[role="alert"]').get_text())

    def test_title_results_are_not_shown_for_a_failed_description(self, mock_describe):
        with patch("games.views.search_game", return_value=self.RESULTS):
            self.page(query="Stardew", mode="title")
        mock_describe.return_value = None

        self.assertIsNone(self.page(query="Stardew").select_one("article"))

    def test_owned_games_are_marked(self, mock_describe):
        mock_describe.return_value = (self.RESULTS, [])
        user = get_user_model().objects.create_user(username="p1", email="p1@example.com", password="Gr8Backlog!42")
        game = Game.objects.create(igdb_id=17000, game_title="Stardew Valley", game_description="", game_rating=4.0)
        Catalog.objects.create(user=user, games=game)
        self.client.force_login(user)

        self.assertIn("In library", self.page().select_one("article").get_text())

    def test_details_back_link_returns_to_the_description_search(self, mock_describe):
        with patch("games.catalog.get_game_details", return_value=None):
            response = self.client.get(reverse("game_details", args=[17000]), {"q": "farming", "mode": "describe"})

        self.assertRedirects(response, reverse("game_search", query={"q": "farming", "mode": "describe"}),
                             fetch_redirect_response=False)
