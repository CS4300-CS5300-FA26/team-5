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
        self.assertContains(response, ">Login</a>")

    def test_logout_and_greeting_are_hidden(self):
        """
            Test that, when you are not logged in, you do not see indicators
            of authentication
        """
        response = self.client.get("/")
        self.assertNotContains(response, reverse("logout"))
        self.assertNotContains(response, "Hello There")
        self.assertNotContains(response, reverse("logout"))

    def test_login_link_not_active(self):
        response = self.client.get("/")
        self.assertNotContains(response, 'aria-current=page')

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
        self.assertContains(response, "Hello There, tester")

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
        self.assertNotContains(response, ">Login</a>")

