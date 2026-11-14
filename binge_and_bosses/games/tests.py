from datetime import date

from bs4 import BeautifulSoup
from django.contrib import messages
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Game, Catalog
from .catalog import get_or_import
from .forms import ReviewForm

from unittest.mock import patch,Mock
import requests
from django.conf import settings
from django.core.cache import cache

from . import igdb_client
from django.urls import reverse

from django.contrib.auth import get_user_model


# Tests for the landing page (URL "/" -> index view -> games/index.html).
class LandingPageTests(TestCase):

    def links(self, response, scope="main"):
        page = BeautifulSoup(response.content, "html.parser").select_one(scope)
        return {a.get_text(" ", strip=True): a["href"] for a in page.select("a[href]")}

    def test_visitor_sees_what_the_app_is_for(self):
        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "One save file for")
        self.assertContains(response, "Find it")
        self.assertContains(response, "Rate it")
        self.assertContains(response, "Example library")

    def test_visitor_gets_sign_up_and_log_in_links(self):
        links = self.links(self.client.get(reverse("index")))

        self.assertEqual(links["Sign up"], reverse("signup"))
        self.assertEqual(links["Log in"], reverse("login"))

    def test_example_games_show_their_igdb_covers(self):
        page = BeautifulSoup(self.client.get(reverse("index")).content, "html.parser")
        covers = [img["src"] for img in page.select("main img.cover")]

        self.assertEqual(covers, [
            "https://images.igdb.com/igdb/image/upload/t_cover_big/coaknx.jpg",   # Hades II
            "https://images.igdb.com/igdb/image/upload/t_cover_big/co9gam.jpg",   # Clair Obscur: Expedition 33
            "https://images.igdb.com/igdb/image/upload/t_cover_big/cobebu.jpg",   # Hollow Knight: Silksong
        ])
        self.assertIn("IGDB", page.select_one("main").get_text())

    def test_demos_use_the_play_statuses_from_story_12(self):
        page = BeautifulSoup(self.client.get(reverse("index")).content, "html.parser")
        pills = [pill.get_text() for pill in page.select(".landing-steps .pills .pill")]
        legend = [dt.get_text() for dt in page.select(".landing-hero .legend dt")]

        statuses = ["Not Started", "Playing", "Completed", "On Hold", "Dropped"]
        self.assertEqual(pills, statuses)
        self.assertEqual(sorted(legend), sorted(statuses))
        self.assertNotIn("Finished", page.get_text())

    def test_visitor_is_asked_to_sign_up_only_once_on_the_page(self):
        page = BeautifulSoup(self.client.get(reverse("index")).content, "html.parser")
        sign_up_links = page.select(f'main a[href="{reverse("signup")}"]')

        self.assertEqual(len(sign_up_links), 1)

    def test_player_gets_library_and_search_links_and_no_sign_up(self):
        user = get_user_model().objects.create_user(
            username="player_one", email="player@example.com", password="Gr8Backlog!42"
        )
        self.client.force_login(user)

        response = self.client.get(reverse("index"))
        page = BeautifulSoup(response.content, "html.parser")

        # The nav bar's Library link counts: an empty library has no library card on the page
        self.assertIn(reverse("library"), self.links(response, "body").values())
        self.assertIsNotNone(page.select_one(f'main form[action="{reverse("game_search")}"]'))
        self.assertNotIn(reverse("signup"), self.links(response, "body").values())

    def test_page_loads_its_stylesheet(self):
        response = self.client.get(reverse("index"))

        self.assertContains(response, "games/css/landing.css")
        self.assertIsNotNone(finders.find("games/css/landing.css"))


