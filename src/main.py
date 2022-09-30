import praw
import praw.models


def main():
    reddit = praw.Reddit("bot1", config_interpolation="basic")
    subreddit = reddit.subreddit("CommunityChess")
    for comment in subreddit.stream.comments():
        print(comment.body)
    print(reddit.user.me())


if __name__ == "__main__":
    main()
