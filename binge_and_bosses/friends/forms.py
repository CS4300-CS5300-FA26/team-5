from django import forms
from django.contrib.auth import get_user_model


class FriendRequestForm(forms.Form):
    username = forms.CharField(
        max_length=get_user_model()._meta.get_field("username").max_length,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Player username", "autocomplete": "off"}),
    )
