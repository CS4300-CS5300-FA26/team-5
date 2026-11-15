from datetime import date

from bs4 import BeautifulSoup
from django.contrib import messages
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Game, Catalog
from .catalog import get_or_import

from unittest.mock import patch,Mock
from .rawg_client import search_game,get_game_details
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
        self.next_rawg_id = 1

    def add(self, title, user=None, **entry):
        game = Game.objects.create(
            rawg_id=self.next_rawg_id, game_title=title, game_description="", game_rating=4.0,
            game_image=f"https://media.example.com/{title}.jpg",
        )
        self.next_rawg_id += 1
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
        self.assertEqual(rows[0]["href"], reverse("game_details", args=[balatro.rawg_id]))

    def test_popular_skips_games_without_an_id_to_link_to(self):
        self.add("Hades II")   # the cards only show once your library has a game
        ana = self.player("ana")
        orphan = self.add("Saved by hand", user=ana).games   # e.g. added in the admin without an id
        orphan.rawg_id = None
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


class SearchAPICheckandDetails(TestCase):

    @patch('games.rawg_client.requests.get')
    def test_RAWG_API_search(self,mock_get):

        mock_response = Mock()

        mock_response.json.return_value = {
            "results":[
                {'id':1,'name':'Minecraft'},
                {'id':2,'name':'Minecraft Pocket Edition'}
            ]
        }

        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        games = search_game("Minecraft")

        #Does the list return 2 games
        self.assertEqual(len(games),2)
        self.assertEqual(games[0]['name'],"Minecraft")
        self.assertEqual(games[0]['id'],1)
        self.assertEqual(games[1]['name'],"Minecraft Pocket Edition")
        self.assertEqual(games[1]['id'],2)

    @patch('games.rawg_client.requests.get')
    def test_RAWG_API_details(self,mock_get):

        mock_response = Mock()

        mock_response.json.return_value = {
            'id':1,
            'name':'Minecraft',
            'released': '2011-11-18',
            'genres':[
                {'id': 1,'name':'Action'},
                {'id': 2,'name':'Adventure'}
            ]
        }

        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        game_details = get_game_details("Minecraft")

        self.assertEqual(game_details['id'],1)
        self.assertEqual(game_details['name'],"Minecraft")
        self.assertEqual(game_details['released'],"2011-11-18")
        self.assertEqual(game_details['genres'][0]['id'],1)
        self.assertEqual(game_details['genres'][0]['name'],'Action')
        self.assertEqual(game_details['genres'][1]['id'],2)
        self.assertEqual(game_details['genres'][1]['name'],'Adventure')

       

