from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import FriendRequestForm
from .models import Friendship


def friends_page(request, form=None):
    relationships = Friendship.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).select_related("sender__profile", "recipient__profile").order_by("pk")
    accepted, incoming, outgoing = [], [], []
    for relationship in relationships:
        relationship.other = relationship.recipient if relationship.sender_id == request.user.pk else relationship.sender
        if relationship.accepted:
            accepted.append(relationship)
        elif relationship.recipient_id == request.user.pk:
            incoming.append(relationship)
        else:
            outgoing.append(relationship)
    return render(request, "friends/index.html", {
        "form": form if form is not None else FriendRequestForm(),
        "relationships": accepted, "friends": [row.other for row in accepted],
        "incoming": incoming, "outgoing": outgoing,
    })


@login_required
def index(request):
    return friends_page(request)


@login_required
@require_POST
def send(request):
    form = FriendRequestForm(request.POST)
    if not form.is_valid():
        return friends_page(request, form)
    recipient = get_user_model().objects.filter(username=form.cleaned_data["username"]).first()
    if recipient is None:
        form.add_error("username", "No player with that username")
    elif recipient == request.user:
        form.add_error("username", "You cannot add yourself.")
    else:
        pair = Q(sender=request.user, recipient=recipient) | Q(sender=recipient, recipient=request.user)
        relationship = Friendship.objects.filter(pair).first()
        if relationship is None:
            try:
                with transaction.atomic():
                    Friendship.objects.create(sender=request.user, recipient=recipient)
            except IntegrityError:
                # Another request for this pair may have won the race.
                relationship = Friendship.objects.filter(pair).first()
                if relationship is None:
                    raise
            else:
                messages.success(request, "Friend request sent.")
                return redirect("friends:index")
        messages.info(request, "You are already friends." if relationship.accepted else "A request is already pending.")
        return redirect("friends:index")
    return friends_page(request, form)


@login_required
@require_POST
def accept(request, pk):
    with transaction.atomic():
        relationship = get_object_or_404(
            Friendship.objects.select_for_update(), pk=pk, recipient=request.user, accepted=False
        )
        relationship.accepted = True
        relationship.save(update_fields=["accepted"])
    messages.success(request, "Friend request accepted.")
    return redirect("friends:index")


@login_required
@require_POST
def decline(request, pk):
    with transaction.atomic():
        relationship = get_object_or_404(
            Friendship.objects.select_for_update(), pk=pk, recipient=request.user, accepted=False
        )
        relationship.delete()
    messages.success(request, "Friend request declined.")
    return redirect("friends:index")


@login_required
@require_POST
def remove(request, pk):
    with transaction.atomic():
        relationship = get_object_or_404(
            Friendship.objects.select_for_update().filter(Q(sender=request.user) | Q(recipient=request.user)),
            pk=pk, accepted=True,
        )
        relationship.delete()
    messages.success(request, "Friend removed.")
    return redirect("friends:index")
