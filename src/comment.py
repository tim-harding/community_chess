import chess
import re
import enum


_MOVE_ERROR_REGEX = re.compile("^(ambiguous|illegal|invalid) san: .*")


class MoveErrorReason(enum.Enum):
    AMBIGUOUS = 1
    ILLEGAL = 2
    INVALID = 3


def move_for_comment(board: chess.Board, text) -> chess.Move | MoveErrorReason:
    candidate = text.split(None, maxsplit=1)[0]
    try:
        return board.parse_san(candidate)
    except ValueError as e:
        match = _MOVE_ERROR_REGEX.match(str(e))
        assert match is not None
        reason = match.group(1)
        if reason == "ambiguous":
            return MoveErrorReason.AMBIGUOUS
        elif reason == "illegal":
            return MoveErrorReason.ILLEGAL
        else:
            return MoveErrorReason.INVALID


def _basic_comment_test():
    board = chess.Board()
    actual = move_for_comment(board, "e4\nI think this move is good :)")
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
    actual = move_for_comment(board, "Ng5 is a good one!")
    assert actual == MoveErrorReason.AMBIGUOUS


def _illegal_move_test():
    board = chess.Board()
    actual = move_for_comment(board, "Nc4")
    assert actual == MoveErrorReason.ILLEGAL


if __name__ == "__main__":
    _basic_comment_test()
    _ambiguous_move_test()
    _illegal_move_test()
