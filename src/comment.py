import chess
import re
import enum


_MOVE_ERROR_REGEX = re.compile("^(ambiguous|illegal|invalid) san: .*")


class BadMove(enum.Enum):
    AMBIGUOUS = 1
    ILLEGAL = 2
    INVALID = 3
    UNKNOWN = 4


def move_for_comment(board: chess.Board, comment: str) -> str | BadMove:
    candidate = comment.split(None, maxsplit=1)[0]
    try:
        board.parse_san(candidate)
    except ValueError as e:
        match _MOVE_ERROR_REGEX.match(str(e)):
            case None:
                return BadMove.UNKNOWN
            case other:
                match other.group(1):
                    case "ambiguous":
                        return BadMove.AMBIGUOUS
                    case "illegal":
                        return BadMove.ILLEGAL
                    case "invalid":
                        return BadMove.INVALID
                    case _:
                        return BadMove.UNKNOWN
    return candidate


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
    assert actual == BadMove.AMBIGUOUS


def _illegal_move_test():
    board = chess.Board()
    actual = move_for_comment(board, "Nc4")
    assert actual == BadMove.ILLEGAL


if __name__ == "__main__":
    _basic_comment_test()
    _ambiguous_move_test()
    _illegal_move_test()
