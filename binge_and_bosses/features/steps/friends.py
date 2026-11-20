from behave import given, when, then
from django.contrib.auth import get_user_model
from django.urls import reverse

from friends.models import Friendship


def other_player(context):
    context.other = get_user_model().objects.create_user(username="friend_player", email="friend@example.com")
    context.friend_username = context.other.username


@given("a valid username")
def valid_username(context):
    other_player(context)


@given("a username that does not exist")
def unknown_username(context):
    context.friend_username = "nonexistent_player"


@when("I send a friend request")
def send_request(context):
    context.response = context.test.client.post(
        reverse("friends:send"), {"username": context.friend_username}, follow=True
    )


@then("the other player sees it as pending")
def pending_for_recipient(context):
    context.test.client.force_login(context.other)
    response = context.test.client.get(reverse("friends:index"))
    context.test.assertContains(response, context.user.username)
    incoming = response.context["incoming"]
    context.test.assertEqual(len(incoming), 1)
    context.test.assertFalse(incoming[0].accepted)
    context.test.assertContains(response, reverse("friends:accept", args=[incoming[0].pk]))


@then("no friend request is sent")
def no_request(context):
    context.test.assertFalse(Friendship.objects.exists())


@given("a pending request")
def pending_request(context):
    other_player(context)
    context.test.client.force_login(context.other)
    context.test.client.post(reverse("friends:send"), {"username": context.user.username})
    context.relationship = Friendship.objects.get()
    context.test.client.force_login(context.user)


@when("I accept it")
def accept_request(context):
    context.response = context.test.client.post(reverse("friends:accept", args=[context.relationship.pk]), follow=True)


@when("I decline it")
def decline_request(context):
    context.response = context.test.client.post(
        reverse("friends:decline", args=[context.relationship.pk]), follow=True
    )


@then("we both appear in each other's friends list")
def both_friends(context):
    for user, friend in [(context.user, context.other), (context.other, context.user)]:
        context.test.client.force_login(user)
        response = context.test.client.get(reverse("friends:index"))
        context.test.assertIn(friend, response.context["friends"])
        context.test.assertContains(response, friend.username)


@then("that player does not appear in my friends list")
@then("we disappear from each other's friends list")
def not_friends(context):
    for user in (context.user, context.other):
        context.test.client.force_login(user)
        response = context.test.client.get(reverse("friends:index"))
        context.test.assertEqual(response.context["friends"], [])
    context.test.assertFalse(Friendship.objects.exists())


@given("a friend")
def accepted_friend(context):
    pending_request(context)
    accept_request(context)


@when("I remove them")
def remove_friend(context):
    context.response = context.test.client.post(reverse("friends:remove", args=[context.relationship.pk]), follow=True)
