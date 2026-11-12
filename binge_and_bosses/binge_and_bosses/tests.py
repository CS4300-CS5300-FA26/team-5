from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

class NavBarUnauthenticated(TestCase):
    """
        What unauthenticated user's will see for the navbar
    """
    def test_navbar_brand_exists_and_links(self):
        """
            Test that on the navbar at the index, there exists
            the 'Binge and Bosses' link that redirects to '/'
        """
        response = self.client.get("/")
        self.assertContains(response, 'class="navbar-brand"')
        self.assertContains(response, 'href="/"') 
        self.assertContains(response, "Binge and Bosses")

    def test_login_link_exists(self):
        """
            Test that on the navbar at the index, there exists 
            the 'login' link that will redirect to '/accounts/login' 
        """
        response = self.client.get("/")
        self.assertContains(response, reverse("login"))
        self.assertContains(response, "Login")

    def test_signup_link_exists(self):
        """
            Test that the signup link in the navbar exists
        """
        response = self.client.get("/")
        self.assertContains(response, reverse("signup"))
        self.assertContains(response, "Signup")

    def test_logout_and_greeting_are_hidden(self):
        """
            Test that, when you are not logged in, you do not see indicators
            of authentication
        """
        response = self.client.get("/")
        self.assertNotContains(response, reverse("logout"))
        self.assertNotContains(response, "Welcome,")

    def test_login_link_not_active(self):
        response = self.client.get("/")
        self.assertNotContains(response, 'auth-login-logout active')

    def test_settings_dropdown_is_hidden(self):
        """
            Test that when not logged in you cannot see 'settings' tab
        """
        response = self.client.get("/")
        self.assertNotContains(response, "Settings")
        self.assertNotContains(response, reverse("profiles:change_username"))

class NavBarAuthenticated(TestCase):
    """
        Basic Tests for when a user is authenticated
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="tester", password="testpass123"
        )
        self.client.force_login(self.user)

    def test_greeting_appears(self):
        """
            Test that the greeting appears in the navbar when authenticated
        """
        response = self.client.get("/")
        self.assertContains(response, "Welcome, tester")

    def test_logout_form_is_shown(self):
        """
            Test that the logout functionality is there
        """
        response = self.client.get("/")
        self.assertContains(response, f'action="{reverse("logout")}"')
        self.assertContains(response, "Logout")
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_login_link_is_hidden(self):
        """
            Test that the login button no longer exists once authenticated
        """
        response = self.client.get("/")
        self.assertNotContains(response, "Login")

    def test_library_link_is_shown(self):
        """
            Test that both the word Library and the link to Library are present
        """
        response = self.client.get("/")
        self.assertContains(response, reverse("library"))
        self.assertContains(response, "Library")

    def test_search_link_is_shown(self):
        """
            Test that both the word Search and the link to library are present
        """
        response = self.client.get("/")
        self.assertContains(response, reverse("game_search"))
        self.assertContains(response, "Search")

    def test_settings_link_visible(self):
        """
            Test that when you are logged in, the settings tab exists
        """
        response = self.client.get("/")
        self.assertContains(response, "Settings")
        self.assertContains(response, reverse("profiles:change_username"))
        self.assertContains(response, "Change Username")