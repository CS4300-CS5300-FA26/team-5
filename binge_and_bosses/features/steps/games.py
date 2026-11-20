"""
    Steps for searching and opening game details (stories #9 and #10).
    IGDB is faked in environment.py for scenarios tagged @fake_igdb.
"""
from behave import given, when, then
from bs4 import BeautifulSoup
from django.urls import reverse


def matching_games(context):
    # A description finds what the fake search by description returns; a title finds the games named like it
    if getattr(context, "mode", "") == "describe":
        return context.search_by_description(context.query)[0]
    return [game for game in context.fake_games if context.query.lower() in game["name"].lower()]


@given('I search "{query}"')
def search_for_title(context, query):
    context.query = query


@given("I search a string that matches no game title")
def search_without_matches(context):
    search_for_title(context, "no-such-game")


@given('I describe "{description}"')
def describe_a_game(context, description):
    context.query = description
    context.mode = "describe"


@given("the description can't be read")
def description_fails(context):
    context.search_by_description.side_effect = None
    context.search_by_description.return_value = None


@when("results load")
def load_results(context):
    params = {"q": context.query, "mode": getattr(context, "mode", "")}
    context.response = context.test.client.get(reverse("game_search"), params)


@then("I see games with matching titles and cover art")
def matching_titles_and_covers(context):
    context.test.assertEqual(context.response.status_code, 200)
    page = BeautifulSoup(context.response.content, "html.parser")
    context.test.assertTrue(matching_games(context), "No fake game matches the search")
    for game in matching_games(context):
        context.test.assertContains(context.response, game["name"])
        context.test.assertIsNotNone(page.find("img", attrs={
            "src": game["cover"], "alt": game["name"],
        }))


@then("I see what the search looked for")
def see_what_search_looked_for(context):
    page = BeautifulSoup(context.response.content, "html.parser")
    labels = [pill.get_text() for pill in page.select(".search-wanted .pill")]
    context.test.assertEqual(labels, ["Role-playing (RPG)", "Game Boy"])


@given("search results are on the screen")
def search_results_on_screen(context):
    search_for_title(context, "Pokemon")
    load_results(context)
    matching_titles_and_covers(context)


@given("the game database is unavailable")
def igdb_unavailable(context):
    for fake in (context.search_game, context.get_game_details):
        fake.side_effect = None
        fake.return_value = None


@when("I click a game")
def click_game(context):
    page = BeautifulSoup(context.response.content, "html.parser")
    link = page.select_one("article h2 a")
    context.test.assertIsNotNone(link, "No game link in the search results")
    context.game = matching_games(context)[0]
    context.response = context.test.client.get(link["href"], follow=True)


@then("I see its cover, genre(s), platform(s), and description")
def game_details(context):
    context.test.assertContains(context.response, context.game["name"])
    page = BeautifulSoup(context.response.content, "html.parser")
    context.test.assertIsNotNone(page.find("img", attrs={
        "src": context.game["cover"], "alt": context.game["name"],
    }))
    context.test.assertContains(context.response, context.game["summary"])
    for name in context.game["genres"] + context.game["platforms"]:
        context.test.assertContains(context.response, name)


@then("I stay on the search results")
def stay_on_search_results(context):
    context.test.assertRedirects(context.response, reverse("game_search", query={"q": context.query}))
    matching_titles_and_covers(context)


@given("a game has no description or cover")
def missing_fields(context):
    context.game = context.fake_game
    context.game.update(summary="", cover="")


@when("I open its details page")
def open_details(context):
    context.response = context.test.client.get(reverse("game_details", args=[context.game["id"]]))


@then("I see a default cover")
def default_cover(context):
    page = BeautifulSoup(context.response.content, "html.parser")
    context.test.assertIsNotNone(page.find("img", attrs={
        "src": "/static/games/cover-placeholder.svg", "alt": "No cover available",
    }))
