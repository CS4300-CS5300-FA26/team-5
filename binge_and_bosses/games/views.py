from django.shortcuts import render
from .models import Game
from .services import Game_Search
# Create your views here.

def index(request):
    games = Game.objects.all()
    return render(request,'games/index.html',{'games':games})