class PlayerHomeTests(TestCase):
    """Logged-in players get a working home page: search, library stats, popular games, recent adds."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="player_one", email="player@example.com", password="Gr8Backlog!42"
        )
        self.client.force_login(self.user)
        self.next_igdb_id = 1

    def add(self, title, user=None, **entry):
        game = Game.objects.create(
            igdb_id=self.next_igdb_id, game_title=title, game_description="", game_rating=4.0,
            game_image=f"https://media.example.com/{title}.jpg",
        )
        self.next_igdb_id += 1
        return Catalog.objects.create(user=user or self.user, games=game, **entry)

    def page(self):
        return BeautifulSoup(self.client.get(reverse("index")).content, "html.parser").select_one("main")

    def titles(self, section):
        return [a.get_text(" ", strip=True) for a in self.page().select(f"{section} li a")]

    def test_player_home_skips_the_pitch_and_the_steps(self):
        text = self.page().get_text(" ", strip=True)

        self.assertIn("Welcome back, player_one", text)
        self.assertNotIn("One save file for", text)
        self.assertNotIn("Find it", text)

    def test_player_home_has_a_search_box(self):
        form = self.page().select_one(f'form[action="{reverse("game_search")}"]')

        self.assertEqual(form["method"], "get")
        self.assertIsNotNone(form.select_one('input[name="q"]'))

    def test_library_card_shows_counts_ratings_and_reviews(self):
        self.add("Hades II", rating=5, review="Best one yet.")
        self.add("Balatro", rating=4)
        self.add("Celeste")

        text = self.page().select_one(".home-library").get_text(" ", strip=True)

        self.assertIn("3 games", text)
        self.assertIn("Not Started 3", text)
        self.assertIn("2 rated", text)
        self.assertIn("1 review", text)

    def player(self, name):
        return get_user_model().objects.create_user(username=name, email=f"{name}@example.com")

    def test_popular_lists_what_other_players_have_that_you_dont(self):
        ana, ben, cy = self.player("ana"), self.player("ben"), self.player("cy")
        balatro = self.add("Balatro", user=ana).games
        hades = self.add("Hades II", user=ana).games
        celeste = self.add("Celeste", user=ana).games
        self.add("Elden Ring", user=ana)
        self.add("Stardew Valley", user=ben)
        for player in (ben, cy):
            Catalog.objects.create(user=player, games=balatro)
        for player in (ben, cy, self.user):   # the most popular, but you already have it
            Catalog.objects.create(user=player, games=celeste)
        Catalog.objects.create(user=ben, games=hades)

        rows = self.page().select(".home-popular li a")

        # Most players first; a tie goes to the game someone added most recently
        self.assertEqual(
            [a.get_text(" ", strip=True) for a in rows],
            ["Balatro 3 players", "Hades II 2 players", "Stardew Valley 1 player"],
        )
        self.assertEqual(rows[0]["href"], reverse("game_details", args=[balatro.igdb_id]))

    def test_popular_skips_games_without_an_id_to_link_to(self):
        self.add("Hades II")   # the cards only show once your library has a game
        ana = self.player("ana")
        orphan = self.add("Saved by hand", user=ana).games   # e.g. added in the admin without an id
        orphan.igdb_id = None
        orphan.save()

        page = self.page()

        self.assertNotIn("Saved by hand", page.select_one(".home-popular").get_text())

    def test_popular_says_when_there_is_nothing_to_suggest(self):
        self.add("Hades II")

        card = self.page().select_one(".home-popular")

        self.assertIn("Nothing to suggest yet", card.get_text())
        self.assertEqual(card.select_one("a")["href"], reverse("game_search"))

    def test_recently_added_shows_the_six_newest_with_covers(self):
        for n in range(1, 8):
            self.add(f"Game {n}")

        items = self.page().select(".home-recent li")

        self.assertEqual([li.get_text(strip=True) for li in items], [f"Game {n}" for n in range(7, 1, -1)])
        self.assertEqual(items[0].select_one("img.cover")["src"], "https://media.example.com/Game 7.jpg")
        self.assertEqual(items[0].select_one("a")["href"], reverse("game_details", args=[7]))

    def test_library_stats_and_recent_adds_count_only_the_players_own_games(self):
        other = get_user_model().objects.create_user(username="someone_else", password="Gr8Backlog!42")
        self.add("Hades II")
        self.add("Balatro", user=other)

        page = self.page()

        self.assertIn("1 game", page.select_one(".home-library .hud").get_text())
        self.assertNotIn("Balatro", page.select_one(".home-recent").get_text())
        self.assertIn("Balatro", page.select_one(".home-popular").get_text())   # suggested, not counted

    def test_empty_library_points_to_search(self):
        page = self.page()

        self.assertIn("Your library is empty", page.get_text())
        self.assertIsNone(page.select_one(".home-library"))


# Dark mode: base.html gives every page a toggle and loads the script that applies the theme.
class DarkModeToggleTests(TestCase):

    def test_every_page_has_a_dark_mode_toggle(self):
        for url in (reverse("index"), reverse("login"), reverse("signup")):
            with self.subTest(url=url):
                page = BeautifulSoup(self.client.get(url).content, "html.parser")
                toggle = page.select_one("nav button#theme-toggle")

                self.assertIsNotNone(toggle)
                self.assertEqual(toggle["aria-label"], "Dark mode")
                self.assertIsNotNone(page.select_one('head script[src$="js/theme.js"]'))

    def test_theme_script_exists(self):
        self.assertIsNotNone(finders.find("js/theme.js"))


class BrandLogoTests(TestCase):

    def test_every_page_shows_the_logo_beside_the_app_name(self):
        for url in (reverse("index"), reverse("login"), reverse("signup")):
            with self.subTest(url=url):
                page = BeautifulSoup(self.client.get(url).content, "html.parser")
                brand = page.select_one("nav a.navbar-brand")
                logo = brand.select_one(".brand-logo")

                self.assertIsNotNone(logo)
                self.assertEqual(logo["aria-hidden"], "true")
                self.assertEqual(brand.get_text(strip=True), "Binge and Bosses")


class IgdbClientTests(TestCase):
    """games/igdb_client.py: gets a Twitch token, queries IGDB and returns games in our own shape."""

    HOLLOW_KNIGHT = {
        "id": 14593,
        "name": "Hollow Knight",
        "summary": "Forge your own path in Hollow Knight!",
        "first_release_date": 1487894400,   # 2017-02-24 UTC
        "total_rating": 92.4,
        "cover": {"id": 1, "image_id": "cobfzp"},
        "genres": [{"id": 8, "name": "Platform"}, {"id": 31, "name": "Adventure"}],
        "platforms": [{"id": 6, "name": "PC (Microsoft Windows)"}, {"id": 130, "name": "Nintendo Switch"}],
    }

    def setUp(self):
        cache.clear()
        patcher = patch("games.igdb_client.requests.post", side_effect=self.fake_post)
        self.post = patcher.start()
        self.addCleanup(patcher.stop)
        self.games = [self.HOLLOW_KNIGHT]
        self.api_status = 200
        self.tokens_issued = 0

    def fake_post(self, url, **kwargs):
        response = Mock()
        if url == igdb_client.TOKEN_URL:
            self.tokens_issued += 1
            response.status_code = 200
            response.json.return_value = {"access_token": f"token-{self.tokens_issued}", "expires_in": 5000000}
        else:
            response.status_code = self.api_status
            response.json.return_value = self.games
            if self.api_status == 401:
                self.api_status = 200   # the next try, with a new token, works
        response.raise_for_status.side_effect = (
            None if response.status_code < 400 else requests.HTTPError(str(response.status_code))
        )
        return response

    def api_calls(self):
        return [c for c in self.post.call_args_list if c.args[0] == igdb_client.API_URL]

    def test_search_returns_games_in_our_shape(self):
        games = igdb_client.search_game("hollow knight")

        self.assertEqual(games, [{
            "id": 14593,
            "name": "Hollow Knight",
            "summary": "Forge your own path in Hollow Knight!",
            "released": "2017-02-24",
            "rating": 4.62,
            "cover": "https://images.igdb.com/igdb/image/upload/t_cover_big/cobfzp.jpg",
            "genres": ["Platform", "Adventure"],
            "platforms": ["PC (Microsoft Windows)", "Nintendo Switch"],
        }])

    def test_search_sends_the_title_credentials_and_release_filter(self):
        igdb_client.search_game("hollow knight")

        call = self.api_calls()[0]
        self.assertIn('search "hollow knight";', call.kwargs["data"])
        self.assertIn("version_parent = null", call.kwargs["data"])
        self.assertEqual(call.kwargs["headers"]["Client-ID"], settings.IGDB_CLIENT_ID)
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer token-1")

    def test_search_escapes_quotes_in_the_title(self):
        igdb_client.search_game('say "hi" \\o/')

        self.assertIn('search "say \\"hi\\" \\\\o/";', self.api_calls()[0].kwargs["data"])

    def test_search_puts_the_most_rated_matches_first_and_keeps_five(self):
        # IGDB ranks by text match only, so a fan game can come before the real one
        counts = [0, 2348, 111, None, 5, 40, 0]
        self.games = [{"id": i, "name": f"Game {i}", "total_rating_count": n} for i, n in enumerate(counts)]
        del self.games[3]["total_rating_count"]

        games = igdb_client.search_game("game")

        self.assertEqual([g["id"] for g in games], [1, 2, 5, 4, 0])
        self.assertIn("limit 20;", self.api_calls()[0].kwargs["data"])

    def test_missing_fields_get_empty_values(self):
        self.games = [{"id": 1, "name": "Mystery"}]

        self.assertEqual(igdb_client.search_game("mystery"), [{
            "id": 1, "name": "Mystery", "summary": "", "released": None, "rating": None,
            "cover": "", "genres": [], "platforms": [],
        }])

    def test_token_is_reused_until_it_expires(self):
        igdb_client.search_game("hollow knight")
        igdb_client.get_game_details(14593)

        self.assertEqual(self.tokens_issued, 1)
        self.assertEqual(len(self.api_calls()), 2)

    def test_rejected_token_is_replaced_once(self):
        igdb_client.search_game("hollow knight")
        self.api_status = 401

        games = igdb_client.search_game("hollow knight")

        self.assertEqual(games[0]["name"], "Hollow Knight")
        self.assertEqual(self.tokens_issued, 2)
        self.assertEqual(self.api_calls()[-1].kwargs["headers"]["Authorization"], "Bearer token-2")

    def test_search_returns_none_when_igdb_fails(self):
        self.api_status = 500

        self.assertIsNone(igdb_client.search_game("hollow knight"))

    def test_search_returns_none_when_the_network_fails(self):
        self.post.side_effect = requests.ConnectionError("down")

        self.assertIsNone(igdb_client.search_game("hollow knight"))

    def test_details_asks_for_one_game_by_id(self):
        game = igdb_client.get_game_details(14593)

        self.assertEqual(game["name"], "Hollow Knight")
        self.assertIn("where id = 14593;", self.api_calls()[0].kwargs["data"])

    def test_details_for_an_unknown_id_is_none(self):
        self.games = []

        self.assertIsNone(igdb_client.get_game_details(999999999))


class GameSearchandDetailsViewTests(TestCase):

    @patch('games.views.search_game')
    def test_game_search_view(self,mock_search_game):

        mock_search_game.return_value = [
            {'id': 1, 'name': 'Minecraft', 'cover': '', 'released': None},
            {'id': 2, 'name': 'Minecraft Pocket Edition', 'cover': '', 'released': None}
        ]

        response = self.client.get('/search/?q=Minecraft')

        self.assertEqual(response.status_code,200)

        mock_search_game.assert_called_once_with("Minecraft")

        self.assertContains(response,"Minecraft")
        self.assertContains(response,"Minecraft Pocket Edition")

    @patch('games.views.search_game')
    def test_search_api_failure(self, mock_search_game):
        mock_search_game.return_value = None

        response = self.client.get('/search/?q=Minecraft')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['error'])
        self.assertEqual(response.context['games'], [])

    @patch('games.views.search_game')
    def test_search_failure_shows_last_results_for_same_query(self, mock_search_game):
        mock_search_game.return_value = [
            {'id': 1, 'name': 'Minecraft', 'cover': 'https://example.com/m.jpg', 'released': None},
        ]
        self.client.get('/search/?q=Minecraft')
        mock_search_game.return_value = None

        response = self.client.get('/search/?q=Minecraft')

        self.assertFalse(response.context['error'])
        self.assertContains(response, 'Minecraft')
        self.assertContains(response, 'https://example.com/m.jpg')

        response = self.client.get('/search/?q=Zelda')

        self.assertTrue(response.context['error'])
        self.assertEqual(response.context['games'], [])

    @patch('games.views.search_game')
    def test_search_links_preserve_encoded_query(self, mock_search_game):
        mock_search_game.return_value = [{'id': 1, 'name': 'Pokemon Red', 'cover': '', 'released': None}]

        response = self.client.get(reverse('game_search'), {'q': 'Pokémon & Red/Blue'})

        self.assertContains(
            response, 'href="/1/?q=Pok%C3%A9mon%20%26%20Red%2FBlue"'
        )

    @patch('games.catalog.get_game_details')
    def test_game_details_view_for_new_games_not_in_database(self,mock_search_game_detail):

        mock_search_game_detail.return_value = {
            'id':1,
            'name':'Minecraft',
            'summary':'',
            'rating':None,
            'cover':'',
            'released':'2011-11-18',
            'genres': ['Action', 'Adventure'],
            'platforms': ['PC (Microsoft Windows)'],
        }

        response = self.client.get('/1/')

        self.assertEqual(response.status_code,200)

        mock_search_game_detail.assert_called_once_with(1)

        self.assertContains(response,"Minecraft")
        self.assertTrue(Game.objects.filter(igdb_id=1).exists())
        self.assertContains(response,'Nov 18, 2011')
        self.assertContains(response, 'Action, Adventure')
        self.assertContains(response, 'PC (Microsoft Windows)')

    @patch('games.catalog.get_game_details')
    def test_game_details_view_when_game_is_in_database(self,mock_details):

        Game.objects.create(
        igdb_id=1, game_title="Minecraft", game_description="Build things.",
        game_rating=4.5, game_genre="Sandbox", game_platforms="PC",
        )

        response = self.client.get(reverse('game_details', args=[1]))

        mock_details.assert_not_called()
        self.assertContains(response, "Minecraft")
        self.assertContains(response, "Build things.")
        self.assertContains(response, "Sandbox")
        self.assertContains(response, "PC")

    @patch('games.catalog.get_game_details')
    def test_details_api_failure(self, mock_get_game_details):

        mock_get_game_details.return_value = None

        response = self.client.get('/1/')

        self.assertEqual(response.status_code, 200)

        mock_get_game_details.assert_called_once_with(1)

        self.assertTrue(response.context['error'])
        self.assertIsNone(response.context['game'])
        self.assertContains(response, 'Could not load game details. Try again.')

    @patch('games.views.search_game')
    @patch('games.catalog.get_game_details')
    def test_details_failure_returns_to_search_with_message(self, mock_details, mock_search):
        mock_details.return_value = None
        mock_search.return_value = [{'id': 1, 'name': 'Pokemon Red', 'cover': '', 'released': None}]

        response = self.client.get(
            reverse('game_details', args=[1]), {'q': 'Pokémon & Red/Blue'}, follow=True
        )

        self.assertRedirects(response, '/search/?q=Pok%C3%A9mon%20%26%20Red%2FBlue')
        self.assertContains(response, 'Could not load game details. Try again.')
        self.assertContains(response, 'Pokemon Red')
        shown_messages = list(response.context['messages'])
        self.assertEqual(len(shown_messages), 1)
        self.assertEqual(shown_messages[0].level, messages.ERROR)
        mock_search.assert_called_once_with('Pokémon & Red/Blue')

    @patch('games.catalog.get_game_details')
    def test_missing_cover_uses_placeholder(self, mock_details):
        mock_details.return_value = {
            'id': 1, 'name': 'Pokemon Red', 'summary': '', 'rating': None, 'cover': '',
            'released': None, 'genres': [], 'platforms': [],
        }

        response = self.client.get(reverse('game_details', args=[1]))

        page = BeautifulSoup(response.content, 'html.parser')
        self.assertIsNotNone(page.find('img', attrs={
            'src': '/static/games/cover-placeholder.svg',
            'alt': 'No cover available',
        }))
        self.assertContains(response, 'No description available')
        self.assertIsNotNone(finders.find('games/cover-placeholder.svg'))



@patch("games.views.search_game")
class SearchPageTests(TestCase):
    """The search page: a labelled search box, result cards with year and cover, and what's already owned."""

    RESULTS = [
        {"id": 1, "name": "Celeste", "released": "2018-01-25", "cover": "https://media.example.com/c.jpg"},
        {"id": 2, "name": "Celeste Classic", "released": None, "cover": ""},
    ]

    def page(self, query="Celeste"):
        response = self.client.get(reverse("game_search"), {"q": query} if query else {})
        self.assertEqual(response.status_code, 200)
        return BeautifulSoup(response.content, "html.parser").select_one("main")

    def cards(self, page):
        return {card.h2.get_text(strip=True): card for card in page.select("article")}

    def test_search_box_is_labelled_and_keeps_the_query(self, mock_search):
        mock_search.return_value = self.RESULTS

        box = self.page().select_one('form[role="search"] input[name="q"]')

        self.assertEqual(box["value"], "Celeste")
        self.assertIsNotNone(self.page().find("label", attrs={"for": box["id"]}))

    def test_results_show_count_year_and_cover(self, mock_search):
        mock_search.return_value = self.RESULTS

        page = self.page()
        cards = self.cards(page)

        self.assertIn("2 results", page.select_one(".search-count").get_text())
        self.assertIn("2018", cards["Celeste"].get_text())
        self.assertIsNotNone(cards["Celeste"].find("img", src="https://media.example.com/c.jpg"))
        # No IGDB cover: a generated one instead of a missing picture
        self.assertIsNone(cards["Celeste Classic"].find("img"))
        self.assertIsNotNone(cards["Celeste Classic"].select_one("span.cover"))

    def test_games_already_in_my_library_are_marked(self, mock_search):
        mock_search.return_value = self.RESULTS
        user = get_user_model().objects.create_user(username="p1", email="p1@example.com", password="Gr8Backlog!42")
        game = Game.objects.create(igdb_id=1, game_title="Celeste", game_description="", game_rating=4.0)
        Catalog.objects.create(user=user, games=game)
        self.client.force_login(user)

        cards = self.cards(self.page())

        self.assertIn("In library", cards["Celeste"].get_text())
        self.assertNotIn("In library", cards["Celeste Classic"].get_text())

    def test_another_players_library_does_not_mark_results(self, mock_search):
        mock_search.return_value = self.RESULTS
        other = get_user_model().objects.create_user(username="p2", email="p2@example.com", password="Gr8Backlog!42")
        game = Game.objects.create(igdb_id=1, game_title="Celeste", game_description="", game_rating=4.0)
        Catalog.objects.create(user=other, games=game)

        self.assertNotIn("In library", self.page().get_text())

    def test_year_survives_an_igdb_outage(self, mock_search):
        mock_search.return_value = self.RESULTS
        self.page()
        mock_search.return_value = None

        self.assertIn("2018", self.cards(self.page())["Celeste"].get_text())

    def test_error_is_shown_as_an_alert(self, mock_search):
        mock_search.return_value = None

        alert = self.page().select_one('[role="alert"]')

        self.assertIn("Could not load games. Try again.", alert.get_text())

    def test_empty_search_shows_no_results_or_count(self, mock_search):
        page = self.page(query="")

        mock_search.assert_not_called()
        self.assertIsNone(page.select_one(".search-count"))
        self.assertIn("IGDB", page.get_text())


