from enum import IntEnum, auto
import sqlite3
from sqlite3.dbapi2 import Connection
import os

import chess
from .moves import MoveNormal


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


_DB: Connection | None = None


def open_db(path: str, reset: bool = False) -> None:
    if reset:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    global _DB
    _DB = sqlite3.connect(path)
    _DB.execute(
        """
        CREATE TABLE IF NOT EXISTS game(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            outcome INTEGER CHECK(outcome >= 1 AND outcome <= 7) DEFAULT 1 NOT NULL
        )
        """
    )
    _DB.execute(
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
    _DB.execute(
        """
        CREATE TABLE IF NOT EXISTS post(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            reddit_id TEXT NOT NULL,
            game INTEGER NOT NULL,
            FOREIGN KEY(game) REFERENCES game(id)
        )
        """
    )
    _DB.commit()


def set_game_outcome(outcome: Outcome) -> None:
    assert _DB is not None
    _DB.execute(
        """
        UPDATE game 
        SET outcome = ? 
        WHERE id = (SELECT MAX(id) FROM game)
        """,
        (int(outcome),),
    )
    _DB.commit()


def insert_game() -> None:
    assert _DB is not None
    _DB.execute("INSERT INTO game DEFAULT VALUES")
    _DB.commit()


def current_game() -> int:
    assert _DB is not None
    res = _DB.execute("SELECT MAX(id) FROM game")
    match res.fetchone():
        case (int() as id,):
            return id
        case (None,):
            raise NoRowsException()
        case _:
            raise ResponseFormatException()


def insert_post(reddit_id: str) -> None:
    assert _DB is not None
    _DB.execute(
        """
        INSERT INTO post (reddit_id, game) 
        VALUES (?, (SELECT MAX(id) FROM game))
        """,
        (reddit_id,),
    )
    _DB.commit()


def last_post_for_game() -> str:
    assert _DB is not None
    res = _DB.execute(
        """
        SELECT reddit_id 
        FROM post 
        WHERE game = (SELECT MAX(id) FROM game) 
        ORDER BY id DESC 
        LIMIT 1
        """
    )
    match res.fetchone():
        case (str() as id,):
            return id
        case None:
            raise NoRowsException()
        case _:
            raise ResponseFormatException()


def insert_move(move: MoveNormal) -> None:
    assert _DB is not None
    _DB.execute(
        """
        INSERT INTO move(uci, draw_offer, game) 
        VALUES (?, ?, (SELECT MAX(id) FROM game))
        """,
        (move.move.uci(), int(move.offer_draw)),
    )
    _DB.commit()


def moves() -> list[MoveNormal]:
    assert _DB is not None
    out: list[MoveNormal] = []
    for row in _DB.execute(
        """
        SELECT uci, draw_offer 
        FROM move 
        WHERE game = (SELECT MAX(id) FROM game)
        """
    ):
        match row:
            case (str() as uci, int() as draw_offer):
                out.append(MoveNormal(chess.Move.from_uci(uci), draw_offer == 1))
            case _:
                raise ResponseFormatException()
    return out
