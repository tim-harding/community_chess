from enum import IntEnum, auto
import sqlite3
from sqlite3.dbapi2 import Connection, Cursor
import os
from typing import NamedTuple

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


SqlData = str | int | float | None


class Database:
    _connection: Connection

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def _execute(self, sql: str, *parameters: SqlData) -> Cursor:
        return self._connection.execute(sql, parameters)

    def _commit(self) -> None:
        self._connection.commit()

    def new_game(
        self,
        previous_game_final_post: str,
        previous_game_outcome: Outcome,
        new_game_initial_post: str,
    ) -> None:
        self.insert_post(previous_game_final_post, commit=False)
        self._execute(
            """
            UPDATE game
            SET outcome    = ?, 
                final_post = ?
            WHERE id = (
                SELECT MAX(id) 
                FROM game
            )
            """,
            int(previous_game_outcome),
            previous_game_final_post,
        )
        self._execute(
            """
            INSERT INTO game DEFAULT VALUES
            """
        )
        self.insert_post(new_game_initial_post, commit=False)
        self._commit()

    def insert_post(self, reddit_id: str, commit: bool = True) -> None:
        self._execute(
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
            reddit_id,
        )
        if commit:
            self._commit()

    def previous_post(self) -> str:
        res = self._execute(
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
        self,
        move: MoveNormal,
        next_post: str,
    ) -> None:
        self._execute(
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
            move.move.uci(),
            int(move.offer_draw),
        )
        self.insert_post(next_post, commit=False)
        self._commit()

    def moves(self) -> list[MoveNormal]:
        out: list[MoveNormal] = []
        for row in self._execute(
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


class NeedsInitialPost(NamedTuple):
    database: Database


def open(path: str, reset: bool = False) -> Database | NeedsInitialPost:
    if reset:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    database = Database(sqlite3.connect(path))

    database._execute(
        """
        CREATE TABLE IF NOT EXISTS game(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            outcome INTEGER CHECK(outcome >= 1 AND outcome <= 7) DEFAULT 1 NOT NULL,
            final_post INTEGER,
            FOREIGN KEY(final_post) REFERENCES post(id)
        )
        """
    )

    database._execute(
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

    database._execute(
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
    res = database._execute(
        """
        SELECT MAX(id) 
        FROM game
        """
    )
    match res.fetchone():
        case (int(),):
            pass
        case (None,):
            database._execute(
                """
                INSERT INTO game DEFAULT VALUES
                """
            )
        case _:
            raise ResponseFormatException()

    database._commit()

    res = database._execute(
        """
        SELECT MAX(id)
        FROM post
        """
    )
    match res.fetchone():
        case (int(),):
            return database
        case (None,):
            return NeedsInitialPost(database)
        case _:
            raise ResponseFormatException()
