from django.contrib import admin
from .models import Game,Catalog

# Register your models here.
#Adds Game to Django Admin interface
admin.site.register(Game)
admin.site.register(Catalog)