import sqlite3


def insert_post(url: str):
    _db.execute("INSERT INTO post(url, game) VALUES (?, ?)", (url, current_game()))
    _db.commit()


def insert_move(san: str):
    _db.execute("INSERT INTO move(san, game) VALUES (?, ?)", (san, current_game()))
    _db.commit()


def insert_game():
    _db.execute("INSERT INTO game DEFAULT VALUES")


def current_game() -> int:
    res = _db.execute("SELECT MAX(id) FROM game")
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
            url TEXT NOT NULL,
            game INTEGER NOT NULL,
            FOREIGN KEY(game) REFERENCES game(id)
        )
        """
    )
    _db.commit()


_db = sqlite3.connect("communitychess.db")
