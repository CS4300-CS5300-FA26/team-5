"""
    Steps for signing up, logging in and logging out (stories #7 and #8).
"""
from behave import given, when, then
from django.contrib.auth import get_user_model
from django.urls import reverse

from common import PASSWORD


def sign_up(context, username, email, password):
    return context.test.client.post(reverse("signup"), {
        "username": username,
        "email": email,
        "password1": password,
        "password2": password,
    })


def log_in(context, username, password):
    return context.test.client.post(reverse("login"), {
        "username": username,
        "password": password,
    })


def is_logged_in(context):
    return "_auth_user_id" in context.test.client.session


# Sign-up (#7)

@when("I submit a valid email and password")
def submit_valid_signup(context):
    context.user_count = get_user_model().objects.count()
    context.response = sign_up(context, "new_player", "new@example.com", PASSWORD)


@then("I am logged in and see my empty library")
def logged_in_with_empty_library(context):
    context.test.assertRedirects(context.response, reverse("library"))
    context.test.assertTrue(is_logged_in(context))

    library = context.test.client.get(reverse("library"))
    context.test.assertContains(library, "Your games will show up here soon.")


@given("an account already exists for an email")
def account_with_email(context):
    context.user = get_user_model().objects.create_user(
        username="first_player", email="taken@example.com", password=PASSWORD
    )


@when("I sign up with that email again")
def sign_up_with_taken_email(context):
    context.user_count = get_user_model().objects.count()
    context.response = sign_up(context, "second_player", context.user.email, PASSWORD)


@when("I submit an invalid email format or a password shorter than 8 characters")
def submit_invalid_signup(context):
    row = context.table[0]
    context.user_count = get_user_model().objects.count()
    context.response = sign_up(context, "new_player", row["email"], row["password"])


@then("no new account is created")
@then("no account is created")
def no_account_created(context):
    context.test.assertEqual(get_user_model().objects.count(), context.user_count)
    context.test.assertFalse(is_logged_in(context))


@then('I see an error next to the "{field}" field')
def error_next_to_field(context, field):
    form = context.response.context["form"]
    context.test.assertIn(field, form.errors)


@then("the message does not reveal whether the email is registered")
def signup_message_does_not_reveal_email(context):
    # A taken username with a new email must get the same message as a taken email
    response = sign_up(context, context.user.username, "brand-new@example.com", PASSWORD)
    context.test.assertContains(
        response,
        "Unable to create an account with those details. Try logging in or resetting your password.",
    )


# Log in and log out (#8)

@given("I have a registered account")
def registered_account(context):
    context.user = get_user_model().objects.create_user(
        username="player_one", email="player@example.com", password=PASSWORD
    )


@when("I enter the correct username and password")
def enter_correct_credentials(context):
    context.response = log_in(context, context.user.username, PASSWORD)


@then("I land on my library")
def land_on_library(context):
    context.test.assertRedirects(
        context.response, reverse("library"), fetch_redirect_response=False
    )
    context.test.assertEqual(
        int(context.test.client.session["_auth_user_id"]), context.user.pk
    )


@when('I click "Logout"')
def click_logout(context):
    # The library page must have a logout form; the test client then submits it
    library = context.test.client.get(reverse("library"))
    context.test.assertContains(library, f'action="{reverse("logout")}"')
    context.response = context.test.client.post(reverse("logout"))


@then("I am returned to the login page")
def returned_to_login(context):
    context.test.assertRedirects(
        context.response, reverse("login"), fetch_redirect_response=False
    )
    context.test.assertFalse(is_logged_in(context))


@when("I enter a username or password that does not match an account")
def enter_wrong_credentials(context):
    get_user_model().objects.create_user(username="player_one", password=PASSWORD)
    context.response = log_in(context, "nobody", PASSWORD)
    context.wrong_password_response = log_in(context, "player_one", "not-the-password")
    context.test.assertFalse(is_logged_in(context))


@then("the message does not reveal whether the username is registered")
def login_message_does_not_reveal_username(context):
    # A wrong password for a real account gets the same message as an unknown username
    context.test.assertContains(context.wrong_password_response, context.error_message)
