from django.urls import reverse
from behave import given, when
from django.contrib.auth import get_user_model

User = get_user_model()
PASSWORD = "Pass291209120-9!9032"

@given('I am logged in as "{username}"')
def logged_in(context, username):
    User.objects.create_user(username=username, email=f"{username}@testing.com", password=PASSWORD)
    context.test.client.login(username=username, password=PASSWORD)

@when('I change my username to "{new_username}"')
def change_username(context, new_username):
    context.response = context.test.client.post(reverse("profiles:change_username"), {"username": new_username}, follow=True)

