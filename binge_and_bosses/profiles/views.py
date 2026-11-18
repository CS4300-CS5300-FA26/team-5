from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UsernameChangeForm, StyledPasswordChangeForm
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from .forms import AvatarForm
from .models import Profile

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

class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    form_class = StyledPasswordChangeForm
    template_name = "profiles/change_password.html"
    success_url = reverse_lazy("profiles:change_password")
    success_message = "Your password has been updated!"

@login_required
def change_avatar(request):
    # using get_or_create protects against users who have no profile yet (if that happens)
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Remove avatar button submits a field name "remove"
        if "remove" in request.POST:
            if profile.avatar:
                # Remove the file from disk and clears the DB field
                profile.avatar.delete(save=True)

            messages.success(request, "Avatar removed.")
            return redirect("profiles:change_avatar")

        # Remember the old file so we can clean it up
        if profile.avatar:
            old_name = profile.avatar.name
        else:
            old_name = None

        form = AvatarForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Delete the old file first
            if old_name and "avatar" in request.FILES:
                profile.avatar.storage.delete(old_name)
            
            form.save()
            
            messages.success(request, "Avatar updated.")

            # Redirect to avoid duplicate submissions
            return redirect("profiles:change_avatar")
    else:
        form = AvatarForm(instance=profile)

    return render(request, "profiles/change_avatar.html", {"form": form, "profile": profile})
    