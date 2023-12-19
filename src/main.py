import praw
import praw.models
import sqlite3
from dataclasses import dataclass


DB = sqlite3.connect("communitychess.db")


@dataclass
class Move:
    number: int
    san: str
    url: str


def main():
    prepare_database()
    print(start_game())


def print_latest_post():
    reddit = praw.Reddit()
    sub = reddit.subreddit("communitychess")
    for post in sub.new(limit=1):
        print(post.title)


def start_game():
    cur = DB.cursor()
    cur.execute("INSERT INTO game DEFAULT VALUES")
    res = cur.execute("SELECT MAX(id) FROM game")
    (id,) = res.fetchone()
    DB.commit()
    return id


def prepare_database():
    cur = DB.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS move(
            number INTEGER NOT NULL,
            san TEXT NOT NULL,
            url TEXT NOT NULL,
            game INTEGER NOT NULL,
            FOREIGN KEY(game) REFERENCES game(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS game(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL
        )
        """
    )
    DB.commit()


if __name__ == "__main__":
    main()
