import sqlite3


def insert_move(san: str):
    _db.execute("INSERT INTO move(san, game) VALUES (?, ?)", (san, current_game()))
    _db.commit()


def insert_game():
    _db.execute("INSERT INTO game DEFAULT VALUES")


def current_game() -> int:
    res = _db.execute("SELECT MAX(id) FROM game")
    (id,) = res.fetchone()
    return id


def insert_post(reddit_id: str, game: int):
    _db.execute("INSERT INTO post (reddit_id, game) VALUES (?, ?)", (reddit_id, game))
    _db.commit()


def last_post() -> str:
    res = _db.execute("SELECT reddit_id FROM post ORDER BY id DESC LIMIT 1")
    (id,) = res.fetchone()
    return id


def moves():
    out = []
    for row in _db.execute(
        "SELECT san FROM move WHERE game = (SELECT MAX(id) FROM game)"
    ):
        (san,) = row
        out.append(san)
    return out


def prepare():
    _db.execute(
        """
        CREATE TABLE IF NOT EXISTS game(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL
        )
        """
    )
    _db.execute(
        """
        CREATE TABLE IF NOT EXISTS move(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            san TEXT NOT NULL,
            game INTEGER NOT NULL,
            FOREIGN KEY(game) REFERENCES game(id)
        )
        """
    )
    _db.execute(
        """
        CREATE TABLE IF NOT EXISTS post(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            reddit_id TEXT NOT NULL,
            game INTEGER NOT NULL,
            FOREIGN KEY(game) REFERENCES game(id)
        )
        """
    )
    _db.commit()


_db = sqlite3.connect("communitychess.db")
