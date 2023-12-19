import praw
import praw.models
import database


def main():
    database.prepare()
    database.insert_game()
    print(database.current_game())
    database.insert_move("e4")
    database.insert_move("e5")


def print_latest_post():
    reddit = praw.Reddit()
    sub = reddit.subreddit("communitychess")
    for post in sub.new(limit=1):
        print(post.title)


if __name__ == "__main__":
    main()
