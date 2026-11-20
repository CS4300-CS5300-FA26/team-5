from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F, Max, Q
from django.db.models.functions import Lower
from django.urls import reverse
from django.views.decorators.http import require_POST
from .models import Catalog, Game
from .igdb_client import search_game
from .catalog import get_or_import
from .forms import ReviewForm
# Create your views here.


def index(request):
    if not request.user.is_authenticated:
        return render(request, "games/index.html")

    # Logged-in players get a working home page built from their own library
    entries = Catalog.objects.filter(user=request.user).select_related("games").order_by("-id")
    counts = dict(entries.values_list("status").annotate(Count("id")).order_by())
    statuses = [
        {"value": value, "label": label, "count": counts.get(value, 0)} for value, label in Catalog.Status.choices
    ]
    # Games in other players' libraries that this player doesn't have yet. Most players first;
    # a tie goes to the game someone added most recently. A game needs an id to link to.
    popular = (
        Game.objects.exclude(catalog__user=request.user)
        .exclude(igdb_id=None)
        .annotate(players=Count("catalog"), last_added=Max("catalog__id"))
        .filter(players__gt=0)
        .order_by("-players", "-last_added")[:3]
    )
    return render(
        request,
        "games/home.html",
        {
            "statuses": statuses,
            "total": sum(counts.values()),
            **entries.aggregate(
                rated=Count("id", filter=Q(rating__isnull=False)),
                reviewed=Count("id", filter=~Q(review="")),
            ),
            "popular": popular,
            "recent": entries[:6],
        },
    )


# Library sort options: URL value -> (link label, ordering). The first one is the default.
LIBRARY_SORTS = {
    "recent": ("Recent", ["-id"]),
    "title": ("Title", [Lower("games__game_title")]),
    "rating": ("Rating", [F("rating").desc(nulls_last=True), Lower("games__game_title")]),
}


@login_required
def library(request):
    sort = request.GET.get("sort")
    if sort not in LIBRARY_SORTS:
        sort = next(iter(LIBRARY_SORTS))
    library_entries = (
        Catalog.objects.filter(user=request.user).select_related("games").order_by(*LIBRARY_SORTS[sort][1])
    )
    return render(
        request,
        "games/library.html",
        {
            "library_entries": library_entries,
            "sort": sort,
            "sorts": {value: label for value, (label, _) in LIBRARY_SORTS.items()},
        },
    )


# Get the game details from IGDB and add it to the user's library if it doesn't exist already
@login_required
@require_POST
def add_to_library(request, game_id):
    game = get_or_import(game_id)
    if game is not None:
        Catalog.objects.get_or_create(user=request.user, games=game)
    return redirect("game_details", game_id=game_id)


# Get the existing catalog entry for the user and game and delete it, then redirect to the game details page
@login_required
@require_POST
def remove_from_library(request, game_id):
    game = get_object_or_404(Catalog, user=request.user, games__igdb_id=game_id)
    game.delete()
    return redirect("game_details", game_id=game_id)


@login_required
@require_POST
def save_review(request, game_id):
    entry = get_object_or_404(Catalog, user=request.user, games__igdb_id=game_id)
    old_review = entry.review
    form = ReviewForm(request.POST, instance=entry)
    if form.is_valid():
        entry = form.save(commit=False)
        if not entry.review:
            entry.review_edited = False
        elif old_review and entry.review != old_review:
            entry.review_edited = True
        entry.save()
    if "rating" in form.errors:
        messages.error(request, "Pick a rating from 1 to 5.")
    if "review" in form.errors:
        messages.error(request, "Keep your review to 1,000 characters or fewer.")
    if "status" in form.errors:
        messages.error(request, "Pick a valid play status.")
    return redirect("game_details", game_id=game_id)


# return search results from IGDB based on user input, return error on empty
def game_search(request):
    query = request.GET.get("q", "").strip()
    games = search_game(query) if query else []
    last_search = request.session.get("last_search", {})
    if games:
        # Keep what search.html shows, so the results survive an IGDB outage.
        request.session["last_search"] = {
            "q": query,
            "games": [
                {"id": g["id"], "name": g["name"], "cover": g["cover"], "released": g["released"]} for g in games
            ],
        }
    elif games is None and last_search.get("q") == query:
        games = last_search["games"]
    error = games is None
    games = games or []

    # Mark the results this player already owns
    owned = set()
    if games and request.user.is_authenticated:
        owned = set(
            Catalog.objects.filter(
                user=request.user,
                games__igdb_id__in=[g["id"] for g in games],
            ).values_list("games__igdb_id", flat=True)
        )

    return render(
        request,
        "games/search.html",
        {
            "games": games,
            "query": query,
            "error": error,
            "owned": owned,
        },
    )


def game_details(request, game_id):
    game = get_or_import(game_id)
    entry = (
        Catalog.objects.filter(user=request.user, games__igdb_id=game_id).first()
        if request.user.is_authenticated
        else None
    )

    if game is None and "q" in request.GET:
        messages.error(request, "Could not load game details. Try again.")
        return redirect(reverse("game_search", query={"q": request.GET["q"]}))

    players = Catalog.objects.filter(games__igdb_id=game_id)
    return render(
        request,
        "games/details.html",
        {
            "game": game,
            "error": game is None,
            "query": request.GET.get("q", ""),
            "entry": entry,
            "in_library": entry is not None,
            "statuses": Catalog.Status.choices,
            "review_form": ReviewForm(instance=entry) if entry else None,
            "players": players.aggregate(average=Avg("rating"), ratings=Count("rating")),
            "reviews": players.filter(
                Q(rating__isnull=False) | ~Q(review=""),
            )
            .select_related("user")
            .order_by("user__username"),
        },
    )
