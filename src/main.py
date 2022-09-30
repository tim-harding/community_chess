import os
import praw
import praw.models


def main():
    username = os.environ["COMMUNITY_CHESS_USERNAME"],
    # TODO(tim-harding): Use praw.ini instead of environment variables
    # https://praw.readthedocs.io/en/latest/getting_started/configuration/prawini.html
    reddit = praw.Reddit(
        client_id=os.environ["COMMUNITY_CHESS_ID"],
        client_secret=os.environ["COMMUNITY_CHESS_SECRET"],
        password=os.environ["COMMUNITY_CHESS_PASSWORD"],
        user_agent=f"Community Chess (by u/{username})",
        username=username,
    )
    subreddit = reddit.subreddit("CommunityChess")
    for comment in subreddit.stream.comments():
        print(comment.body)


if __name__ == "__main__":
    main()
