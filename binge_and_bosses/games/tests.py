from datetime import date

from django.test import TestCase

from .models import Game, Catalog
from .catalog import get_or_import

from unittest.mock import patch,Mock
from .rawg_client import search_game,get_game_details
from django.urls import reverse

from django.contrib.auth import get_user_model


# Tests for the landing page (URL "/" -> index view -> Game model -> index.html).
# Django's TestCase runs against a temporary test database, so these tests
# never read or write the real development or production data.
class LandingPageTests(TestCase):

    def test_home_page_lists_saved_game(self):
        Game.objects.create(
            game_title="Hollow Knight",
            game_description="Explore the ruined kingdom of Hallownest.",
            game_rating=9.5,
            game_release=date(2017, 2, 24),
        )

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hollow Knight")
        self.assertContains(response, "Explore the ruined kingdom of Hallownest.")
        self.assertContains(response, "9.5")
        self.assertContains(response, "Feb. 24, 2017")
        self.assertNotContains(response, "No games yet...")

    def test_home_page_shows_empty_message_without_games(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No games yet...")


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

    @patch('games.views.get_game_details')
    def test_game_details_view(self,mock_search_game_detail):

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
        self.assertContains(response,1)
        self.assertContains(response,'2011-11-18')

    @patch('games.views.get_game_details')
    def test_details_api_failure(self, mock_get_game_details):

        mock_get_game_details.return_value = None

        response = self.client.get('/1/')

        self.assertEqual(response.status_code, 200)

        mock_get_game_details.assert_called_once_with(1)

        self.assertTrue(response.context['error'])
        self.assertIsNone(response.context['game'])

    
    

    



# Tests that the logout button actually logs the user out via post and redirects to the right place
class LogoutTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="user_b", password="TesTINGp#ass0r0d")
        self.client.force_login(self.user)

    def test_logout_post_logs_user_out(self):
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, "/accounts/login/", fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_nav_shows_username_when_logged_in(self):
        response = self.client.get("/")
        self.assertContains(response, "user_b")
        self.assertContains(response, "Log out")

    def test_nav_shows_correct_buttons_when_logged_out(self):
        self.client.logout()
        response = self.client.get("/")
        self.assertContains(response, "Log in")
        self.assertContains(response, "Sign up")

    def test_signup_directs_to_signup_page(self):

        """
            Checks if the index page contains the expected signup url for the sign up button
        """
        
        self.client.logout()

        response = self.client.get(reverse('index'))

        expected_url = reverse('signup')

        expected_url_html = f'href="{expected_url}"'

        self.assertContains(response,expected_url_html)

# Tests that the library page displays correctly and that logged out users are redirected to the login page when visiting.
class LibraryPageTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="user_b", email="user_b@example.com", password="TesTINGp#ass0r0d")

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
        self.client.force_login(self.user)

        response = self.client.get(reverse("library"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Celeste")
        self.assertContains(response, "Status: Not Started")
        self.assertContains(response, "https://example.com/celeste.jpg")
        self.assertContains(response, reverse("game_details", args=[42]))
        self.assertNotContains(response, "Your games will show up here soon.")
    
    def test_library_does_not_show_other_users_games(self):
        other_user = get_user_model().objects.create_user(
            username="other_user", email="other@example.com", password="testpassword123"
        )
        other_game = Game.objects.create(
            rawg_id=99,
            game_title="Elden Ring",
            game_description="Become the Elden Lord.",
            game_rating=4.9,
        )
        Catalog.objects.create(user=other_user, games=other_game)
        self.client.force_login(self.user)

        response = self.client.get(reverse("library"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Elden Ring")
        self.assertContains(response, "Your games will show up here soon.")

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
            "genres": [],
        }

        game = get_or_import(101)

        self.assertIsNotNone(game)
        self.assertEqual(game.game_title, "Mystery Game")
        self.assertEqual(game.game_description, "")
        self.assertEqual(game.game_rating, 0)
        self.assertIsNone(game.game_release)
        self.assertEqual(game.game_image, "")
        self.assertEqual(game.game_genre, "")

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
