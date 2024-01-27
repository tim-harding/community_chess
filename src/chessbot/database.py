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


class NoInitialPostException(Exception):
    def __init__(self) -> None:
        super().__init__("The database does not contain an initial post")


_DB: Connection | None = None


def open(path: str, reset: bool = False) -> None:
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
            outcome INTEGER CHECK(outcome >= 1 AND outcome <= 7) DEFAULT 1 NOT NULL,
            final_post INTEGER,
            FOREIGN KEY(final_post) REFERENCES post(id)
        )
        """
    )

    _DB.execute(
        """
        CREATE TABLE IF NOT EXISTS move(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            uci TEXT NOT NULL,
            draw_offer INTEGER NOT NULL,
            post INTEGER NOT NULL,
            FOREIGN KEY(post) REFERENCES post(id)
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

    # Populate a game if none exists
    res = _DB.execute(
        """
        SELECT MAX(id) 
        FROM game
        """
    )
    match res.fetchone():
        case (int(),):
            pass
        case (None,):
            _DB.execute(
                """
                INSERT INTO game DEFAULT VALUES
                """
            )
        case _:
            raise ResponseFormatException()

    res = _DB.execute(
        """
        SELECT MAX(id)
        FROM post
        """
    )
    match res.fetchone():
        case (int(),):
            pass
        case (None,):
            raise NoInitialPostException()
        case _:
            raise ResponseFormatException()

    _DB.commit()


def new_game(
    previous_game_final_post: str,
    previous_game_outcome: Outcome,
    new_game_initial_post: str,
) -> None:
    assert _DB is not None
    insert_post(previous_game_final_post, commit=False)
    _DB.execute(
        """
        UPDATE game
        SET outcome    = ?, 
            final_post = ?
        WHERE id = (
            SELECT MAX(id) 
            FROM game
        )
        """,
        (int(previous_game_outcome), previous_game_final_post),
    )
    _DB.execute(
        """
        INSERT INTO game DEFAULT VALUES
        """
    )
    insert_post(new_game_initial_post, commit=False)
    _DB.commit()


def insert_post(reddit_id: str, commit: bool = True) -> None:
    assert _DB is not None
    _DB.execute(
        """
        INSERT INTO post (reddit_id, game) 
        VALUES (
            ?, 
            (
                SELECT MAX(id) 
                FROM game
            )
        )
        """,
        (reddit_id,),
    )
    if commit:
        _DB.commit()


def last_post_for_game() -> str:
    assert _DB is not None
    res = _DB.execute(
        """
        SELECT reddit_id 
        FROM post 
        WHERE game = (
            SELECT MAX(id) 
            FROM game
        )
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


def play_move(
    move: MoveNormal,
    next_post: str,
) -> None:
    assert _DB is not None
    _DB.execute(
        """
        INSERT INTO move(uci, draw_offer, post) 
        VALUES (
            ?, 
            ?, 
            (
                SELECT MAX(id) 
                FROM post 
                WHERE post.game = (
                    SELECT MAX(id) 
                    FROM game
                )
            )
        )
        """,
        (move.move.uci(), int(move.offer_draw)),
    )
    insert_post(next_post, commit=False)
    _DB.commit()


def moves() -> list[MoveNormal]:
    assert _DB is not None
    out: list[MoveNormal] = []
    for row in _DB.execute(
        """
        SELECT uci, draw_offer 
        FROM move 
        INNER JOIN post
        ON post.id = move.post
        WHERE post.game = (
            SELECT MAX(id) 
            FROM game
        )
        """
    ):
        match row:
            case (str() as uci, int() as draw_offer):
                out.append(MoveNormal(chess.Move.from_uci(uci), draw_offer == 1))
            case _:
                raise ResponseFormatException()
    return out
