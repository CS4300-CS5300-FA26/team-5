from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.urls import reverse
from django.views.decorators.http import require_POST
from .models import Game, Catalog
from .rawg_client import search_game, get_game_details 
from .catalog import get_or_import
from .forms import ReviewForm
# Create your views here.


def index(request):
    games = Game.objects.all()
    return render(request,'games/index.html',{'games':games})

@login_required
def library(request):
    library_entries = Catalog.objects.filter(user=request.user).select_related('games')
    return render(request,'games/library.html', {'library_entries': library_entries})

#Get the game details from rawg and add it to the user's library if it doesn't exist already
@login_required
@require_POST
def add_to_library(request, game_id):
    game = get_or_import(game_id)
    if game is not None:
        Catalog.objects.get_or_create(user=request.user, games=game)
    return redirect("game_details", game_id=game_id)

#Get the existing catalog entry for the user and game and delete it, then redirect to the game details page
@login_required
@require_POST
def remove_from_library(request, game_id):
    game = get_object_or_404(Catalog, user=request.user, games__rawg_id=game_id)
    game.delete()
    return redirect("game_details", game_id=game_id)


@login_required
@require_POST
def save_review(request, game_id):
    entry = get_object_or_404(Catalog, user=request.user, games__rawg_id=game_id)
    old_review = entry.review
    form = ReviewForm(request.POST, instance=entry)
    if form.is_valid():
        entry = form.save(commit=False)
        if not entry.review:
            entry.review_edited = False
        elif old_review and entry.review != old_review:
            entry.review_edited = True
        entry.save()
    else:
        messages.error(request, "Pick a rating from 1 to 5.")
    return redirect("game_details", game_id=game_id)


#return search results from rawg based on user input, return error on empty 
def game_search(request):
    query = request.GET.get("q", "").strip()
    games = search_game(query) if query else []
    last_search = request.session.get("last_search", {})
    if games:
        # Keep what search.html shows, so the results survive a RAWG outage.
        request.session["last_search"] = {"q": query, "games": [
            {"id": g["id"], "name": g["name"], "background_image": g.get("background_image")}
            for g in games
        ]}
    elif games is None and last_search.get("q") == query:
        games = last_search["games"]

    return render(request, "games/search.html", {
        "games": games if games is not None else[], 
        "query": query,
        "error": games is None
        })

def game_details(request, game_id):
    game = get_game_details(game_id)
    entry = (
        Catalog.objects.filter(user=request.user, games__rawg_id=game_id).first()
        if request.user.is_authenticated else None
    )

    if game is None and "q" in request.GET:
        messages.error(request, "Could not load game details. Try again.")
        return redirect(reverse("game_search", query={"q": request.GET["q"]}))

    return render(request, "games/details.html", {
        "game": game,
        "error": game is None,
        "in_library": entry is not None,
        "review_form": ReviewForm(instance=entry) if entry else None,
        "reviews": Catalog.objects.filter(games__rawg_id=game_id).filter(
            Q(rating__isnull=False) | ~Q(review=""),
        ).select_related("user").order_by("user__username"),
    })

