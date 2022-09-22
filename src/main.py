import os
import praw

username = os.environ["COMMUNITY_CHESS_USERNAME"],
reddit = praw.Reddit(
    client_id=os.environ["COMMUNITY_CHESS_ID"],
    client_secret=os.environ["COMMUNITY_CHESS_SECRET"],
    password=os.environ["COMMUNITY_CHESS_PASSWORD"],
    user_agent=f"Community Chess (by u/{username})",
    username=username,
)
