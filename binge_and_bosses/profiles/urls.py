from django.urls import path
from . import views

app_name = "profiles"

urlpatterns = [
    path("settings/username/", views.change_username, name="change_username")
]

