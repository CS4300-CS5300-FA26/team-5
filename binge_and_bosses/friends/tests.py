from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from .models import Friendship


class FriendRequestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.alice, cls.bob, cls.eve = [
            User.objects.create_user(username=name, email=f"{name}@example.com") for name in ("alice", "bob", "eve")
        ]

    def setUp(self):
        self.client.force_login(self.alice)

    def send(self, username="bob", client=None):
        return (client or self.client).post(reverse("friends:send"), {"username": username}, follow=True)

    def action(self, action, relationship, client=None):
        return (client or self.client).post(reverse(f"friends:{action}", args=[relationship.pk]), follow=True)

    def test_send_and_recipient_sees_pending(self):
        self.assertContains(self.send(), "Friend request sent.")
        relationship = Friendship.objects.get()
        self.assertFalse(relationship.accepted)
        self.client.force_login(self.bob)
        response = self.client.get(reverse("friends:index"))
        self.assertContains(response, "alice")
        self.assertContains(response, reverse("friends:accept", args=[relationship.pk]))

    def test_unknown_self_and_blank_requests_create_nothing(self):
        for username, message in [
            ("missing", "No player with that username"),
            ("alice", "You cannot add yourself."),
            ("", "This field is required."),
        ]:
            with self.subTest(username=username):
                self.assertContains(self.send(username), message)
                self.assertFalse(Friendship.objects.exists())

    def test_duplicate_and_reverse_request_stay_pending(self):
        self.send()
        self.assertContains(self.send(), "A request is already pending.")
        self.client.force_login(self.bob)
        self.assertContains(self.send("alice"), "A request is already pending.")
        self.assertEqual(Friendship.objects.count(), 1)
        self.assertFalse(Friendship.objects.get().accepted)

    def test_accept_lists_both_users_and_prevents_new_request(self):
        self.send()
        relationship = Friendship.objects.get()
        self.client.force_login(self.bob)
        self.assertContains(self.action("accept", relationship), "alice")
        relationship.refresh_from_db()
        self.assertTrue(relationship.accepted)
        for user, other in [(self.alice, self.bob), (self.bob, self.alice)]:
            self.client.force_login(user)
            response = self.client.get(reverse("friends:index"))
            self.assertIn(other, response.context["friends"])
            self.assertContains(self.send(other.username), "You are already friends.")
        self.assertEqual(Friendship.objects.count(), 1)

    def test_decline_allows_a_later_request(self):
        self.send()
        relationship = Friendship.objects.get()
        self.client.force_login(self.bob)
        self.action("decline", relationship)
        self.assertFalse(Friendship.objects.exists())
        self.client.force_login(self.alice)
        self.assertContains(self.send(), "Friend request sent.")

    def test_either_friend_can_remove_and_both_lists_update(self):
        for remover in (self.alice, self.bob):
            with self.subTest(remover=remover.username):
                self.client.force_login(self.alice)
                self.send()
                relationship = Friendship.objects.get()
                self.client.force_login(self.bob)
                self.action("accept", relationship)
                self.client.force_login(remover)
                self.action("remove", relationship)
                self.assertFalse(Friendship.objects.exists())
                for user in (self.alice, self.bob):
                    self.client.force_login(user)
                    response = self.client.get(reverse("friends:index"))
                    self.assertEqual(list(response.context["friends"]), [])

    def test_only_recipient_can_respond_and_only_friends_can_remove(self):
        self.send()
        relationship = Friendship.objects.get()
        for user in (self.alice, self.eve):
            self.client.force_login(user)
            for action in ("accept", "decline", "remove"):
                self.assertEqual(self.action(action, relationship).status_code, 404)
        self.client.force_login(self.bob)
        self.assertEqual(self.action("remove", relationship).status_code, 404)
        self.action("accept", relationship)
        for action in ("accept", "decline"):
            self.assertEqual(self.action(action, relationship).status_code, 404)
        self.client.force_login(self.eve)
        self.assertEqual(self.action("remove", relationship).status_code, 404)
        self.assertTrue(Friendship.objects.get().accepted)

    def test_login_post_and_csrf_are_required(self):
        self.send()
        relationship = Friendship.objects.get()
        urls = [reverse("friends:send")] + [
            reverse(f"friends:{action}", args=[relationship.pk]) for action in ("accept", "decline", "remove")
        ]
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.bob)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 405)
            self.assertEqual(csrf_client.post(url).status_code, 403)
        self.client.logout()
        for url in urls + [reverse("friends:index")]:
            self.assertEqual(self.client.get(url).status_code, 302)
        for url in urls:
            self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(Friendship.objects.get().accepted)

    def test_missing_request_and_private_inbox(self):
        self.send()
        self.client.force_login(self.eve)
        response = self.client.get(reverse("friends:index"))
        self.assertEqual(list(response.context["incoming"]), [])
        self.assertEqual(list(response.context["outgoing"]), [])
        self.assertContains(response, "No friends yet")
        for action in ("accept", "decline", "remove"):
            self.assertEqual(self.client.post(reverse(f"friends:{action}", args=[999])).status_code, 404)

    def test_database_rejects_duplicate_reverse_and_self_relationships(self):
        self.send()
        for sender, recipient in [(self.alice, self.bob), (self.bob, self.alice), (self.alice, self.alice)]:
            with self.subTest(sender=sender.username, recipient=recipient.username):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Friendship.objects.create(sender=sender, recipient=recipient)
