from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from .models import Profile

User = get_user_model()
MAX_AVATAR_MB = 2

class UsernameChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username"]

    def clean_username(self):
        username = self.cleaned_data["username"]

        # ensure that username is unique
        taken = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)

        if taken.exists():
            raise forms.ValidationError("That username is taken.")

        return username

class StyledPasswordChangeForm(PasswordChangeForm):
    """
        Password change form but modified to work with bootstrap
    """
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

class AvatarForm(forms.ModelForm):
    """
        Form for uploading an avatar + cleaning
    """
    class Meta:
        model = Profile
        fields = ["avatar"]
        widgets = {
            "avatar": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"})
        }

    def clean_avatar(self):
        """
            Reject any files larger than the variable MAX_AVATAR_MB
        """
        avatar = self.cleaned_data.get("avatar")

        # hasattr: an unchanged existing avatar has no.size on the upload object
        if avatar and hasattr(avatar, "size") and avatar.size > MAX_AVATAR_MB * 1024 * 1024:
            raise forms.ValidationError(f"Image must be smaller than {MAX_AVATAR_MB} MB.")

        return avatar
