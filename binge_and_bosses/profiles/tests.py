from django.test import TestCase
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

# Create your tests here.

User = get_user_model()
PASSWORD = "1FindY0urL@ckoFP@$$w0RDSD1$turbing"
NEW_PASSWORD = "Sw33t-Dee-Is-a-B1rd!"
CHANGE_USERNAME_TEMPLATE = "profiles/change_username.html"
DIFFERENT_USERNAME = "dennis_reynolds"

class ChangeUsernameTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dennis", email="dennis@paddyspub.com", password=PASSWORD)
        self.other = User.objects.create_user(username="charlie", email="charlie@paddyspub.com", password=PASSWORD)
        self.url = reverse("profiles:change_username")

    def login(self):
        """
            Function that logs in the "dennis" user
        """
        self.client.login(username="dennis", password=PASSWORD)

    def test_anonymous_get_redirected(self):
        """
            Test that if an authenticated user tries to access the change username page, they become redirected to 'login'
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.LOGIN_URL, response["Location"])

    def test_anonymous_post_changes_nothing(self):
        """
            Test that if someone sends a POST request to change a username, it does nothing
        """
        response = self.client.post(self.url, {"username": "Dr.Mantis-Toboggan"})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "dennis")

    def test_current_user_is_prefilled(self):
        """
            Test that the current user is prefilled in the area where you change your username
        """
        self.login()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, CHANGE_USERNAME_TEMPLATE)
        self.assertEqual(response.context["form"].initial["username"], "dennis")
        self.assertContains(response, "dennis")

    def test_successful_username_change(self):
        """
            Test that a successful username that meets the rules successfully changes the user's name
        """
        self.login()
        response = self.client.post(self.url, {"username": DIFFERENT_USERNAME}, follow=True)
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, DIFFERENT_USERNAME)
        self.assertContains(response, "Your username has been updated!")

    def test_user_stays_logged_in_after_change(self):
        """
            Test that the user does not become logged out after changing the username
        """
        self.login()
        self.client.post(self.url, {"username": DIFFERENT_USERNAME})
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_old_username_is_allowed(self):
        """
            Test that the old username is allowed to be used when changing the username
        """
        self.login()
        response = self.client.post(self.url, {"username": "dennis"})
        self.assertEqual(response.status_code, 302)

    def test_duplicate_username_fails(self):
        """
            Test that you cannot name yourself after a user that already exists
        """
        self.login()
        response = self.client.post(self.url, {"username": "charlie"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That username is taken.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "dennis")

    def test_duplicate_username_is_case_insensitive(self):
        """
            Test that even if you make a character uppercase it still doesnt change the name if another user 
            with that name exists
        """
        self.login()
        response = self.client.post(self.url, {"username": "Charlie"})
        self.assertContains(response, "That username is taken.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "dennis")

    def test_empty_user_is_rejected(self):
        """
            Test you cannot leave username field empty
        """
        self.login()
        response = self.client.post(self.url, {"username": ""})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["username"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "dennis")

    def test_invalid_char_rejected(self):
        """
            Test you cannot name yourself after invalid characters (i.e. having a space in the username)
        """
        self.login()
        response = self.client.post(self.url, {"username": "Frank Reynolds"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["username"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "dennis")

    def test_user_cant_change_other_user_username(self):
        """
            Test that you cannot change another user's username when authenticated as your own user
        """
        self.login()
        self.client.post(self.url, {"username": "DENNIS", "id": self.other.pk})
        self.other.refresh_from_db()
        self.assertEqual(self.other.username, "charlie")

    def test_too_long_username_rejected(self):
        """
            Test that you bounds are enforced. 
        """
        self.login()
        response = self.client.post(self.url, {"username": "d" * 151})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["username"])

class ChangePasswordTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="Mac", email="mac@paddyspub.com", password=PASSWORD)
        self.url = reverse("profiles:change_password")

    def login(self):
        """
            Function that logs in the 'Mac' user
        """
        self.client.login(username="Mac", password=PASSWORD)

    def post_password_change(self, old=PASSWORD, new=NEW_PASSWORD, confirm=None):
        """
            Change the password. If confirm is None then have the password match, else use confirm as second password
        """
        return self.client.post(self.url, {
            "old_password": old,
            "new_password1": new,
            "new_password2": new if confirm is None else confirm
        })

    def test_anonymous_redirect_to_login(self):
        """
            Test that if an unauthenticated user manually tries to go to this URL they are redirected
            to the login page
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.LOGIN_URL, response["Location"])

    def test_anonymous_post_changes_nothing(self):
        response = self.post_password_change()
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_password_values_are_not_rendered_back(self):
        """
            Test that the password values are not rendered back to the user
        """
        self.login()
        response = self.post_password_change(confirm="something-else-entirely")
        self.assertNotContains(response, NEW_PASSWORD)
        self.assertNotContains(response, PASSWORD)

    def test_successful_password_change(self):
        """
            Test that a user can successfully change their password when both new passwords match and old password is correct
        """
        self.login()
        response = self.client.post(self.url, {
            "old_password": PASSWORD,
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD
        }, follow=True)
        self.assertRedirects(response, self.url)
        self.assertContains(response, "Your password has been updated!")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_user_stays_logged_in_after_change(self):
        """
            Test that the user stays logged in after a successful password change
        """
        self.login()
        self.post_password_change()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_old_password_stops_working_after_change(self):
        """
            Test that the old password no longer logs the user in once they successfully change their password
        """
        self.login()
        self.post_password_change()
        self.client.logout()
        self.assertFalse(self.client.login(username="Mac", password=PASSWORD))
        self.assertTrue(self.client.login(username="Mac", password=NEW_PASSWORD))

    def test_wrong_current_rejected(self):
        """
            Test that when the user enters the wrong current password, it is rejected
        """
        self.login()
        response = self.post_password_change(old="notthepassword")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["old_password"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_confirmation_mismatch_rejected(self):
        """
            Test that when the user enters 2 different passwords when changing it fails
        """
        self.login()
        response = self.post_password_change(confirm="Different-P@$$w0rd")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["new_password2"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_password_too_short(self):
        """
            Test that if the password is not enough characters long, it is rejected
        """
        self.login()
        response = self.post_password_change(new="aB!")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["new_password2"])

    def test_common_password(self):
        """
            Test that a common password is rejected
        """
        self.login()
        response = self.post_password_change(new="password")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["new_password2"])

    def test_numeric_only_password(self):
        """
            Test that only numeric passwords are rejected
        """
        self.login()
        response = self.post_password_change(new="289123908341092")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["new_password2"])

    def test_empty_fields(self):
        """
            Test that when leaving the fields empty it rejects
        """
        self.login()
        response = self.post_password_change(old="", new="")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)