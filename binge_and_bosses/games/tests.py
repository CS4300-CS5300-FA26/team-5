from datetime import date

from django.test import TestCase

from .models import Game

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
        self.user = get_user_model().objects.create_user(username="user_b", password="TesTINGp#ass0r0d")

    def test_logged_out_user_redirected_to_login(self):
        response = self.client.get(reverse("library"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('library')}")

    def test_logged_in_user_sees_their_library(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("library"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "user_b's Library")