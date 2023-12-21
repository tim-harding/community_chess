import sqlite3

_db = sqlite3.connect("communitychess.db")


class ResponseFormatException(Exception):
    def __init__(self) -> None:
        super().__init__("Unexpected database query response format")


class NoRowsException(Exception):
    def __init__(self) -> None:
        super().__init__("Database response contains no rows")


def insert_move(san: str) -> None:
    _db.execute("INSERT INTO move(san, game) VALUES (?, ?)", (san, current_game()))
    _db.commit()


def insert_game() -> None:
    _db.execute("INSERT INTO game DEFAULT VALUES")
    _db.commit()


def current_game() -> int:
    res = _db.execute("SELECT MAX(id) FROM game")
    match res.fetchone():
        case (int() as id,):
            return id
        case (None,):
            raise NoRowsException()
        case _:
            raise ResponseFormatException()


def insert_post(reddit_id: str, game: int) -> None:
    _db.execute("INSERT INTO post (reddit_id, game) VALUES (?, ?)", (reddit_id, game))
    _db.commit()


def last_post() -> str:
    res = _db.execute("SELECT reddit_id FROM post ORDER BY id DESC LIMIT 1")
    match res.fetchone():
        case (str() as id,):
            return id
        case None:
            raise NoRowsException()
        case _:
            raise ResponseFormatException()


def moves() -> list[str]:
    out: list[str] = []
    for row in _db.execute(
        "SELECT san FROM move WHERE game = (SELECT MAX(id) FROM game)"
    ):
        match row:
            case (str() as san,):
                out.append(san)
            case _:
                raise ResponseFormatException()
    return out


def prepare() -> None:
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
