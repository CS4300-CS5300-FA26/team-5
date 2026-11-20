"""
    Steps for searching and opening game details (stories #9 and #10).
    IGDB is faked in environment.py for scenarios tagged @fake_igdb.
"""
from behave import given, when, then
from bs4 import BeautifulSoup
from django.urls import reverse


def matching_games(context):
    return [game for game in context.fake_games if context.query.lower() in game["name"].lower()]


@given('I search "{query}"')
def search_for_title(context, query):
    context.query = query


@given("I search a string that matches no game title")
def search_without_matches(context):
    search_for_title(context, "no-such-game")


@when("results load")
def load_results(context):
    context.response = context.test.client.get(reverse("game_search"), {"q": context.query})


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


@given('IGDB has {count:d} games matching "{query}"')
def many_matches(context, count, query):
    context.fake_games = [
        {"id": i, "name": f"{query} {i}", "released": None, "cover": ""} for i in range(1, count + 1)
    ]


@when("I choose to show {per_page:d} results per page")
def choose_page_size(context, per_page):
    context.response = context.test.client.get(reverse("game_search"), {"q": context.query, "per_page": per_page})


@then("I see results {first:d} to {last:d} of {total:d}")
def see_results(context, first, last, total):
    page = BeautifulSoup(context.response.content, "html.parser")
    titles = [link.get_text(strip=True) for link in page.select("article h2 a")]
    context.test.assertEqual(titles, [f"{context.query} {i}" for i in range(first, last + 1)])
    context.test.assertIn(f"{first}–{last} of {total} results", page.select_one(".search-count").get_text())


@when("I go to page {number:d}")
def go_to_page(context, number):
    form = BeautifulSoup(context.response.content, "html.parser").select_one(".search-pages form")
    context.test.assertIsNotNone(form, "No page box on the search results")
    fields = {field["name"]: field.get("value", "") for field in form.select("input[name]")}
    context.response = context.test.client.get(reverse("game_search"), {**fields, "page": number})
