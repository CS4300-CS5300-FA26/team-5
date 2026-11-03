from datetime import date

from django.test import TestCase

from .models import Game

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



# Tests that the library page displays correctly and that logged out users are redirected to the login page when visiting.
class LibraryPageTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="user_b", password="TesTINGp#ass0r0d")

    def test_logged_out_user_redirected_to_login(self):
        response = self.client.get(reverse("library"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('library')}")

    def test_logged_in_user_sees_their_library(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("library"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "user_b's Library")
