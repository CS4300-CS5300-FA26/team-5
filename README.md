# Binge & Bosses (Team 5)
CS 4300/5300 Fall 2026 — Team 5 group project

## Team Members:
- Ethan Capehart
- Michael Gonzalez
- Carlos Lucero Ortega
- Ryan Rupakheti
- Laura Baird

## What is Binge & Bosses
Binge & Bosses is a backlog management and social interaction platform geared for gamers who want to do the following:
- Track their backlog of games
- Review games they have played
- See the activity of their friends
- Get game recommendations
- Track the time spent in-game

## How to run Binge & Bosses
### Step 1. Install the requirements
Run: 
```bash
pip3 install -r requirements.txt
```

### Step 2. Create .env file
within `binge_and_bosses/` create a file called `.env` in the same directory as `manage.py`

### Step 3. Add secret key
Next, generate a secret key and place it within the `.env` file with the format like:
```.env
SECRET_KEY=<SECRET_KEY_HERE>
``` 
You can generate a secret key by running
```
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 4. Run the server
```bash
binge_and_bosses/manage.py runserver
```

## Sprint Plan

## AI Usage Log
