from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("search/", views.game_search, name="game_search"),
    path("<int:game_id>/", views.game_details, name="game_details"),
    path("library/", views.library, name="library"),
]