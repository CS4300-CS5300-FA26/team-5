from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Game
# Create your views here.

def index(request):
    games = Game.objects.all()
    return render(request,'games/index.html',{'games':games, 'user': request.user})

@login_required
def library(request):
    return render(request,'games/library.html')