from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm

User = get_user_model()

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

