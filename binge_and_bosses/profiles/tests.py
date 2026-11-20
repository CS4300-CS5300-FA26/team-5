from django.test import TestCase, override_settings
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from .models import Profile
# Create your tests here.

User = get_user_model()
PASSWORD = "1FindY0urL@ckoFP@$$w0RDSD1$turbing"
NEW_PASSWORD = "Sw33t-Dee-Is-a-B1rd!"
CHANGE_USERNAME_TEMPLATE = "profiles/change_username.html"
DIFFERENT_USERNAME = "dennis_reynolds"
CHANGE_AVATAR_TEMPLATE = "profiles/change_avatar.html"

TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def make_image(filename="avatar.png", image_format="PNG"):
    """
    Function that makes an image in memory
    """
    buffer = BytesIO()
    Image.new("RGB", (10, 10), "red").save(buffer, image_format)
    return SimpleUploadedFile(filename, buffer.getvalue())


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
        Test that if an authenticated user tries to access the change username page,
        they become redirected to 'login'
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
        return self.client.post(
            self.url, {"old_password": old, "new_password1": new, "new_password2": new if confirm is None else confirm}
        )

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
        Test that a user can successfully change their password when both new passwords match
        and old password is correct
        """
        self.login()
        response = self.client.post(
            self.url,
            {"old_password": PASSWORD, "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
            follow=True,
        )
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


class ChangeAvatarTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        override = override_settings(MEDIA_ROOT=self.media_root, STORAGES=TEST_STORAGES)
        override.enable()

        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, True)

        self.user = User.objects.create_user(username="dee", email="dee@paddyspub.com", password=PASSWORD)
        self.other_user = User.objects.create_user(username="frank", email="frank@paddyspub.com", password=PASSWORD)
        self.url = reverse("profiles:change_avatar")

    def login(self, user):
        """
        Helper function to login a user
        """
        self.client.login(username=user, password=PASSWORD)

    def upload(self, image=None, **kargs):
        """
        Post an image to the change avatar page, creates PNG if none is supplied
        """
        return self.client.post(self.url, {"avatar": image or make_image()}, **kargs)

    def test_profile_is_created_automatically(self):
        """
        Test that when creating a new user, their profile is automatically generated
        """
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_anonymous_get_redirected(self):
        """
        Test that if an unauthenticated user tries to access the change avatar page, they are redirected to login
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.LOGIN_URL, response["Location"])

    def test_anonymous_post_changes_nothing(self):
        """
        Test that if an unauthenticated user sends a POST request to upload an avatar, nothing is saved
        """
        response = self.upload()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Profile.objects.get(user=self.user).avatar)

    def test_page_loads_for_authenticated_user(self):
        """
        Test that an authenticated user can load the change avatar page using the correct template
        """
        self.login("dee")
        response = self.upload(follow=True)
        self.assertRedirects(response, self.url)
        self.assertContains(response, "Avatar updated.")

        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.avatar.name, f"avatars/user_{self.user.id}.png")
        self.assertTrue(Path(profile.avatar.path).exists())

    def test_non_image_rejected(self):
        """
        Test that if a file which is not a valid image is rejected
        """
        self.login("dee")

        fake = SimpleUploadedFile("not_an_image.png", b"this is not an image")
        response = self.upload(fake)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["avatar"])
        self.assertFalse(Profile.objects.get(user=self.user).avatar)

    def test_image_over_limit_is_rejected(self):
        """
        Test that an image larger than the size limit is rejected
        """
        self.login("dee")

        # lower the size limit rather than creating a big image
        with patch("profiles.forms.MAX_AVATAR_MB", 0.000000001):
            response = self.upload()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Image must be smaller than")
        self.assertFalse(Profile.objects.get(user=self.user).avatar)

    def test_empty_upload_changes_nothing(self):
        """
        Test that submitting the form with no file does not alter the profile
        """
        self.login("dee")
        self.upload()

        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Profile.objects.get(user=self.user).avatar)

    def test_replacing_avatar_deletes_old_file(self):
        """
        Test that replacing an avatar with a different file type does not leave an orphaned old file
        """
        self.login("dee")

        self.upload(make_image("first.png", "PNG"))
        old_path = Path(Profile.objects.get(user=self.user).avatar.path)
        self.assertTrue(old_path.exists())

        self.upload(make_image("second.jpg", "JPEG"))
        profile = Profile.objects.get(user=self.user)

        self.assertEqual(profile.avatar.name, f"avatars/user_{self.user.id}.jpg")
        self.assertFalse(old_path.exists())

    def test_remove_avatar(self):
        """
        Test that removing an avatar clears the field and deletes the file from FS
        """
        self.login("dee")
        self.upload()
        path = Path(Profile.objects.get(user=self.user).avatar.path)

        response = self.client.post(self.url, {"remove": "1"}, follow=True)
        self.assertRedirects(response, self.url)
        self.assertContains(response, "Avatar removed.")
        self.assertFalse(Profile.objects.get(user=self.user).avatar)
        self.assertFalse(path.exists())

    def test_remove_with_no_avatar_does_not_crash(self):
        """
        Test that removing an avatar when the user does not have one does not crash the application
        """
        self.login("dee")
        response = self.client.post(self.url, {"remove": "1"})
        self.assertEqual(response.status_code, 302)

    def test_avatar_stays_after_username_change(self):
        """
        Test that the avatar is still associated with the profile even if a user changes their username
        """
        self.login("dee")
        self.upload()

        self.client.post(reverse("profiles:change_username"), {"username": DIFFERENT_USERNAME})

        self.user.refresh_from_db()
        self.assertTrue(self.user.profile.avatar)

    def test_navbar_shows_custom_avatar(self):
        """
        Test that the navbar shows the uploaded image rather than the placeholder
        """
        self.login("dee")
        self.upload()

        response = self.client.get(self.url)
        profile = Profile.objects.get(user=self.user)
        self.assertContains(response, 'class="avatar avatar-sm"')
        self.assertContains(response, profile.avatar.url)
        self.assertNotContains(response, "avatar-sm avatar-placeholder")

    def test_settings_dropdown_has_change_avatar_link(self):
        """
        Test that the settings dropdown in the navbar links to the change avatar page
        """
        self.login("dee")
        response = self.client.get(self.url)
        self.assertContains(response, "Change Avatar")
        self.assertContains(response, f'href="{self.url}"')

    def test_user_cannot_change_other_user_avatar(self):
        """
        Test that uploading an avatar only changes the logged in user's profile and not another users
        """
        self.login("dee")
        self.client.post(self.url, {"avatar": make_image(), "user": self.other_user.pk})
        self.assertTrue(Profile.objects.get(user=self.user).avatar)
        self.assertFalse(Profile.objects.get(user=self.other_user).avatar)

    def test_deleting_user_deletes_avatar_file(self):
        """
            Test that deleting a user also deletes their avatar file from the disk
        """
        self.login("dee")
        self.upload()
        path = Path(Profile.objects.get(user=self.user).avatar.path)
        self.assertTrue(path.exists())

        self.user.delete()
        self.assertFalse(path.exists())

    def test_deleting_profile_deletes_avatar_file(self):
        """
            Test that when deleiting a profile directly it also removes the avatar file from the disk
        """
        self.login("dee")
        self.upload()
        profile = Profile.objects.get(user=self.user)
        path = Path(profile.avatar.path)

        profile.delete()
        self.assertFalse(path.exists())

