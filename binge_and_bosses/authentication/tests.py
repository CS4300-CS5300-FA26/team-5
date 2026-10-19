from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

# Create your tests here.
class SignupTests(TestCase):
    """
        Test for the registration functionality
    """
    def setUp(self):
        self.url = reverse("signup")
        self.valid_registration_details = {
            "username": "test_user",
            "email": "test_user@example.com",
            "password1": "SuperSecureP@$swo0RD",
            "password2": "SuperSecureP@$swo0RD"
        }

    def test_signup_page_200(self):
        """
            Test that the signup page loads and uses the correct template
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/signup.html")

    def test_successful_signup(self):
        """
            Test that when entering valid data, the user is in the database
        """
        self.client.post(self.url, self.valid_registration_details)
        self.assertTrue(get_user_model().objects.filter(username="test_user").exists())

    def test_successful_signup_redirect(self):
        """
            Test that a valid signup redirects to the library page
        """
        response = self.client.post(self.url, self.valid_registration_details)
        self.assertRedirects(response, reverse("library"))


    def test_successful_login_after_signup(self):
        """
            Test that once the user signs up, the user is logged in as the newly created user
        """
        response = self.client.post(self.url, self.valid_registration_details)
        user = get_user_model().objects.get(username="test_user")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_mismatched_passwords_fail(self):
        """
            Test that if the user enters 2 different passwords, the user is not created
        """
        invalid_registration_details = {
            "username": "bad_user",
            "email": "bad_user@example.com",
            "password1": "Thisisthefirstpassword",
            "password2": "thisisthefirstpassword"
        }
        response = self.client.post(self.url, invalid_registration_details)

        # NOTE: a failed form just returns a 200 (the same page re-rendered)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username="bad_user").exists())

    def test_unique_usernames(self):
        """
            Ensure that the username of a new user is unique to that user
        """
        get_user_model().objects.create_user(username="test_user", password="mesaapassword")
        response = self.client.post(self.url, self.valid_registration_details)

        # Page should just reload
        self.assertEqual(response.status_code, 200)

        # Make sure only 1 user with the username "test_user" exists within the database
        self.assertEqual(get_user_model().objects.filter(username="test_user").count(), 1)

    def test_password_requirements(self):
        """
            Ensure that weak passwords arent allowed
        """
        data = {**self.valid_registration_details, "password1": "password", "password2": "password"}
        response = self.client.post(self.url, data)

        # Page should reload
        self.assertEqual(response.status_code, 200)

        # Make sure the user didnt get created with a weak password
        self.assertFalse(get_user_model().objects.filter(username="test_user").exists())

    def test_password_was_hashed(self):
        """
            Check that the password was hashed and is not stored in plaintext
        """
        self.client.post(self.url, self.valid_registration_details)
        user = get_user_model().objects.get(username="test_user")

        # Check that the plaintext password is not set as the user's password
        self.assertNotEqual(user.password, "SuperSecureP@$swo0RD")

        # Ensure that the hashed password matches the plaintext password
        self.assertTrue(user.check_password("SuperSecureP@$swo0RD"))

class loginTests(TestCase):
    '''
        Tests for the login functionality
    '''
    def setUp(self):
        self.url = reverse("login")
        self.user = get_user_model().objects.create_user(
            username="user_a",
            email="usera@example.com",
            password="TesTINGp#ass0r0d"
        )

    def test_login_page_200(self):
        """
            Test that the login page resolves and is the login page template
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")

    def test_login_correct_creds(self):
        """
            Test a login with correct credentials
        """
        response = self.client.post(self.url, {
            "username": "user_a",
            "password": "TesTINGp#ass0r0d"
        })

        # Check that we redirect back to user's library
        self.assertRedirects(response, "/library/", fetch_redirect_response=False)

        # Ensure that the session holds this user's ID
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_login_incorrect_pass(self):
        """
            Test that the login does not log a user in when inputting the wrong password
        """
        response = self.client.post(self.url, {
            "username": "user_a",
            "password": "a_wrong_pass!"
        })

        # Check that the login did not redirect but re-rendered
        self.assertEqual(response.status_code, 200)

        # Check the ID
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_with_unregistered_user(self):
        """
            Test that putting an unregistered username does not log the user in
        """
        response = self.client.post(self.url, {
            "username": "unknown",
            "password": "TesTINGp#ass0r0d"
        })