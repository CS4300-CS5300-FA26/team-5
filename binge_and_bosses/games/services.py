import requests
from django.conf import settings


HEADERS = {}


#Game_Search to get API request
def Game_Search(name):

    #Call the API response 
    response = requests.get(
            f"{settings.RAWG_BASE_URL}/games",
            params = {"key":settings.RAWG_API_KEY,'search':name,'page_size':1},
            timeout=10
            )

    results = response.json().get('results',[])
    return results
