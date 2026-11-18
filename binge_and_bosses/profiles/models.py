from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


# Create your models here.
def avatar_upload_path(instance, filename):
    """
    Store each avatar as avatars/user_<ID>.<file_extention> so filenames are predictable
    """
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"avatars/user_{instance.user_id}.{ext}"


class Profile(models.Model):
    # One profile per user
    # Deleting the user deletes the profile as well
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")

    # Make the image field blank and null to ensure users arent required to have an avatar
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True)

    def __str__(self):
        return f"Profile for {self.user}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    """
    Automatically create a profile whenever a new user signs up
    """
    if created:
        Profile.objects.create(user=instance)
