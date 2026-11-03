"""
    Steps for adding games to the library.
    RAWG is faked in environment.py for scenarios tagged @fake_rawg.
"""
from behave import given, when, then
from bs4 import BeautifulSoup
from django.urls import reverse

from games.models import Catalog, Game


def game_id(context):
    return context.fake_game["id"]


def game_page(context):
    return context.test.client.get(reverse("game_details", args=[game_id(context)]))

def form_for(response, url_name, args):
    page = BeautifulSoup(response.content, "html.parser")
    return page.find("form", action=reverse(url_name, args=args))

def add_form(response, rawg_id):
    return form_for(response, "add_to_library", [rawg_id])


def is_logged_in(context):
    return "_auth_user_id" in context.test.client.session


@given("I am logged in on a game page")
def logged_in_on_game_page(context):
    context.execute_steps("Given I am logged in")
    context.response = game_page(context)
    context.test.assertEqual(context.response.status_code, 200)


@given("the game is already in my library")
def game_already_in_library(context):
    context.execute_steps("Given I am logged in")
    data = context.fake_game
    game = Game.objects.create(
        rawg_id=data["id"],
        game_title=data["name"],
        game_description=data["description_raw"],
        game_rating=data["rating"],
    )
    Catalog.objects.create(user=context.user, games=game)



@when('I click "Add to library"')
def click_add_to_library(context):
    context.game_page = game_page(context)
    form = add_form(context.game_page, game_id(context))
    if form is None:
        # Logged-out visitors have no button, so send the request it would have sent
        context.test.assertFalse(is_logged_in(context), 'No "Add to library" form on the game page')
        context.response = context.test.client.post(reverse("add_to_library", args=[game_id(context)]))
        return
    context.test.assertIsNotNone(form.find("button", string="Add to library"))
    context.response = context.test.client.post(form["action"])


@when("I open its page")
def open_game_page(context):
    context.response = game_page(context)


@then('the game appears in my library as "{status}"')
def game_in_library_with_status(context, status):
    context.test.assertRedirects(
        context.response, reverse("game_details", args=[game_id(context)]),
        fetch_redirect_response=False,
    )
    entry = Catalog.objects.get(user=context.user, games__rawg_id=game_id(context))
    context.test.assertEqual(entry.get_status_display(), status)

    library = context.test.client.get(reverse("library"))
    context.test.assertContains(library, context.fake_game["name"])
    context.test.assertContains(library, f"Status: {status}")


@then('the button reads "{label}" and cannot add a duplicate')
def in_library_no_duplicate(context, label):
    context.test.assertContains(context.response, label)
    remove = form_for(context.response, "remove_from_library", [game_id(context)])
    context.test.assertIsNotNone(remove, 'No "Remove from library" form on the page')
    context.test.assertEqual(remove.get("method", "").lower(), "post")
    context.test.assertIsNotNone(remove.find("button", string="Remove from library"))
    context.test.assertIsNone(
        add_form(context.response, game_id(context)),
        'The page still shows an "Add to library" form',
    )
    # Even a direct second add must not create a second entry
    context.test.client.post(reverse("add_to_library", args=[game_id(context)]))
    context.test.assertEqual(
        Catalog.objects.filter(user=context.user, games__rawg_id=game_id(context)).count(), 1
    )


@then("I am asked to log in and nothing is added")
def asked_to_log_in(context):
    add_url = reverse("add_to_library", args=[game_id(context)])
    context.test.assertRedirects(
        context.response, f"{reverse('login')}?next={add_url}", fetch_redirect_response=False
    )
    context.test.assertContains(context.game_page, "Log in to add to your library")
    context.test.assertFalse(Catalog.objects.exists())
    context.test.assertFalse(Game.objects.exists())