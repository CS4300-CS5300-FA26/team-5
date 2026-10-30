from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Game, Catalog
from .rawg_client import search_game, get_game_details 
from .catalog import get_or_import
# Create your views here.


def index(request):
    games = Game.objects.all()
    return render(request,'games/index.html',{'games':games})

@login_required
def library(request):
    return render(request,'games/library.html')

#Get the game details from rawg and add it to the user's library if it doesn't exist already
@login_required
@require_POST
def add_to_library(request, game_id):
    game = get_or_import(game_id)
    if game is not None:
        Catalog.objects.get_or_create(user=request.user, games=game)
    return redirect("game_details", game_id=game_id)

#return search results from rawg based on user input, return error on empty 
def game_search(request):
    query = request.GET.get("q", "").strip()
    games = search_game(query) if query else []
    
    return render(request, "games/search.html", {
        "games": games if games is not None else[], 
        "query": query,
        "error": games is None
        })

def game_details(request, game_id):
    game = get_game_details(game_id)
    in_library = (
        request.user.is_authenticated
        and Catalog.objects.filter(user=request.user, games__rawg_id=game_id).exists()
    )

    return render(request, "games/details.html", {
        "game": game,
        "error": game is None,
        "in_library": in_library,
    })
    return render(request,'games/index.html',{'games':games, 'user': request.user})

