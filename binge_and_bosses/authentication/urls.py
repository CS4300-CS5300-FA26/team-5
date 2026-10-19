from django.urls import path, include
from django.contrib.auth import views as auth_view 
from . import views
from .forms import LoginForm

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", auth_view.LoginView.as_view(authentication_form=LoginForm), name="login"),
    path("", include("django.contrib.auth.urls")),
]