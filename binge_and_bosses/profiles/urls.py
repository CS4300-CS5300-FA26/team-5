from django.urls import path
from . import views

app_name = "profiles"

urlpatterns = [
    path("settings/username/", views.change_username, name="change_username"),
    path("settings/password/", views.ChangePasswordView.as_view(), name="change_password"),
    path("settings/change_avatar/", views.change_avatar, name="change_avatar"),
]
