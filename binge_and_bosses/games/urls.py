from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("search/", views.game_search, name="game_search"),
    path("<int:game_id>/", views.game_details, name="game_details"),
    path("library/", views.library, name="library"),
    path("<int:game_id>/add/", views.add_to_library, name="add_to_library"),
    path("<int:game_id>/remove/", views.remove_from_library, name="remove_from_library"),
    path("<int:game_id>/review/", views.save_review, name="save_review"),
]
