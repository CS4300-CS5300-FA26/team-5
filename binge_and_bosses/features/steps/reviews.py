"""Rating and review steps. RAWG is faked by the @fake_rawg hook."""
from behave import given, when, then
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.urls import reverse

from games.models import Catalog


@given("a game in my library")
def game_in_my_library(context):
    context.execute_steps("Given the game is already in my library")
    context.entry = Catalog.objects.get(user=context.user, games__rawg_id=context.fake_game["id"])


def submit_review(context, rating=None, review=None):
    url = reverse("game_details", args=[context.fake_game["id"]])
    page = BeautifulSoup(context.test.client.get(url).content, "html.parser")
    form = page.find("form", action=reverse("save_review", args=[context.fake_game["id"]]))
    context.test.assertIsNotNone(form, "No rating and review form on the game page")
    context.test.assertEqual(form.get("method", "").lower(), "post")
    context.test.assertIsNotNone(form.find("button", string="Save"))
    data = {item["name"]: item.get("value", "") for item in form.select('input[type="hidden"][name]')}
    checked = form.select_one('input[name="rating"]:checked')
    if checked:
        data["rating"] = checked["value"]
    if rating is not None:
        radio = form.find("input", attrs={"type": "radio", "name": "rating", "value": str(rating)})
        context.test.assertIsNotNone(radio, f"No radio button for {rating} stars")
        data[radio["name"]] = radio["value"]
    textarea = form.find("textarea", attrs={"name": "review"})
    context.test.assertIsNotNone(textarea, "No review textarea")
    data[textarea["name"]] = textarea.get_text() if review is None else review
    context.response = context.test.client.post(form["action"], data, follow=True)
    context.test.assertRedirects(context.response, url)


@when("I select 4 stars")
def select_four_stars(context):
    submit_review(context, rating=4)


@then("my library shows 4 stars on that game")
def library_shows_rating(context):
    page = BeautifulSoup(context.test.client.get(reverse("library")).content, "html.parser")
    article = page.find("article")
    context.test.assertIn(context.fake_game["name"], article.get_text())
    context.test.assertIn("Rating: 4/5", article.get_text())


@given("a game I have already rated")
def already_rated(context):
    game_in_my_library(context)
    context.entry.rating = 2
    context.entry.save()


@when("I pick a new rating")
def pick_new_rating(context):
    submit_review(context, rating=5)


@then("the old rating is replaced")
def rating_replaced(context):
    context.entry.refresh_from_db()
    context.test.assertEqual(context.entry.rating, 5)
    context.test.assertContains(context.response, "Rating: 5/5")
    context.test.assertNotContains(context.response, "Rating: 2/5")


@when("I save a review")
def save_a_review(context):
    context.review = "Fun to explore and play."
    submit_review(context, review=context.review)


@then("it appears on that game's page under my username")
def review_under_username(context):
    article = BeautifulSoup(context.response.content, "html.parser").find("article")
    context.test.assertEqual(article.h3.get_text(strip=True), context.user.username)
    context.test.assertIn(context.review, article.get_text())


@given("I have a review on a game")
def existing_review(context):
    game_in_my_library(context)
    context.entry.review = "My original review."
    context.entry.save()


@when("I edit and save it")
def edit_review(context):
    context.review = "Even better on a second play."
    submit_review(context, review=context.review)


@then("the new text replaces the old text")
def review_replaced(context):
    context.entry.refresh_from_db()
    context.test.assertEqual(context.entry.review, context.review)
    context.test.assertContains(context.response, context.review)
    context.test.assertNotContains(context.response, "My original review.")


@then('the review shows an "edited" label')
def edited_label(context):
    article = BeautifulSoup(context.response.content, "html.parser").find("article")
    context.test.assertIsNotNone(article.find(string="edited"))


@given("other users reviewed a game")
def other_reviews(context):
    game_in_my_library(context)
    for username, rating, review in [("reader_a", 3, "Good game."), ("reader_b", 5, "Loved it.")]:
        user = get_user_model().objects.create_user(username=username, email=f"{username}@example.com")
        Catalog.objects.create(user=user, games=context.entry.games, rating=rating, review=review)


@then("I see all their ratings and reviews")
def see_all_reviews(context):
    articles = BeautifulSoup(context.response.content, "html.parser").find_all("article")
    context.test.assertEqual(len(articles), 2)
    for article, username, rating, review in zip(articles, ["reader_a", "reader_b"], [3, 5], ["Good game.", "Loved it."]):
        context.test.assertEqual(article.h3.get_text(strip=True), username)
        context.test.assertIn(f"Rating: {rating}/5", article.get_text())
        context.test.assertIn(review, article.get_text())
