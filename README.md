# Community Chess Bot

A moderator bot for [Community Chess](https://www.reddit.com/r/CommunityChess/), a collaborative chess game on Reddit.

## Contributing

### Setup

Use [pyenv](https://github.com/pyenv/pyenv) to manage your Python installation. Create a virtual environment and install the package.

```sh
python -m venv .venv
source .venv/bin/activate # Run each time you open the project
pip install --editable .[dev]
```

### Authentication 

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

3. Use `get_refresh_token` to generate a refresh token. 

4. Add this line to your `praw.ini`:

```ini
refresh_token=MY_REFRESH_TOKEN
```

### Testing

#### Type checking

```sh
mypy
```

#### Unit tests

```sh
python -m unittest
```

#### Running

If you wish to test the bot in a live environment, please do so over at [/r/testingground4bots](https://www.reddit.com/r/testingground4bots/) or somewhere else off the main sub. 

```sh
# Show command documentation
chessbot --help

# Enable verbose logging and 
# check for moves on the current post every five seconds
chessbot --log INFO --timeout 5
```

### Deployment

The bot is deployed with [Fly.io](https://fly.io/). 

#### Secrets

Set [secrets](https://fly.io/docs/reference/secrets/) for the `CLIENT_ID`, `CLIENT_SECRET`, and `REFRESH_TOKEN` variables from `praw.ini`.

```sh
fly secrets set MY_VAR=xxxxxxxx --stage
```

#### Volume

Create the [volume](https://fly.io/docs/apps/volume-storage/) `community_chess_db`. 

```sh
fly volumes create community_chess_db -r sea -n 1 -s 1
```

#### Publish

```sh
# High availability creates unnecessary extra machines
fly deploy --ha=false
```
