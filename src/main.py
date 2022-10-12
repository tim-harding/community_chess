import praw
import praw.models


def main():
    reddit = praw.Reddit("bot1", config_interpolation="basic")
    submission = reddit.submission("xlm3zg")
    submission.comments.replace_more(limit=0) #prevents needing to load more comments
    for top_level_comment in submission.comments:
        print(top_level_comment.body)
        print(top_level_comment.author)
    print(reddit.user.me())


if __name__ == "__main__":
    main()
