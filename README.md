# Community Chess Bot

A moderator bot for [Community Chess](https://www.reddit.com/r/CommunityChess/), a collaborative chess game on Reddit.

## Contributing

1. Create a virtual environment to work in
```sh
python -m venv .venv
```

2. Activate the virtual environment each time you open the project
```sh
source .venv/bin/activate
```

3. Install dependencies
```sh 
pip install -r requirements.txt`
```

4. [Set up](#authentication) Reddit API authentication

4. Run the bot

- `--help` shows options
- `--timeout` sets how frequently the bot should look for moves to play
- `--log` sets the log level

```sh
# Enable verbose logging and 
# check for moves on the current post every five seconds
python src/main.py --log INFO --timeout 5
```

## Authentication 

This bot uses Praw's [Code Flow](https://praw.readthedocs.io/en/stable/getting_started/authentication.html#code-flow) for authentication. 

1. Create an application in your Reddit [application preferences](https://www.reddit.com/prefs/apps/). Note your `client_secret`, shown when your press *edit*, and your `client_id`, listed below *personal use script*.

2. Set up your `praw.ini` in the project root as follows:
```ini
[DEFAULT]
redirect_uri=http://localhost:8080
client_id=MY_CLIENT_ID
client_secret=MY_CLIENT_SECRET
user_agent=script:com.MY_NAME.communitychess:v0.1.0 (by /u/MY_USERNAME)
```

3. Use `python src/get_refresh_token.py` to generate a refresh token. 

4. Add this line to your `praw.ini`:

```ini
refresh_token=MY_REFRESH_TOKEN
```
