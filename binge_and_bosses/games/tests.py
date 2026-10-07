from datetime import date

from django.test import TestCase

from .models import Game


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
