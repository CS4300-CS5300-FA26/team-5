from django.contrib.auth.forms import UserCreationForm
from .models import User

class SignupForm(UserCreationForm):
    """
        Registration Form for users. By default, the UserCreationForm handles important
        security stuff such as password checking and running Django's validators 
    """
    class Meta(UserCreationForm.Meta):
        model = User

        # NOTE: the password fields are handled automatically by UserCreationForm so dont worry
        fields = ("username", "email")