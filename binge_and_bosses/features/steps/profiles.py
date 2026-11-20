from django.urls import reverse
from behave import given, when, then
from django.contrib.auth import get_user_model

import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from profiles.models import Profile

User = get_user_model()
PASSWORD = "Pass291209120-9!9032"


def make_image(filename):
    """
    Create an image file in memory
    """
    buffer = BytesIO()
    Image.new("RGB", (10, 10), "blue").save(buffer, "PNG")
    return SimpleUploadedFile(filename, buffer.getvalue())


def page_html(context):
    """
    Get the last response's HTML, decoded for simple text checks
    """
    return context.response.content.decode()


@given('I am logged in as "{username}"')
def logged_in(context, username):
    context.user = User.objects.create_user(username=username, email=f"{username}@testing.com", password=PASSWORD)
    context.test.client.login(username=username, password=PASSWORD)


@when('I change my username to "{new_username}"')
def change_username(context, new_username):
    context.response = context.test.client.post(
        reverse("profiles:change_username"), {"username": new_username}, follow=True
    )


@given("uploads are stored in a temporary media folder")
def step_temp_media(context):
    """
    Function to specify location of media root and storage so that the scenarios
    do not write into a real media folder
    """
    media_root = tempfile.mkdtemp()
    override = override_settings(
        MEDIA_ROOT=media_root,
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        },
    )
    override.enable()
    context.add_cleanup(override.disable)
    context.add_cleanup(shutil.rmtree, media_root, True)


@given("I am logged out")
def step_logout(context):
    context.test.client.logout()
    assert "_auth_user_id" not in context.test.client.session, "Client is still logged in"


@given("I have uploaded an avatar")
def step_have_avatar(context):
    url = reverse("profiles:change_avatar")
    context.test.client.post(url, {"avatar": make_image("existing.png")})
    assert Profile.objects.get(user=context.user).avatar


@when("I open the change avatar page")
def step_open_page(context):
    context.response = context.test.client.get(reverse("profiles:change_avatar"))


@when('I upload a valid image named "{filename}"')
def step_upload_valid(context, filename):
    context.response = context.test.client.post(
        reverse("profiles:change_avatar"), {"avatar": make_image(filename)}, follow=True
    )


@when('I upload a fake image named "{filename}"')
def step_upload_fake(context, filename):
    fake = SimpleUploadedFile(filename, b"this is not an image")
    context.response = context.test.client.post(reverse("profiles:change_avatar"), {"avatar": fake}, follow=True)


@when("I remove my avatar")
def step_remove(context):
    context.response = context.test.client.post(reverse("profiles:change_avatar"), {"remove": "1"}, follow=True)


@then('I should see the message "{text}"')
def step_see_message(context, text):
    assert text in page_html(context), f"'{text}' not found on the page"


@then("the navbar shows the initial placeholder")
def step_navbar_placeholder(context):
    response = context.test.client.get(reverse("profiles:change_avatar"))
    assert "avatar-sm avatar-placeholder" in response.content.decode()


@then('the settings dropdown has a "{label}" link')
def step_dropdown_link(context, label):
    assert label in page_html(context)


@then("my avatar file exists on disk")
def step_file_exists(context):
    profile = Profile.objects.get(user=context.user)
    assert Path(profile.avatar.path).exists()


@then("my avatar is not saved")
def step_not_saved(context):
    assert not Profile.objects.get(user=context.user).avatar
