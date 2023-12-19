import praw
import praw.models
import sqlite3


def main():
    prepare_database()
    reddit = praw.Reddit()
    sub = reddit.subreddit("communitychess")


def db_cursor():
    con = sqlite3.connect("communitychess.db")
    return con.cursor()


def prepare_database():
    cur = db_cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS move(
            number INTEGER,
            san TEXT,
            submission_url TEXT,
            game INTEGER,
            FOREIGN KEY(game) REFERENCES game(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS game(
            id INTEGER PRIMARY KEY
        )
        """
    )


if __name__ == "__main__":
    main()
