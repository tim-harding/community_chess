import unittest

import chess
from chessbot import database
from chessbot.moves import MoveNormal


def clear() -> None:
    database.open_db("test.db", reset=True)


class TestDatabase(unittest.TestCase):
    def test_no_initial_post(self) -> None:
        clear()
        self.assertRaises(database.NoRowsException, database.last_post_for_game)

    def test_no_initial_game(self) -> None:
        clear()
        self.assertRaises(database.NoRowsException, database.current_game)

    def test_initial_post_requires_game(self) -> None:
        clear()
        self.assertRaises(Exception, database.insert_post)

    def test_game_insertions(self) -> None:
        clear()
        database.insert_game()
        self.assertEqual(1, database.current_game())
        database.insert_game()
        self.assertEqual(2, database.current_game())

    def test_moves_for_game(self) -> None:
        clear()
        board = chess.Board()
        e4 = MoveNormal(board.push_san("e4"), False)
        e5 = MoveNormal(board.push_san("e5"), True)
        database.insert_game()
        database.insert_move(e4)
        database.insert_move(e5)
        self.assertEqual([e4, e5], database.moves())

        database.insert_game()
        board = chess.Board()
        nf3 = MoveNormal(board.push_san("Nf3"), False)
        d5 = MoveNormal(board.push_san("d5"), False)
        database.insert_game()
        database.insert_move(nf3)
        database.insert_move(d5)
        self.assertEqual([nf3, d5], database.moves())

    def test_latest_post(self) -> None:
        clear()
        database.insert_game()
        database.insert_post("asdf")
        self.assertEqual("asdf", database.last_post_for_game())
        database.insert_post("arst")
        self.assertEqual("arst", database.last_post_for_game())


if __name__ == "__main__":
    unittest.main()
