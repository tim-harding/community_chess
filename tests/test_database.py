import unittest
import chess
from chessbot.database import (
    open as open_database,
    Database,
    NeedsInitialPost,
    Outcome,
)
from chessbot.moves import MoveNormal


def cleared() -> Database:
    match open_database("test.db", reset=True):
        case Database() as db:
            return db
        case NeedsInitialPost(db):
            db.insert_post("init")
            return db


class TestDatabase(unittest.TestCase):
    def test_moves_for_game(self) -> None:
        database = cleared()
        board = chess.Board()
        e4 = MoveNormal(board.push_san("e4"), False)
        e5 = MoveNormal(board.push_san("e5"), True)
        database.new_game("a", Outcome.VICTORY_WHITE, "b")
        database.play_move(e4, "c")
        database.play_move(e5, "d")
        self.assertEqual([e4, e5], database.moves())

        board = chess.Board()
        nf3 = MoveNormal(board.push_san("Nf3"), False)
        d5 = MoveNormal(board.push_san("d5"), False)
        database.new_game("e", Outcome.RESIGNATION_BLACK, "f")
        database.play_move(nf3, "g")
        database.play_move(d5, "h")
        self.assertEqual([nf3, d5], database.moves())

    def test_latest_post(self) -> None:
        database = cleared()
        database.new_game("a", Outcome.DRAW, "b")
        self.assertEqual("b", database.previous_post())
        database.insert_post("asdf")
        self.assertEqual("asdf", database.previous_post())

        database.new_game("c", Outcome.STALEMATE, "d")
        self.assertEqual("d", database.previous_post())
        database.insert_post("arst")
        self.assertEqual("arst", database.previous_post())


if __name__ == "__main__":
    unittest.main()
