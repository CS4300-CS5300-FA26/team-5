from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class UsernameChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username"]

    def sanitize_username(self):
        username = self.cleaned_data["username"]

        # ensure that username is unique
        taken = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        
        if taken.exists():
            raise forms.ValidationError("That username is taken.")
        
        return username 