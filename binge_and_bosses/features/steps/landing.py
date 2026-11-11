"""
    Steps for the landing page. Link checks look inside <main>, because the nav bar
    in base.html has its own links.
"""
from behave import then, when
from bs4 import BeautifulSoup
from django.urls import reverse

from common import PAGES


def links(context, scope="main"):
    page = BeautifulSoup(context.response.content, "html.parser").select_one(scope)
    return {a.get_text(" ", strip=True): a["href"] for a in page.select("a[href]")}


@when("I visit the home page")
def visit_home(context):
    context.response = context.test.client.get(reverse("index"))
    context.test.assertEqual(context.response.status_code, 200)


@then("I see what Binge & Bosses is for")
def see_pitch(context):
    heading = BeautifulSoup(context.response.content, "html.parser").select_one("main h1")
    context.test.assertIsNotNone(heading, "The home page has no heading")
    context.test.assertIn("save file", heading.get_text(" ", strip=True))


@then('I see a "{first}" link and a "{second}" link')
def see_two_links(context, first, second):
    found = links(context)
    context.test.assertIn(first, found)
    context.test.assertIn(second, found)


@when('I follow "{text}"')
def follow_link(context, text):
    context.response = context.test.client.get(links(context)[text])


@then("I am on the {page} page")
def on_page(context, page):
    context.test.assertEqual(context.response.status_code, 200)
    context.test.assertEqual(context.response.request["PATH_INFO"], reverse(PAGES[page]))


@then("I see links to my library and to search")
def see_player_links(context):
    hrefs = links(context).values()
    context.test.assertIn(reverse("library"), hrefs)
    context.test.assertIn(reverse("game_search"), hrefs)


@then('I do not see a "Sign up" link')
def no_sign_up_link(context):
    context.test.assertNotIn(reverse("signup"), links(context, "body").values())
