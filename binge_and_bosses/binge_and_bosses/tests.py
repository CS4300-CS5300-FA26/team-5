import json
import os
import subprocess
import sys

from django.conf import settings
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
        self.assertNotContains(response, "auth-login-logout active")

    def test_settings_dropdown_is_hidden(self):
        """
        Test that when not logged in you cannot see 'settings' tab
        """
        response = self.client.get("/")
        self.assertNotContains(response, "Settings")
        self.assertNotContains(response, reverse("profiles:change_username"))
        self.assertNotContains(response, reverse("profiles:change_password"))


class NavBarAuthenticated(TestCase):
    """
    Basic Tests for when a user is authenticated
    """

    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="testpass123")
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
        self.assertContains(response, "Change Password")

class HttpsSettingsTests(TestCase):
    """Heroku sets DYNO on every dyno; there the site is HTTPS only. Locally it stays plain HTTP."""

    def load_settings(self, **env):
        # Import settings in a fresh process, since they're read once at startup.
        code = (
            "import json; from django.conf import settings as s; print(json.dumps([s.SECURE_PROXY_SSL_HEADER,"
            " s.SECURE_SSL_REDIRECT, s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE]))"
        )
        clean_env = {key: value for key, value in os.environ.items() if key != "DYNO"}
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=settings.BASE_DIR,
            env={**clean_env, "DJANGO_SETTINGS_MODULE": "binge_and_bosses.settings", **env},
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_heroku_redirects_to_https_and_uses_secure_cookies(self):
        proxy_header, redirect, session_secure, csrf_secure = self.load_settings(DYNO="web.1")
        self.assertEqual(proxy_header, ["HTTP_X_FORWARDED_PROTO", "https"])
        self.assertTrue(redirect)
        self.assertTrue(session_secure)
        self.assertTrue(csrf_secure)

    def test_local_runs_stay_on_http(self):
        proxy_header, redirect, session_secure, csrf_secure = self.load_settings()
        self.assertIsNone(proxy_header)
        self.assertFalse(redirect)
        self.assertFalse(session_secure)
        self.assertFalse(csrf_secure)


class CloudinarySettingsTests(TestCase):
    """Turning on Cloudinary for uploads must not break the Heroku build or static files."""

    def run_with_cloudinary(self, *args):
        # Settings are read once at startup, so each check runs in a fresh process.
        return subprocess.run(
            [sys.executable, *args],
            cwd=settings.BASE_DIR,
            env={
                **os.environ,
                "DJANGO_SETTINGS_MODULE": "binge_and_bosses.settings",
                "DEBUG": "False",
                "REDIS_URL": "redis://127.0.0.1:1/0",
                "CLOUDINARY_CLOUD_NAME": "test-cloud",
                "CLOUDINARY_API_KEY": "test-key",
                "CLOUDINARY_API_SECRET": "test-secret",
            },
            capture_output=True,
            text=True,
            check=False,
        )

    def test_collectstatic_runs_with_cloudinary_vars(self):
        result = self.run_with_cloudinary("manage.py", "collectstatic", "--noinput", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr[-500:])

    def test_static_tags_work_with_cloudinary_vars_and_no_manifest(self):
        # Heroku may build the slug before the Cloudinary vars exist, so no manifest is written.
        code = (
            "import django; django.setup(); from django.templatetags.static import static;"
            " print(static('css/navbar.css'))"
        )
        result = self.run_with_cloudinary("-c", code)
        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        self.assertEqual(result.stdout.strip(), "/static/css/navbar.css")
