"""
    Steps shared by many features: visiting pages, being logged in, and checking
    what the page shows. Check here before adding a step to another file, since
    two steps with the same text cause an error.
"""
from behave import given, then
from django.contrib.auth import get_user_model
from django.urls import reverse

# Page names used in feature files, mapped to URL names
PAGES = {
    "sign-up": "signup",
    "login": "login",
}

PASSWORD = "Gr8Backlog!42"


@given("I am on the {page} page")
def visit_page(context, page):
    context.response = context.test.client.get(reverse(PAGES[page]))
    context.test.assertEqual(context.response.status_code, 200)


@given("I am logged in")
def logged_in(context):
    context.user = get_user_model().objects.create_user(
        username="player_one", email="player@example.com", password=PASSWORD
    )
    context.test.client.force_login(context.user)


@then('I see "{text}"')
def see_text(context, text):
    context.test.assertContains(context.response, text)


@then('I see the error "{message}"')
def see_error(context, message):
    context.test.assertContains(context.response, message)
