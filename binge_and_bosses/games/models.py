from django.db import models

# Create your models here.

#Game Model and Attributes We Need
class Game(models.Model):
    game_title = models.CharField(max_length=100)
    game_description = models.TextField()
    game_rating = models.FloatField()
    game_release = models.DateField()