# Tests that the library page displays correctly and that logged out users are redirected to the login page when visiting.
class LibraryPageTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="user_b", email="user_b@example.com", password="TesTINGp#ass0r0d")
        self.next_igdb_id = 1

    def add(self, title, user=None, **entry):
        game = Game.objects.create(
            igdb_id=self.next_igdb_id, game_title=title, game_description="", game_rating=4.0,
        )
        self.next_igdb_id += 1
        return Catalog.objects.create(user=user or self.user, games=game, **entry)

    def page(self, **params):
        self.client.force_login(self.user)
        response = self.client.get(reverse("library"), params)
        self.assertEqual(response.status_code, 200)
        return BeautifulSoup(response.content, "html.parser").select_one("main")

    def titles(self, **params):
        return [h2.get_text(strip=True) for h2 in self.page(**params).select("article h2")]

    def test_logged_out_user_redirected_to_login(self):
        response = self.client.get(reverse("library"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('library')}")

    def test_logged_in_user_sees_their_library(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("library"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "user_b's Library")

    def test_logged_in_user_sees_saved_games_in_library(self):
        game = Game.objects.create(
            igdb_id=42,
            game_title="Celeste",
            game_description="Climb a mountain.",
            game_rating=4.8,
            game_image="https://example.com/celeste.jpg",
        )
        Catalog.objects.create(user=self.user, games=game)

        card = self.page().select_one("article")

        self.assertIn("Celeste", card.get_text())
        self.assertIn("Status: Not Started", card.get_text())
        self.assertIsNotNone(card.find("img", src="https://example.com/celeste.jpg"))
        self.assertIsNotNone(card.find("a", href=reverse("game_details", args=[42])))

    def test_library_does_not_show_other_users_games(self):
        other_user = get_user_model().objects.create_user(
            username="other_user", email="other@example.com", password="testpassword123"
        )
        self.add("Elden Ring", user=other_user)

        page = self.page()

        self.assertNotIn("Elden Ring", page.get_text())
        self.assertIn("Your library is empty", page.get_text())

    def test_card_reads_out_the_rating_or_says_not_rated(self):
        self.add("Celeste", rating=4)
        self.add("Balatro")

        rated, unrated = self.page().select("article")[::-1]

        self.assertIn("Rating: 4/5", rated.get_text())
        self.assertIn("Not rated", unrated.get_text())

    def test_header_counts_games_and_links_to_search(self):
        self.add("Celeste")
        self.add("Balatro")

        page = self.page()

        self.assertEqual(page.select_one(".library-top .hud").get_text(strip=True), "2 games")
        self.assertIsNotNone(page.find("a", href=reverse("game_search")))

    def test_newest_games_come_first_by_default(self):
        for title in ("Celeste", "Balatro", "Hades II"):
            self.add(title)

        self.assertEqual(self.titles(), ["Hades II", "Balatro", "Celeste"])

    def test_sort_by_title(self):
        for title in ("celeste", "Balatro", "Hades II"):
            self.add(title)

        self.assertEqual(self.titles(sort="title"), ["Balatro", "celeste", "Hades II"])

    def test_sort_by_rating_puts_unrated_games_last(self):
        self.add("Celeste", rating=3)
        self.add("Balatro")
        self.add("Hades II", rating=5)

        self.assertEqual(self.titles(sort="rating"), ["Hades II", "Celeste", "Balatro"])

    def test_unknown_sort_falls_back_to_newest_first(self):
        self.add("Celeste")
        self.add("Balatro")

        self.assertEqual(self.titles(sort="nonsense"), ["Balatro", "Celeste"])

    def test_sort_links_mark_the_current_order(self):
        self.add("Celeste")

        current = self.page(sort="title").select('.library-sort a[aria-current="true"]')

        self.assertEqual([a.get_text(strip=True) for a in current], ["Title"])

    def test_empty_library_points_to_search_and_hides_sorting(self):
        page = self.page()

        self.assertIn("Your library is empty", page.get_text())
        self.assertIsNotNone(page.find("a", href=reverse("game_search")))
        self.assertIsNone(page.select_one(".library-sort"))

    def test_logout_is_only_in_the_nav_bar(self):
        self.assertIsNone(self.page().find("form", action=reverse("logout")))

# Test that Catalog's get_or_import method works as expected
class CatalogGetOrImportTests(TestCase):

    @patch("games.catalog.get_game_details")
    def test_returns_existing_game_without_calling_igdb(self, mock_details):
        existing = Game.objects.create(
            igdb_id=42,
            game_title="Celeste",
            game_description="Climb a mountain.",
            game_rating=4.8,
        )

        result = get_or_import(42)

        self.assertEqual(result, existing)
        mock_details.assert_not_called()

    @patch("games.catalog.get_game_details")
    def test_imports_and_saves_new_game_from_igdb(self, mock_details):
        mock_details.return_value = {
            "id": 100,
            "name": "Hades",
            "summary": "Defy the god of the dead.",
            "rating": 4.9,
            "released": "2020-09-17",
            "cover": "https://example.com/hades.jpg",
            "genres": ["Action", "Indie"],
            "platforms": ["PC (Microsoft Windows)"],
        }

        game = get_or_import(100)

        self.assertIsNotNone(game)
        self.assertEqual(Game.objects.count(), 1)
        self.assertEqual(game.igdb_id, 100)
        self.assertEqual(game.game_title, "Hades")
        self.assertEqual(game.game_description, "Defy the god of the dead.")
        self.assertEqual(game.game_rating, 4.9)
        self.assertEqual(str(game.game_release), "2020-09-17")
        self.assertEqual(game.game_image, "https://example.com/hades.jpg")
        self.assertEqual(game.game_genre, "Action, Indie")
        self.assertEqual(game.game_platforms, "PC (Microsoft Windows)")

    @patch("games.catalog.get_game_details")
    def test_returns_none_when_igdb_fails(self, mock_details):
        mock_details.return_value = None

        result = get_or_import(999)

        self.assertIsNone(result)
        self.assertEqual(Game.objects.count(), 0)

    @patch("games.catalog.get_game_details")
    def test_handles_missing_or_null_igdb_fields(self, mock_details):
        mock_details.return_value = {
            "id": 101,
            "name": "Mystery Game",
            "summary": "",
            "rating": None,
            "released": None,
            "cover": "",
            "genres": [],
            "platforms": [],
        }

        game = get_or_import(101)

        self.assertIsNotNone(game)
        self.assertEqual(game.game_title, "Mystery Game")
        self.assertEqual(game.game_description, "")
        self.assertEqual(game.game_rating, 0)
        self.assertIsNone(game.game_release)
        self.assertEqual(game.game_image, "")
        self.assertEqual(game.game_genre, "")
        self.assertEqual(game.game_platforms, "")

class AddToLibraryViewTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="player1", email="player1@example.com", password="testpassword123"
        )

    @patch("games.views.get_or_import")
    def test_add_to_library_creates_catalog_entry(self, mock_get_or_import):
        game = Game.objects.create(
            igdb_id=10,
            game_title="Portal",
            game_description="A puzzle game.",
            game_rating=4.7,
        )
        mock_get_or_import.return_value = game
        self.client.force_login(self.user)

        response = self.client.post(reverse("add_to_library", args=[10]))

        self.assertRedirects(response, reverse("game_details", args=[10]), fetch_redirect_response=False)
        self.assertTrue(Catalog.objects.filter(user=self.user, games=game).exists())

    @patch("games.views.get_or_import")
    def test_add_to_library_does_not_duplicate_catalog_entry(self, mock_get_or_import):
        game = Game.objects.create(
            igdb_id=10,
            game_title="Portal",
            game_description="A puzzle game.",
            game_rating=4.7,
        )
        mock_get_or_import.return_value = game
        self.client.force_login(self.user)

        self.client.post(reverse("add_to_library", args=[10]))
        self.client.post(reverse("add_to_library", args=[10]))

        self.assertEqual(Catalog.objects.filter(user=self.user, games=game).count(), 1)

    @patch("games.views.get_or_import")
    def test_add_to_library_handles_igdb_failure(self, mock_get_or_import):
        mock_get_or_import.return_value = None
        self.client.force_login(self.user)

        response = self.client.post(reverse("add_to_library", args=[999]))

        self.assertRedirects(response, reverse("game_details", args=[999]), fetch_redirect_response=False)
        self.assertEqual(Catalog.objects.count(), 0)

    def test_add_to_library_requires_login(self):
        url = reverse("add_to_library", args=[10])
        response = self.client.post(url)

        self.assertRedirects(response, f"{reverse('login')}?next={url}")
        self.assertEqual(Catalog.objects.count(), 0)

        
    def test_catalog_rejects_duplicate_user_and_game(self):
        game = Game.objects.create(
            igdb_id=10, game_title="Portal", game_description="A puzzle game.", game_rating=4.7,
        )
        Catalog.objects.create(user=self.user, games=game)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Catalog.objects.create(user=self.user, games=game)

class RemoveFromLibraryViewTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="player1", email="player1@example.com", password="testpassword123"
        )
        self.game = Game.objects.create(
            igdb_id=10,
            game_title="Portal",
            game_description="A puzzle game.",
            game_rating=4.7,
        )

    def test_remove_from_library_deletes_catalog_entry(self):
        Catalog.objects.create(user=self.user, games=self.game)
        self.client.force_login(self.user)

        response = self.client.post(reverse("remove_from_library", args=[10]))

        self.assertRedirects(response, reverse("game_details", args=[10]), fetch_redirect_response=False)
        self.assertFalse(Catalog.objects.filter(user=self.user, games=self.game).exists())
        self.assertTrue(Game.objects.filter(igdb_id=10).exists())

    def test_remove_from_library_returns_404_when_not_in_library(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("remove_from_library", args=[999]))

        self.assertEqual(response.status_code, 404)

    def test_remove_from_library_cannot_delete_other_users_entry(self):
        other_user = get_user_model().objects.create_user(
            username="player2", email="player2@example.com", password="testpassword123"
        )
        Catalog.objects.create(user=other_user, games=self.game)
        self.client.force_login(self.user)

        response = self.client.post(reverse("remove_from_library", args=[10]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Catalog.objects.filter(user=other_user, games=self.game).exists())

    def test_remove_from_library_requires_login(self):
        Catalog.objects.create(user=self.user, games=self.game)
        url = reverse("remove_from_library", args=[10])

        response = self.client.post(url)

        self.assertRedirects(response, f"{reverse('login')}?next={url}")
        self.assertTrue(Catalog.objects.filter(user=self.user, games=self.game).exists())


class DetailsPageTests(TestCase):
    """The game page: cover and facts from IGDB, our players' average, and the player's own save file."""

    GAME = {
        "id": 42, "name": "Portal", "summary": "A puzzle game with portals.", "released": "2007-10-10",
        "rating": 4.5, "cover": "https://images.example.com/portal.jpg",
        "genres": ["Puzzle", "Shooter"], "platforms": ["PC (Microsoft Windows)", "Xbox 360"],
    }

    def setUp(self):
        patcher = patch("games.catalog.get_game_details", return_value=dict(self.GAME))
        self.details = patcher.start()
        self.addCleanup(patcher.stop)
        self.user = get_user_model().objects.create_user(username="player", email="player@example.com")
        self.game = get_or_import(42)   # saved from the fake IGDB answer, as the first visit would

    def page(self, **params):
        response = self.client.get(reverse("game_details", args=[42]), params)
        self.assertEqual(response.status_code, 200)
        return BeautifulSoup(response.content, "html.parser").select_one("main")

    def own(self, **entry):
        self.client.force_login(self.user)
        return Catalog.objects.create(user=self.user, games=self.game, **entry)

    def test_header_shows_year_genres_and_igdb_score(self):
        head = self.page().select_one(".details-head")

        self.assertEqual(head.h1.get_text(strip=True), "Portal")
        self.assertIn("2007 · Puzzle, Shooter", head.get_text(" ", strip=True))
        self.assertIn("IGDB 4.5", head.get_text(" ", strip=True))

    def test_facts_list_release_date_and_platforms(self):
        facts = self.page().select_one("dl.details-facts")

        self.assertEqual(facts.find("time")["datetime"], "2007-10-10")
        self.assertIn("Oct 10, 2007", facts.get_text())
        self.assertIn("PC (Microsoft Windows), Xbox 360", facts.get_text())

    def test_players_average_counts_only_ratings(self):
        for name, rating in [("a", 3), ("b", 4), ("c", None)]:
            user = get_user_model().objects.create_user(username=name, email=f"{name}@example.com")
            Catalog.objects.create(user=user, games=self.game, rating=rating, review="Hm.")

        head = self.page().select_one(".details-head").get_text(" ", strip=True)

        self.assertIn("Players 3.5", head)
        self.assertIn("2 ratings", head)

    def test_no_players_average_without_ratings(self):
        self.assertNotIn("Players", self.page().select_one(".details-head").get_text())

    def test_visitor_is_asked_to_log_in_and_come_back(self):
        save = self.page().select_one(".details-save")

        link = save.find("a", string="Log in to add to your library")
        self.assertEqual(link["href"], f"{reverse('login')}?next={reverse('game_details', args=[42])}")
        self.assertIsNone(save.find("form"))

    def test_player_without_the_game_can_add_it(self):
        self.client.force_login(self.user)

        save = self.page().select_one(".details-save")

        self.assertIsNotNone(save.find("form", action=reverse("add_to_library", args=[42])))
        self.assertIsNone(save.find("form", action=reverse("save_review", args=[42])))

    def test_owner_can_change_status_in_review_form(self):
        self.own()

        form = self.page().find("form", action=reverse("save_review", args=[42]))
        status = form.select_one("fieldset.status-picker")

        self.assertFalse(status.has_attr("disabled"))
        checked = status.select('input[name="status"][checked]')
        self.assertEqual([i["value"] for i in checked], ["not_started"])
        self.assertEqual(status.find("label", attrs={"for": checked[0]["id"]}).get_text(strip=True), "Not Started")

    def test_review_box_counts_characters(self):
        self.own(review="Fun puzzles.")

        form = self.page().find("form", action=reverse("save_review", args=[42]))

        self.assertEqual(form.find("textarea")["maxlength"], "1000")
        self.assertEqual(form.select_one("[data-review-count]").get_text(strip=True), "12 / 1,000")

    def test_removing_asks_for_confirmation_in_a_site_dialog(self):
        self.own()
        page = self.page()

        # The button only opens a Bootstrap modal; the form that removes the game is inside it
        opener = page.find("button", string="Remove from library", attrs={"data-bs-toggle": "modal"})
        self.assertEqual(opener["type"], "button")
        dialog = page.select_one(opener["data-bs-target"])
        self.assertIn("modal", dialog["class"])
        self.assertEqual(dialog.select_one("#" + dialog["aria-labelledby"]).get_text(strip=True), "Remove Portal?")
        self.assertIn("rating and review", dialog.get_text())
        form = dialog.find("form", action=reverse("remove_from_library", args=[42]))
        self.assertEqual(form.find("button", type="submit").get_text(strip=True), "Remove from library")
        self.assertEqual(form.find("button", attrs={"data-bs-dismiss": "modal"}).get_text(strip=True), "Keep it")
        # No browser confirm box on top of the dialog
        self.assertIsNone(page.select_one("[data-confirm]"))

    def test_reviews_show_stars_and_read_out_the_rating(self):
        self.own(rating=4, review="Clever.")

        review = self.page().select_one(".details-reviews article")

        self.assertEqual(review.select_one(".stars")["aria-hidden"], "true")
        self.assertIn("Rating: 4/5", review.get_text())

    def test_back_link_returns_to_the_search(self):
        link = self.page(q="portal & co").find("a", string=lambda t: t and "Back to results" in t)

        self.assertEqual(link["href"], "/search/?q=portal%20%26%20co")

    def test_no_back_link_without_a_search(self):
        self.assertIsNone(self.page().find("a", string=lambda t: t and "Back to results" in t))

    def test_error_is_an_alert_with_a_way_back_to_search(self):
        self.game.delete()
        self.details.return_value = None

        page = self.page()

        self.assertIn("Could not load game details. Try again.", page.select_one('[role="alert"]').get_text())
        self.assertIsNotNone(page.find("a", href=reverse("game_search")))
        self.assertIsNone(page.select_one(".details-save"))


class ReviewTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="player", email="player@example.com")
        self.game = Game.objects.create(
            igdb_id=42, game_title="Portal", game_description="Puzzles.", game_rating=4.7,
        )
        self.entry = Catalog.objects.create(user=self.user, games=self.game)
        self.client.force_login(self.user)
        patcher = patch("games.catalog.get_game_details", return_value={"id": 42, "name": "Portal"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def save_review(self, rating="", review="", status=Catalog.Status.NOT_STARTED, **kwargs):
        return self.client.post(reverse("save_review", args=[42]), {
            "rating": rating, "review": review, "status": status
        }, **kwargs)

    def assert_entry(self, rating, review, edited, status=Catalog.Status.NOT_STARTED):
        self.entry.refresh_from_db()
        self.assertEqual(
            (self.entry.rating, self.entry.review, self.entry.review_edited, self.entry.status),
            (rating, review, edited, status),
        )

    def test_save_review_requires_login(self):
        self.client.logout()
        url = reverse("save_review", args=[42])
        response = self.save_review(4, "Fun.")
        self.assertRedirects(response, f"{reverse('login')}?next={url}")
        self.assert_entry(None, "", False)

    def test_save_review_requires_library_entry(self):
        self.entry.delete()
        response = self.save_review(4, "Fun.")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Catalog.objects.exists())

    def test_save_review_rejects_get(self):
        response = self.client.get(reverse("save_review", args=[42]))
        self.assertEqual(response.status_code, 405)
        self.assert_entry(None, "", False)

    def test_rating_is_saved_and_shown_in_library(self):
        response = self.save_review(4)
        self.assertRedirects(response, reverse("game_details", args=[42]))
        self.assert_entry(4, "", False)
        library = BeautifulSoup(self.client.get(reverse("library")).content, "html.parser")
        self.assertIn("Rating: 4/5", library.select_one("main article").get_text())

    def test_new_rating_replaces_old_rating(self):
        self.entry.rating = 2
        self.entry.save()
        self.save_review(5)
        self.assert_entry(5, "", False)

    def test_review_over_1000_characters_changes_nothing_and_shows_error(self):
        self.entry.rating, self.entry.review = 3, "Keep this."
        self.entry.save()
        response = self.save_review(5, "x" * 1001, status=Catalog.Status.PLAYING, follow=True)
        self.assertContains(response, "Keep your review to 1,000 characters or fewer.")
        self.assertNotContains(response, "Pick a rating from 1 to 5.")
        self.assert_entry(3, "Keep this.", False)
        self.save_review(5, "x" * 1000)
        self.assert_entry(5, "x" * 1000, True)

    def test_invalid_rating_changes_nothing_and_shows_error(self):
        self.entry.rating, self.entry.review = 3, "Keep this."
        self.entry.review_edited = True
        self.entry.save()
        for rating in (0, 6, "abc"):
            with self.subTest(rating=rating):
                response = self.save_review(rating, "Must not save.", status=Catalog.Status.PLAYING, follow=True)
                self.assertRedirects(response, reverse("game_details", args=[42]))
                self.assertContains(response, "Pick a rating from 1 to 5.")
                shown = list(response.context["messages"])
                self.assertEqual([(m.level, str(m)) for m in shown], [
                    (messages.ERROR, "Pick a rating from 1 to 5."),
                ])
                self.assert_entry(3, "Keep this.", True)

    def test_database_rejects_out_of_range_rating(self):
        for rating in (0, 6):
            with self.subTest(rating=rating), self.assertRaises(IntegrityError):
                with transaction.atomic():
                    self.entry.rating = rating
                    self.entry.save()

    def test_model_validators_reject_out_of_range_rating(self):
        for rating in (0, 6):
            with self.subTest(rating=rating), self.assertRaises(ValidationError):
                self.entry.rating = rating
                self.entry.full_clean()

    def test_review_edited_tracks_text_changes_only(self):
        for rating, review, edited in [
            ("", "First review.", False),
            (4, "First review.", False),
            (4, "Changed review.", True),
            (5, "Changed review.", True),
            (5, "", False),
            (5, "A fresh review.", False),
        ]:
            with self.subTest(rating=rating, review=review):
                self.save_review(rating, review)
                self.assert_entry(rating or None, review, edited)

    def test_both_fields_can_be_cleared(self):
        self.entry.rating, self.entry.review = 4, "Fun."
        self.entry.review_edited = True
        self.entry.save()
        self.save_review()
        self.assert_entry(None, "", False)
        self.assertContains(self.client.get(reverse("library")), "Not rated")

    def test_not_rated_clears_the_rating_and_keeps_the_review(self):
        self.entry.rating, self.entry.review = 4, "Fun."
        self.entry.save()
        self.save_review("", "Fun.")
        self.assert_entry(None, "Fun.", False)

    def test_user_cannot_change_another_users_entry(self):
        other = get_user_model().objects.create_user(username="other", email="other@example.com")
        entry = Catalog.objects.create(user=other, games=self.game, rating=2, review="Their review.")
        response = self.client.post(reverse("save_review", args=[42]), {
            "rating": 5, "review": "My review.", "status": Catalog.Status.COMPLETED, "user": other.pk, "id": entry.pk,
        })
        self.assertRedirects(response, reverse("game_details", args=[42]))
        self.assert_entry(5, "My review.", False, status=Catalog.Status.COMPLETED)
        self.entry.delete()
        self.assertEqual(self.save_review(1, "Overwrite.").status_code, 404)
        entry.refresh_from_db()
        self.assertEqual((entry.rating, entry.review, entry.review_edited, entry.status), (2, "Their review.", False, Catalog.Status.NOT_STARTED))

    def test_game_page_lists_all_reviews_in_username_order_for_everyone(self):
        self.entry.rating, self.entry.review = 4, "<b>Fun.</b>"
        self.entry.review_edited = True
        self.entry.save()
        for username, rating, review in [("alpha", 2, ""), ("beta", None, "Great puzzles."), ("empty", None, "")]:
            user = get_user_model().objects.create_user(username=username, email=f"{username}@example.com")
            Catalog.objects.create(user=user, games=self.game, rating=rating, review=review)
        other_game = Game.objects.create(igdb_id=99, game_title="Other", game_description="", game_rating=0)
        Catalog.objects.create(user=self.user, games=other_game, review="Wrong game.")
        for logged_in in (True, False):
            with self.subTest(logged_in=logged_in):
                if not logged_in:
                    self.client.logout()
                response = self.client.get(reverse("game_details", args=[42]))
                articles = BeautifulSoup(response.content, "html.parser").find_all("article")
                self.assertEqual([a.h3.get_text(strip=True) for a in articles], ["alpha", "beta", "player"])
                self.assertIn("Rating: 2/5", articles[0].get_text())
                self.assertNotIn("edited", articles[0].get_text())
                self.assertIn("Great puzzles.", articles[1].get_text())
                self.assertNotIn("Rating:", articles[1].get_text())
                self.assertIn("Rating: 4/5", articles[2].get_text())
                self.assertIn("<b>Fun.</b>", articles[2].get_text())
                self.assertIsNone(articles[2].find("b"))
                self.assertIn("edited", articles[2].get_text())
                self.assertNotContains(response, "Wrong game.")

    def test_game_page_prefills_review_form_and_rating_choices(self):
        self.entry.rating, self.entry.review, self.entry.status = 4, "Fun puzzles.", Catalog.Status.PLAYING
        self.entry.save()
        response = self.client.get(reverse("game_details", args=[42]))
        page = BeautifulSoup(response.content, "html.parser")
        form = page.find("form", action=reverse("save_review", args=[42]))
        self.assertIsNotNone(form)
        self.assertEqual(form["method"], "post")
        self.assertIsNotNone(form.find("input", attrs={"name": "csrfmiddlewaretoken"}))
        radios = form.find_all("input", attrs={"type": "radio", "name": "rating"})
        self.assertEqual([r["value"] for r in radios], ["", "1", "2", "3", "4", "5"])
        self.assertEqual([r["value"] for r in radios if r.has_attr("checked")], ["4"])
        for radio, label in zip(radios, ["Not rated", "1 star", "2 stars", "3 stars", "4 stars", "5 stars"]):
            self.assertEqual(form.find("label", attrs={"for": radio["id"]}).get_text(strip=True), label)
        self.assertEqual(form.find("textarea", attrs={"name": "review"}).get_text().strip(), "Fun puzzles.")
        self.assertEqual(form.find("button").get_text(strip=True), "Save")
        selected = form.select_one('select[name="status"] option[selected]')
        self.assertIsNotNone(selected)
        self.assertEqual(selected["value"], Catalog.Status.PLAYING)

    def test_review_form_hidden_without_library_entry_or_login(self):
        url = reverse("save_review", args=[42])
        self.client.logout()
        response = self.client.get(reverse("game_details", args=[42]))
        self.assertIsNone(BeautifulSoup(response.content, "html.parser").find("form", action=url))
        self.client.force_login(self.user)
        self.entry.delete()
        response = self.client.get(reverse("game_details", args=[42]))
        self.assertIsNone(BeautifulSoup(response.content, "html.parser").find("form", action=url))

    def test_game_page_shows_no_reviews_for_unrated_entry(self):
        response = self.client.get(reverse("game_details", args=[42]))
        self.assertContains(response, "No reviews yet.")

    def test_removing_game_deletes_rating_and_review(self):
        self.entry.rating, self.entry.review = 4, "Fun."
        self.entry.save()
        self.client.post(reverse("remove_from_library", args=[42]))
        self.assertFalse(Catalog.objects.filter(pk=self.entry.pk).exists())
        self.assertContains(self.client.get(reverse("game_details", args=[42])), "No reviews yet.")

    # This section of tests tests the status field of the Catalog model, which tracks whether a user has started, is playing, or has completed a game.
    
    def test_status_only_save_does_not_create_review(self):
        self.entry.status = Catalog.Status.DROPPED
        self.entry.save()

        for status, label in Catalog.Status.choices:
            with self.subTest(status=status):
                response = self.save_review(status=status, follow=True)

                self.assertRedirects(response, reverse("game_details", args=[42]))
                self.assert_entry(None, "", False, status=status)
                self.assertEqual(
                    list(Catalog.objects.values_list("pk", flat=True)),
                    [self.entry.pk],
                )
                self.assertContains(response, "No reviews yet.")
                self.assertContains(
                    self.client.get(reverse("library")), f"Status: {label}"
                )

    def test_status_change_preserves_existing_review(self):
        for edited in (False, True):
            with self.subTest(edited=edited):
                self.entry.rating, self.entry.review = 4, "Keep this."
                self.entry.review_edited = edited
                self.entry.status = Catalog.Status.NOT_STARTED
                self.entry.save()

                response = self.save_review(
                    4, "Keep this.", status=Catalog.Status.COMPLETED
                )

                self.assertRedirects(response, reverse("game_details", args=[42]))
                self.assert_entry(
                    4, "Keep this.", edited, status=Catalog.Status.COMPLETED
                )

    def test_missing_or_invalid_status_changes_nothing(self):
        self.entry.rating, self.entry.review = 3, "Keep this."
        self.entry.review_edited = True
        self.entry.status = Catalog.Status.PLAYING
        self.entry.save()

        for status_data in ({}, {"status": ""}, {"status": "invalid"}):
            with self.subTest(status_data=status_data):
                response = self.client.post(
                    reverse("save_review", args=[42]),
                    {"rating": 5, "review": "Must not save.", **status_data},
                    follow=True,
                )

                self.assertRedirects(response, reverse("game_details", args=[42]))
                self.assertContains(response, "Pick a valid play status.")
                self.assert_entry(
                    3, "Keep this.", True, status=Catalog.Status.PLAYING
                )