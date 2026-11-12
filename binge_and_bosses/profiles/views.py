from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UsernameChangeForm

# Create your views here.
@login_required
def change_username(request):
    if request.method == "POST":
        # NOTE: instance=request.user ensures that only the user can edit themself and no one else. 
        form = UsernameChangeForm(request.POST, instance=request.user)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Your username has been updated!")
            return redirect("profiles:change_username")
    else:
        form = UsernameChangeForm(instance = request.user)

    return render(request, "profiles/change_username.html", {"form":form})

        