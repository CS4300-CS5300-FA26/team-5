"""
    Steps for changing a game's play status (story #12).
    RAWG is faked in environment.py for scenarios tagged @fake_rawg.
"""
from behave import given, when, then
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.urls import reverse

from common import PASSWORD
from games.models import Catalog, Game
from reviews import submit_review

STATUS_VALUES = {label: value for value, label in Catalog.Status.choices}


@given('a game in my library marked "{status}"')
def game_in_library_marked(context, status):
    context.execute_steps("Given a game in my library")
    context.entry.status = STATUS_VALUES[status]
    context.entry.save()


@given('a game marked "{status}"')
def game_marked(context, status):
    game_in_library_marked(context, status)
    context.entry.rating = 4
    context.entry.review = "Enjoyed the early hours."
    context.entry.save()


@when('I change its status to "{status}"')
@when('I mark it "{status}"')
def change_play_status(context, status):
    context.expected_status = status
    submit_review(context, status=status)


@then('my library shows it under "{status}"')
def library_shows_under_status(context, status):
    context.entry.refresh_from_db()
    context.test.assertEqual(context.entry.get_status_display(), status)
    page = BeautifulSoup(context.test.client.get(reverse("library")).content, "html.parser")
    article = page.find("article")
    context.test.assertIsNotNone(article, "No library entry shown on the library page")
    context.test.assertIn(context.fake_game["name"], article.get_text())
    context.test.assertIn(f"Status: {status}", article.get_text())


@then('it leaves "{old_status}"')
def leaves_old_status(context, old_status):
    library_shows_under_status(context, context.expected_status)
    library = context.test.client.get(reverse("library"))
    context.test.assertNotContains(library, f"Status: {old_status}")


@then("its rating and review are kept")
def rating_and_review_kept(context):
    context.entry.refresh_from_db()
    context.test.assertEqual(context.entry.rating, 4)
    context.test.assertEqual(context.entry.review, "Enjoyed the early hours.")
    context.test.assertFalse(context.entry.review_edited)
    context.test.assertContains(context.response, "Rating: 4/5")
    context.test.assertContains(context.response, "Enjoyed the early hours.")
    library = context.test.client.get(reverse("library"))
    context.test.assertContains(library, "Rating: 4/5")


@when("I try to change a status")
def try_to_change_status_logged_out(context):
    data = context.fake_game
    owner = get_user_model().objects.create_user(
        username="owner", email="owner@example.com", password=PASSWORD
    )
    game = Game.objects.create(
        rawg_id=data["id"],
        game_title=data["name"],
        game_description=data["description_raw"],
        game_rating=data["rating"],
    )
    context.entry = Catalog.objects.create(
        user=owner,
        games=game,
        status=Catalog.Status.NOT_STARTED,
        rating=4,
        review="Owner review.",
    )
    save_url = reverse("save_review", args=[data["id"]])
    context.game_page = context.test.client.get(reverse("game_details", args=[data["id"]]))
    page = BeautifulSoup(context.game_page.content, "html.parser")
    context.test.assertIsNone(
        page.find("form", action=save_url),
        "Logged-out visitor should not see the status form",
    )
    context.response = context.test.client.post(save_url, {"status": Catalog.Status.PLAYING})


@then("I am asked to log in and nothing changes")
def asked_to_log_in_nothing_changes(context):
    save_url = reverse("save_review", args=[context.fake_game["id"]])
    context.test.assertRedirects(
        context.response, f"{reverse('login')}?next={save_url}", fetch_redirect_response=False
    )
    context.entry.refresh_from_db()
    context.test.assertEqual(context.entry.status, Catalog.Status.NOT_STARTED)
    context.test.assertEqual(context.entry.rating, 4)
    context.test.assertEqual(context.entry.review, "Owner review.")
