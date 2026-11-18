from django.urls import path
from . import views

app_name = "friends"
urlpatterns = [
    path("", views.index, name="index"),
    path("send/", views.send, name="send"),
    path("<int:pk>/accept/", views.accept, name="accept"),
    path("<int:pk>/decline/", views.decline, name="decline"),
    path("<int:pk>/remove/", views.remove, name="remove"),
]