class GameSearchandDetailsViewTests(TestCase):

    @patch('games.views.search_game')
    def test_game_search_view(self,mock_search_game):

        mock_search_game.return_value = [
            {'id': 1,'name':'Minecraft'},
            {'id':2,'name':'Minecraft Pocket Edition'}
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
            {'id': 1, 'name': 'Minecraft', 'background_image': 'https://example.com/m.jpg'},
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
        mock_search_game.return_value = [{'id': 1, 'name': 'Pokemon Red'}]

        response = self.client.get(reverse('game_search'), {'q': 'Pokémon & Red/Blue'})

        self.assertContains(
            response, 'href="/1/?q=Pok%C3%A9mon%20%26%20Red%2FBlue"'
        )

    @patch('games.catalog.get_game_details')
    def test_game_details_view_for_new_games_not_in_database(self,mock_search_game_detail):

        mock_search_game_detail.return_value = {
            'id':1,
            'name':'Minecraft',
            'released':'2011-11-18',
            'genres':[
                {'id': 1,'name':'Action'},
                {'id': 2,'name':'Adventure'}
            ]
        }

        response = self.client.get('/1/')

        self.assertEqual(response.status_code,200)

        mock_search_game_detail.assert_called_once_with(1)

        self.assertContains(response,"Minecraft")
        self.assertTrue(Game.objects.filter(rawg_id=1).exists())
        self.assertContains(response,'Nov 18, 2011')

    @patch('games.catalog.get_game_details')
    def test_game_details_view_when_game_is_in_database(self,mock_details):

        Game.objects.create(
        rawg_id=1, game_title="Minecraft", game_description="Build things.",
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
        mock_search.return_value = [{'id': 1, 'name': 'Pokemon Red'}]

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
        for image in ['', None]:
            with self.subTest(background_image=image):
                mock_details.return_value = {
                    'id': 1, 'name': 'Pokemon Red',
                    'background_image': image, 'description_raw': '',
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
        {"id": 1, "name": "Celeste", "released": "2018-01-25", "background_image": "https://media.example.com/c.jpg"},
        {"id": 2, "name": "Celeste Classic", "released": None, "background_image": None},
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
        # No RAWG image: a generated cover instead of a missing picture
        self.assertIsNone(cards["Celeste Classic"].find("img"))
        self.assertIsNotNone(cards["Celeste Classic"].select_one("span.cover"))

    def test_games_already_in_my_library_are_marked(self, mock_search):
        mock_search.return_value = self.RESULTS
        user = get_user_model().objects.create_user(username="p1", email="p1@example.com", password="Gr8Backlog!42")
        game = Game.objects.create(rawg_id=1, game_title="Celeste", game_description="", game_rating=4.0)
        Catalog.objects.create(user=user, games=game)
        self.client.force_login(user)

        cards = self.cards(self.page())

        self.assertIn("In library", cards["Celeste"].get_text())
        self.assertNotIn("In library", cards["Celeste Classic"].get_text())

    def test_another_players_library_does_not_mark_results(self, mock_search):
        mock_search.return_value = self.RESULTS
        other = get_user_model().objects.create_user(username="p2", email="p2@example.com", password="Gr8Backlog!42")
        game = Game.objects.create(rawg_id=1, game_title="Celeste", game_description="", game_rating=4.0)
        Catalog.objects.create(user=other, games=game)

        self.assertNotIn("In library", self.page().get_text())

    def test_year_survives_a_rawg_outage(self, mock_search):
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
        self.assertIn("RAWG", page.get_text())


# Tests that the library page displays correctly and that logged out users are redirected to the login page when visiting.
class LibraryPageTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="user_b", email="user_b@example.com", password="TesTINGp#ass0r0d")
        self.next_rawg_id = 1

    def add(self, title, user=None, **entry):
        game = Game.objects.create(
            rawg_id=self.next_rawg_id, game_title=title, game_description="", game_rating=4.0,
        )
        self.next_rawg_id += 1
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
            rawg_id=42,
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
    def test_returns_existing_game_without_calling_rawg(self, mock_details):
        existing = Game.objects.create(
            rawg_id=42,
            game_title="Celeste",
            game_description="Climb a mountain.",
            game_rating=4.8,
        )

        result = get_or_import(42)

        self.assertEqual(result, existing)
        mock_details.assert_not_called()

    @patch("games.catalog.get_game_details")
    def test_imports_and_saves_new_game_from_rawg(self, mock_details):
        mock_details.return_value = {
            "id": 100,
            "name": "Hades",
            "description_raw": "Defy the god of the dead.",
            "rating": 4.9,
            "released": "2020-09-17",
            "background_image": "https://example.com/hades.jpg",
            "genres": [{"name": "Action"}, {"name": "Indie"}],
            "platforms": [{"platform": {"name": "PC"}}]
        }


        game = get_or_import(100)

        self.assertIsNotNone(game)
        self.assertEqual(Game.objects.count(), 1)
        self.assertEqual(game.rawg_id, 100)
        self.assertEqual(game.game_title, "Hades")
        self.assertEqual(game.game_description, "Defy the god of the dead.")
        self.assertEqual(game.game_rating, 4.9)
        self.assertEqual(str(game.game_release), "2020-09-17")
        self.assertEqual(game.game_image, "https://example.com/hades.jpg")
        self.assertEqual(game.game_genre, "Action, Indie")
        self.assertEqual(game.game_platforms, "PC")

    @patch("games.catalog.get_game_details")
    def test_returns_none_when_rawg_fails(self, mock_details):
        mock_details.return_value = None

        result = get_or_import(999)

        self.assertIsNone(result)
        self.assertEqual(Game.objects.count(), 0)

    @patch("games.catalog.get_game_details")
    def test_handles_missing_or_null_rawg_fields(self, mock_details):
        mock_details.return_value = {
            "id": 101,
            "name": "Mystery Game",
            "description_raw": None,
            "rating": None,
            "released": None,
            "background_image": None,
            "genres": None,
            "platforms": None,
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
            rawg_id=10,
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
            rawg_id=10,
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
    def test_add_to_library_handles_rawg_failure(self, mock_get_or_import):
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
            rawg_id=10, game_title="Portal", game_description="A puzzle game.", game_rating=4.7,
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
            rawg_id=10,
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
        self.assertTrue(Game.objects.filter(rawg_id=10).exists())

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


class ReviewTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="player", email="player@example.com")
        self.game = Game.objects.create(
            rawg_id=42, game_title="Portal", game_description="Puzzles.", game_rating=4.7,
        )
        self.entry = Catalog.objects.create(user=self.user, games=self.game)
        self.client.force_login(self.user)
        patcher = patch("games.catalog.get_game_details", return_value={"id": 42, "name": "Portal"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def save_review(self, rating="", review="", **kwargs):
        return self.client.post(reverse("save_review", args=[42]), {
            "rating": rating, "review": review,
        }, **kwargs)

    def assert_entry(self, rating, review, edited):
        self.entry.refresh_from_db()
        self.assertEqual(
            (self.entry.rating, self.entry.review, self.entry.review_edited),
            (rating, review, edited),
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
        response = self.save_review(5, "x" * 1001, follow=True)
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
                response = self.save_review(rating, "Must not save.", follow=True)
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
            "rating": 5, "review": "My review.", "user": other.pk, "id": entry.pk,
        })
        self.assertRedirects(response, reverse("game_details", args=[42]))
        self.assert_entry(5, "My review.", False)
        self.entry.delete()
        self.assertEqual(self.save_review(1, "Overwrite.").status_code, 404)
        entry.refresh_from_db()
        self.assertEqual((entry.rating, entry.review, entry.review_edited), (2, "Their review.", False))

    def test_game_page_lists_all_reviews_in_username_order_for_everyone(self):
        self.entry.rating, self.entry.review = 4, "<b>Fun.</b>"
        self.entry.review_edited = True
        self.entry.save()
        for username, rating, review in [("alpha", 2, ""), ("beta", None, "Great puzzles."), ("empty", None, "")]:
            user = get_user_model().objects.create_user(username=username, email=f"{username}@example.com")
            Catalog.objects.create(user=user, games=self.game, rating=rating, review=review)
        other_game = Game.objects.create(rawg_id=99, game_title="Other", game_description="", game_rating=0)
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
        self.entry.rating, self.entry.review = 4, "Fun puzzles."
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
