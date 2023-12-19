import praw
import praw.models


def main():
    reddit = praw.Reddit()
    sub = reddit.subreddit("communitychess")


if __name__ == "__main__":
    main()
