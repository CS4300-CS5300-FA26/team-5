from django.contrib import admin
from .models import Game

# Register your models here.
#Adds Game to Django Admin interface
admin.site.register(Game)