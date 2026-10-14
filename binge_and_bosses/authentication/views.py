from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import SignupForm

# Create your views here.
def signup(request):
    # Source: https://www.pythontutorial.net/django-tutorial/django-registration/
    if request.method == 'GET':
        form = SignupForm()
    else:
        form = SignupForm(request.POST)
        """
        If the form is valid, save the user in database + hash user password
        """
        if form.is_valid():
            user = form.save()

            # Login as user (preventing annoying retyping)
            login(request, user)
            return redirect("/")
    return render(request, "registration/signup.html", {"form": form})