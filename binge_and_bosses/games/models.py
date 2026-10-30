from django.db import models
from django.conf import settings

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

class Catalog(models.Model):

    games = models.ForeignKey(Game,on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)


