"""Steps for searching and opening game details (stories #9 and #10)."""
from unittest.mock import patch

from behave import given, when, then
from bs4 import BeautifulSoup
from django.urls import reverse


def fake_rawg(context):
    context.game = {
        "id": 1, "name": "Pokemon Red",
        "background_image": "https://example.com/pokemon-red.jpg",
        "description_raw": "Explore Kanto and catch Pokemon.",
        "genres": [{"name": "Adventure"}, {"name": "RPG"}],
        "platforms": [{"platform": {"name": "Game Boy"}}],
    }
    context.games = [context.game, dict(
        context.game, id=2, name="Pokemon Blue",
        background_image="https://example.com/pokemon-blue.jpg",
    )]
    for name, answer in [("search_game", context.games), ("get_game_details", context.game)]:
        replacement = patch(f"games.views.{name}", return_value=answer)
        setattr(context, name, replacement.start())
        context.add_cleanup(replacement.stop)


@given('I search "{query}"')
def search_for_title(context, query):
    fake_rawg(context)
    context.query = query


@given("I search a string that matches no game title")
def search_without_matches(context):
    search_for_title(context, "no-such-game")
    context.search_game.return_value = []


@when("results load")
def load_results(context):
    context.response = context.test.client.get(reverse("game_search"), {"q": context.query})


@then("I see games with matching titles and cover art")
def matching_titles_and_covers(context):
    context.test.assertEqual(context.response.status_code, 200)
    page = BeautifulSoup(context.response.content, "html.parser")
    for game in context.games:
        context.test.assertContains(context.response, game["name"])
        context.test.assertIsNotNone(page.find("img", attrs={
            "src": game["background_image"], "alt": game["name"],
        }))


@given("search results are on the screen")
def search_results_on_screen(context):
    search_for_title(context, "Pokemon")
    load_results(context)
    matching_titles_and_covers(context)


@given("the game database is unavailable")
def rawg_unavailable(context):
    context.search_game.return_value = None
    context.get_game_details.return_value = None


@when("I click a game")
def click_game(context):
    page = BeautifulSoup(context.response.content, "html.parser")
    link = page.select_one("article h2 a")
    context.test.assertIsNotNone(link, "No game link in the search results")
    context.response = context.test.client.get(link["href"], follow=True)


@then("I see its cover, genre(s), platform(s), and description")
def game_details(context):
    context.test.assertContains(context.response, context.game["name"])
    page = BeautifulSoup(context.response.content, "html.parser")
    context.test.assertIsNotNone(page.find("img", attrs={
        "src": context.game["background_image"], "alt": context.game["name"],
    }))
    context.test.assertContains(context.response, context.game["description_raw"])
    for genre in context.game["genres"]:
        context.test.assertContains(context.response, genre["name"])
    for platform in context.game["platforms"]:
        context.test.assertContains(context.response, platform["platform"]["name"])


@then("I stay on the search results")
def stay_on_search_results(context):
    context.test.assertRedirects(context.response, reverse("game_search", query={"q": context.query}))
    matching_titles_and_covers(context)


@given("a game has no description or cover")
def missing_fields(context):
    fake_rawg(context)
    context.game.update(description_raw="", background_image="")


@when("I open its details page")
def open_details(context):
    context.response = context.test.client.get(reverse("game_details", args=[context.game["id"]]))


@then("I see a default cover")
def default_cover(context):
    page = BeautifulSoup(context.response.content, "html.parser")
    context.test.assertIsNotNone(page.find("img", attrs={
        "src": "/static/games/cover-placeholder.svg", "alt": "No cover available",
    }))
