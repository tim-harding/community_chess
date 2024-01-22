from enum import IntEnum, auto
import sqlite3

import chess
from moves import MoveNormal

_db = sqlite3.connect("communitychess.db")


class Outcome(IntEnum):
    ONGOING = auto()
    DRAW = auto()
    STALEMATE = auto()
    VICTORY_WHITE = auto()
    VICTORY_BLACK = auto()
    RESIGNATION_WHITE = auto()
    RESIGNATION_BLACK = auto()


class ResponseFormatException(Exception):
    def __init__(self) -> None:
        super().__init__("Unexpected database query response format")


class NoRowsException(Exception):
    def __init__(self) -> None:
        super().__init__("Database response contains no rows")


def set_game_outcome(outcome: Outcome):
    _db.execute(
        "UPDATE game SET outcome = ? WHERE id = (SELECT MAX(id) FROM game)",
        (int(outcome),),
    )
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


def insert_move(move: MoveNormal) -> None:
    _db.execute(
        "INSERT INTO move(uci, draw_offer, game) VALUES (?, ?, (SELECT MAX(id) FROM game))",
        (move.move.uci(), int(move.offer_draw)),
    )
    _db.commit()


def moves() -> list[MoveNormal]:
    out: list[MoveNormal] = []
    for row in _db.execute(
        "SELECT uci, draw_offer FROM move WHERE game = (SELECT MAX(id) FROM game)"
    ):
        match row:
            case (str() as uci, int() as draw_offer):
                out.append(MoveNormal(chess.Move.from_uci(uci), draw_offer == 1))
            case _:
                raise ResponseFormatException()
    return out


def prepare() -> None:
    for outcome in Outcome:
        assert outcome >= 1 and outcome <= 7

    _db.execute(
        """
        CREATE TABLE IF NOT EXISTS game(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL
            outcome INTEGER CHECK(outcome >= 1 AND outcome <= 6) NOT NULL
        )
        """
    )
    _db.execute(
        """
        CREATE TABLE IF NOT EXISTS move(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            uci TEXT NOT NULL,
            draw_offer INTEGER NOT NULL,
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
