"""Search by description: the model call, the IGDB lookup of the games it suggests, and the search page."""
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

# A cache of our own, so tests need no Redis and never clear the running app's cache
LOCAL_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
STARDEW = {"id": 17000, "name": "Stardew Valley", "first_release_date": 1456444800}         # 2016
GOW_2005 = {"id": 549, "name": "God of War", "first_release_date": 1111449600}              # 2005
GOW_2018 = {"id": 19560, "name": "God of War", "first_release_date": 1524182400}            # 2018
MAJORA = {"id": 1030, "name": "The Legend of Zelda: Majora's Mask", "first_release_date": 956275200}


@override_settings(CACHES=LOCAL_CACHE)
class FindTitlesTests(TestCase):
    """igdb_client.find_titles: one IGDB query finds the games the model suggested, in its order."""

    def setUp(self):
        patcher = patch("games.igdb_client._query")
        self.query = patcher.start()
        self.addCleanup(patcher.stop)

    def body(self):
        return self.query.call_args.args[0]

    def test_one_query_finds_every_title_in_the_suggested_order(self):
        self.query.return_value = [GOW_2018, STARDEW]

        games = igdb_client.find_titles([("Stardew Valley", 2016), ("God of War", 2018)])

        self.assertEqual(self.query.call_count, 1)
        self.assertIn('name ~ "Stardew Valley" | name ~ "God of War"', self.body())
        self.assertIn("version_parent = null", self.body())
        self.assertEqual([game["name"] for game in games], ["Stardew Valley", "God of War"])

    def test_titles_igdb_does_not_have_are_left_out(self):
        self.query.return_value = [STARDEW]

        games = igdb_client.find_titles([("Made Up Game", 2020), ("stardew valley", None)])

        self.assertEqual([game["id"] for game in games], [17000])

    def test_a_shared_title_picks_the_suggested_year_else_the_best_known(self):
        self.query.return_value = [GOW_2018, GOW_2005]   # IGDB sorts the best known first

        self.assertEqual(igdb_client.find_titles([("God of War", 2005)])[0]["id"], 549)
        self.assertEqual(igdb_client.find_titles([("God of War", 1999)])[0]["id"], 19560)

    def test_curly_quotes_match_and_quotes_cannot_end_the_string(self):
        self.query.return_value = [MAJORA]

        games = igdb_client.find_titles([("The Legend of Zelda: Majora’s Mask", 2000), ('Bad "Title\\', None)])

        self.assertIn('name ~ "The Legend of Zelda: Majora\'s Mask"', self.body())
        self.assertIn('name ~ "Bad \\"Title\\\\"', self.body())
        self.assertEqual([game["id"] for game in games], [1030])

    def test_a_game_suggested_twice_is_listed_once_and_at_most_ten_are_listed(self):
        rows = [{"id": i, "name": f"Game {i}"} for i in range(12)]
        self.query.return_value = rows

        games = igdb_client.find_titles([("Game 0", None)] + [(row["name"], None) for row in rows])

        self.assertEqual([game["id"] for game in games], list(range(10)))

    def test_no_titles_skips_igdb_and_failure_is_none(self):
        self.assertEqual(igdb_client.find_titles([]), [])
        self.query.assert_not_called()

        self.query.return_value = None
        self.assertIsNone(igdb_client.find_titles([("Stardew Valley", 2016)]))


@override_settings(OPENAI_API_KEY="test-key", OPENAI_MODEL="test-model", CACHES=LOCAL_CACHE)
class DescribeTests(TestCase):
    """describe.py: the model suggests games for a description, and IGDB confirms them."""

    def setUp(self):
        cache.clear()
        self.answer = {"looking_for": ["Farming", "Co-op"],
                       "games": [{"title": "Stardew Valley", "year": 2016}, {"title": "Fae Farm", "year": 2023}]}
        patcher = patch("games.describe.OpenAI")
        self.openai = patcher.start()
        self.addCleanup(patcher.stop)
        self.create = self.openai.return_value.responses.create
        self.create.side_effect = lambda **kwargs: Mock(output_text=json.dumps(self.answer))
        fake = patch("games.describe.igdb_client.find_titles", return_value=[{"id": 17000, "name": "Stardew Valley"}])
        self.find_titles = fake.start()
        self.addCleanup(fake.stop)

    def test_model_gets_the_description_with_a_strict_schema(self):
        describe.search_by_description("a cozy farming game")

        kwargs = self.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "test-model")
        self.assertEqual(kwargs["input"], "a cozy farming game")
        self.assertTrue(kwargs["text"]["format"]["strict"])
        self.assertEqual(sorted(kwargs["text"]["format"]["schema"]["required"]), ["games", "looking_for"])

    def test_suggested_games_are_looked_up_and_labelled(self):
        games, labels = describe.search_by_description("a cozy co-op farming game")

        self.find_titles.assert_called_once_with([("Stardew Valley", 2016), ("Fae Farm", 2023)])
        self.assertEqual(games, [{"id": 17000, "name": "Stardew Valley"}])
        self.assertEqual(labels, ["Farming", "Co-op"])

    def test_at_most_twelve_suggestions_and_four_labels(self):
        self.answer = {"looking_for": list("abcdef"), "games": [{"title": f"G{i}", "year": None} for i in range(20)]}

        _, labels = describe.search_by_description("anything")

        self.assertEqual(len(self.find_titles.call_args.args[0]), 12)
        self.assertEqual(labels, list("abcd"))

    def test_the_same_description_is_answered_from_the_cache(self):
        describe.search_by_description("a cozy farming game")
        describe.search_by_description("A cozy farming game ")

        self.assertEqual(self.create.call_count, 1)

    def test_failures_return_none(self):
        self.create.side_effect = openai.APIConnectionError(request=Mock())
        self.assertIsNone(describe.search_by_description("a farming game"))

        self.create.side_effect = lambda **kwargs: Mock(output_text="not json")
        self.assertIsNone(describe.search_by_description("a farming game"))

        self.create.side_effect = lambda **kwargs: Mock(output_text=json.dumps(self.answer))
        self.find_titles.return_value = None
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
        link = page.select_one("article h2 a")["href"]
        self.assertIn("mode=describe", link)

    def test_title_mode_does_not_call_the_model(self, mock_describe):
        with patch("games.views.search_game", return_value=[]):
            page = self.page(query="Stardew", mode="title")

        mock_describe.assert_not_called()
        self.assertEqual(page.select_one('.search-tabs [aria-current="page"]').get_text(strip=True), "Titles")

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

    def test_tabs_switch_the_same_query_between_titles_and_ai(self, mock_describe):
        mock_describe.return_value = (self.RESULTS, [])

        tabs = self.page(query="zelda but darker").select(".search-tabs a")

        self.assertEqual([tab.get_text(strip=True) for tab in tabs], ["Titles", "AI picks"])
        self.assertEqual(tabs[0]["href"], "?q=zelda%20but%20darker")
        self.assertEqual(tabs[1]["href"], "?q=zelda%20but%20darker&mode=describe")
        self.assertEqual(tabs[1]["aria-current"], "page")
        self.assertFalse(tabs[0].has_attr("aria-current"))

    def test_details_back_link_returns_to_the_description_search(self, mock_describe):
        with patch("games.catalog.get_game_details", return_value=None):
            response = self.client.get(reverse("game_details", args=[17000]), {"q": "farming", "mode": "describe"})

        self.assertRedirects(response, reverse("game_search", query={"q": "farming", "mode": "describe"}),
                             fetch_redirect_response=False)
