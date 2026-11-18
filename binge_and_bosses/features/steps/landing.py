"""
Steps for the landing page. Link checks look inside <main>, because the nav bar
in base.html has its own links.
"""

from urllib.parse import urljoin

from behave import given, then, when
from bs4 import BeautifulSoup
from django.urls import reverse

from games.models import Catalog, Game

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
    # Resolve the link against the current page, as a browser does (the sort links are "?sort=...")
    here = context.response.request["PATH_INFO"]
    context.response = context.test.client.get(urljoin(here, links(context)[text]))


@then("I am on the {page} page")
def on_page(context, page):
    context.test.assertEqual(context.response.status_code, 200)
    context.test.assertEqual(context.response.request["PATH_INFO"], reverse(PAGES[page]))


@then("I see links to my library and to search")
def see_player_links(context):
    main = BeautifulSoup(context.response.content, "html.parser").select_one("main")
    # The nav bar's Library link counts: an empty library has no library card on the page
    context.test.assertIn(reverse("library"), links(context, "body").values())
    context.test.assertIsNotNone(main.select_one(f'form[action="{reverse("game_search")}"]'))


@then('I do not see a "Sign up" link')
def no_sign_up_link(context):
    context.test.assertNotIn(reverse("signup"), links(context, "body").values())


@given('my library has "{first}" and "{second}"')
def library_has(context, first, second):
    for igdb_id, title in enumerate((first, second), start=1):
        game = Game.objects.create(igdb_id=igdb_id, game_title=title, game_description="", game_rating=4.0)
        Catalog.objects.create(user=context.user, games=game)


@then('I see "{first}" and "{second}" under Recently added')
def recently_added(context, first, second):
    section = BeautifulSoup(context.response.content, "html.parser").select_one("main .home-recent")
    context.test.assertIsNotNone(section, "The home page has no Recently added section")
    titles = [li.get_text(strip=True) for li in section.select("li")]
    context.test.assertEqual(titles, [first, second])
