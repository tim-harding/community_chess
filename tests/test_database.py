import unittest

import chess
from chessbot import database
from chessbot.database import NoInitialPostException, Outcome
from chessbot.moves import MoveNormal


def clear() -> None:
    try:
        database.open("test.db", reset=True)
    except NoInitialPostException:
        database.insert_post("init")


class TestDatabase(unittest.TestCase):
    def test_moves_for_game(self) -> None:
        clear()
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
        clear()
        database.new_game("a", Outcome.DRAW, "b")
        self.assertEqual("b", database.last_post_for_game())
        database.insert_post("asdf")
        self.assertEqual("asdf", database.last_post_for_game())

        database.new_game("c", Outcome.STALEMATE, "d")
        self.assertEqual("d", database.last_post_for_game())
        database.insert_post("arst")
        self.assertEqual("arst", database.last_post_for_game())


if __name__ == "__main__":
    unittest.main()
