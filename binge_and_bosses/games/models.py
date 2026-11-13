from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.

#Game Model
class Game(models.Model):
    # Store the rawg_id for a game 
    rawg_id = models.IntegerField(unique=True, null=True, blank=True)
    # Store all other attributes we get from it
    game_title = models.CharField(max_length=200)
    game_description = models.TextField()
    game_rating = models.FloatField()
    game_release = models.DateField(null=True, blank=True)
    game_image = models.URLField(blank=True)
    game_genre = models.TextField(blank=True)
    game_platforms = models.TextField(blank=True)

class Catalog(models.Model):

    class Status(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "games"], name="unique_catalog_user_game"),
            models.CheckConstraint(
                condition=models.Q(rating__isnull=True) | models.Q(rating__gte=1, rating__lte=5),
                name="catalog_rating_1_to_5",
            ),
        ]

    games = models.ForeignKey(Game,on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    review = models.TextField(max_length=1000, blank=True)
    review_edited = models.BooleanField(default=False)


