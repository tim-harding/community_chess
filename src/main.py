import os
import praw


def main():
    reddit = praw.Reddit("bot1", config_interpolation="basic")
    subreddit = reddit.subreddit("CommunityChess")
    #subreddit.submit("Test", selftext="Self text")
    print(reddit.user.me())


if __name__ == "__main__":
    main()
