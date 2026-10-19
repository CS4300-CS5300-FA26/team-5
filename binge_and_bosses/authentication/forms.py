from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

class StyledForm:
    """
        Adds bootstrap's form-control to each field for <input> styles
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add bootstrap class to each widget
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        
class SignupForm(StyledForm, UserCreationForm):
    """
        Registration Form for users. By default, the UserCreationForm handles important
        security stuff such as password checking and running Django's validators 
    """
    class Meta(UserCreationForm.Meta):
        model = User

        # NOTE: the password fields are handled automatically by UserCreationForm so dont worry
        fields = ("username", "email")

class LoginForm(StyledForm, AuthenticationForm):
    pass