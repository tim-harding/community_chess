import chess
import re
import enum


MOVE_ERROR_REGEX = re.compile("^(ambiguous|illegal|invalid) san: .*")
MoveErrorReason = enum.Enum("MoveErrorReason", "AMBIGUOUS ILLEGAL INVALID")


def move_from_comment(board: chess.Board, comment: str) -> chess.Move:
    candidate = comment.split(None, maxsplit=1)[0]
    try:
        return board.parse_san(candidate)
    except ValueError as e:
        match = MOVE_ERROR_REGEX.match(str(e))
        reason = match.group(1)
        if reason == "ambiguous":
            return MoveErrorReason.AMBIGUOUS
        elif reason == "illegal":
            return MoveErrorReason.ILLEGAL
        else:
            return MoveErrorReason.INVALID


def _basic_comment_test():
    comment = "e4\nI think this move is good :)"
    board = chess.Board()
    actual = move_from_comment(board, comment)
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
    comment = "Ng5 is a good one!"
    actual = move_from_comment(board, comment)
    assert actual == MoveErrorReason.AMBIGUOUS


def _straight_up_illegal_test():
    board = chess.Board()
    comment = "Nc4"
    actual = move_from_comment(board, comment)
    assert actual == MoveErrorReason.ILLEGAL


if __name__ == "__main__":
    _basic_comment_test()
    _ambiguous_move_test()
    _straight_up_illegal_test()
