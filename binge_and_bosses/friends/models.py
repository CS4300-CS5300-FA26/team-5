from django.conf import settings
from django.db import models
from django.db.models.functions import Greatest, Least


class Friendship(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friendships_sent")
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friendships_received"
    )
    accepted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~models.Q(sender=models.F("recipient")), name="friendship_not_self"),
            # The same pair is unique regardless of who sent the request first.
            models.UniqueConstraint(
                Least("sender", "recipient"), Greatest("sender", "recipient"), name="friendship_unique_pair"
            ),
        ]
