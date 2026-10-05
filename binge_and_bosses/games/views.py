from django.shortcuts import render
from .models import Game
# Create your views here.

def index(request):
    games = Game.objects.all()
    return render(request,'games/index.html',{'games':games})