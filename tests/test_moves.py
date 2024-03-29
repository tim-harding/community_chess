import unittest
from chessbot.moves import (
    MoveDraw,
    MoveError,
    MoveErrorKind,
    MoveResign,
    move_for_comment,
    MoveNormal,
)
import chess
from chess import Board


class TestMoves(unittest.TestCase):
    def test_not_found(self):
        self.assertEqual(move_for_comment("", Board()), None)
        self.assertEqual(move_for_comment("I like our position", Board()), None)

    def test_found(self):
        self.assertEqual(
            move_for_comment("e4", Board()),
            MoveNormal(chess.Move(chess.E2, chess.E4), False),
        )
        self.assertEqual(
            move_for_comment("nf3", Board()),
            MoveNormal(chess.Move(chess.G1, chess.F3), False),
        )

    def test_found_multiline(self):
        self.assertEqual(
            move_for_comment("e4 looks good", Board()),
            MoveNormal(chess.Move(chess.E2, chess.E4), False),
        )
        self.assertEqual(
            move_for_comment("  nf3, should we resign?", Board()),
            MoveNormal(chess.Move(chess.G1, chess.F3), False),
        )

    def test_found_with_draw(self):
        self.assertEqual(
            move_for_comment("e4 Draw", Board()),
            MoveNormal(chess.Move(chess.E2, chess.E4), True),
        )
        self.assertEqual(
            move_for_comment("Nf3 draw, this is drawish", Board()),
            MoveNormal(chess.Move(chess.G1, chess.F3), True),
        )

    def test_illegal(self):
        self.assertEqual(
            move_for_comment("ke2", Board()), MoveError("Ke2", MoveErrorKind.ILLEGAL)
        )

    def test_ambiguous(self):
        board = Board()
        board.push_san("e3")
        board.push_san("e6")
        board.push_san("Nc3")
        board.push_san("e5")
        self.assertEqual(
            move_for_comment("Ne2", board), MoveError("Ne2", MoveErrorKind.AMBIGUOUS)
        )

    def test_resign(self):
        self.assertEqual(move_for_comment("resign", Board()), MoveResign())

    def test_bare_draw(self):
        self.assertEqual(move_for_comment("draw", Board()), MoveDraw())


if __name__ == "__main__":
    unittest.main()
