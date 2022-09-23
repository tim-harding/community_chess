import chess
import re
import enum


_MOVE_ERROR_REGEX = re.compile("^(ambiguous|illegal|invalid) san: .*")
_MoveErrorReason = enum.Enum("MoveErrorReason", "AMBIGUOUS ILLEGAL INVALID")


class Comment:
    def __init__(self, text: str, upvotes: int):
        self.text = text
        self.upvotes = upvotes

    def move(self, board: chess.Board) -> chess.Move:
        candidate = self.text.split(None, maxsplit=1)[0]
        try:
            return board.parse_san(candidate)
        except ValueError as e:
            match = _MOVE_ERROR_REGEX.match(str(e))
            reason = match.group(1)
            if reason == "ambiguous":
                return _MoveErrorReason.AMBIGUOUS
            elif reason == "illegal":
                return _MoveErrorReason.ILLEGAL
            else:
                return _MoveErrorReason.INVALID


def _basic_comment_test():
    comment = Comment("e4\nI think this move is good :)", 1)
    board = chess.Board()
    actual = comment.move(board)
    expected = chess.Move(chess.E2, chess.E4)
    assert actual == expected


def _ambiguous_move_test():
    board = chess.Board()
    moves = [
        "Nc3",
        "a6",
        "Ne4",
        "b6",
        "Nf3",
        "c6",
    ]
    for move in moves:
        board.push_san(move)
    comment = Comment("Ng5 is a good one!", 1)
    actual = comment.move(board)
    assert actual == _MoveErrorReason.AMBIGUOUS


def _illegal_move_test():
    board = chess.Board()
    comment = Comment("Nc4", 1)
    actual = comment.move(board)
    assert actual == _MoveErrorReason.ILLEGAL


if __name__ == "__main__":
    _basic_comment_test()
    _ambiguous_move_test()
    _illegal_move_test()
