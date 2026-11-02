from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import Game
from .rawg_client import search_game, get_game_details 
# Create your views here.


def index(request):
    games = Game.objects.all()
    return render(request,'games/index.html',{'games':games})

@login_required
def library(request):
    return render(request,'games/library.html')

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

    if game is None and "q" in request.GET:
        messages.error(request, "Could not load game details. Try again.")
        return redirect(reverse("game_search", query={"q": request.GET["q"]}))

    return render(request, "games/details.html", {
        "game": game,
        "error": game is None,
    })
    return render(request,'games/index.html',{'games':games, 'user': request.user})

