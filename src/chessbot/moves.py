from collections.abc import Callable
from enum import IntEnum, auto
import re
from typing import Any, Final, NamedTuple, assert_never
import chess
from chess import Board


class MoveNormal(NamedTuple):
    move: chess.Move
    offer_draw: bool


class MoveResign:
    def __eq__(self, other: Any) -> bool:
        return isinstance(other, MoveResign)


Move = MoveNormal | MoveResign


class MoveErrorKind(IntEnum):
    AMBIGUOUS = auto()
    ILLEGAL = auto()

    def __str__(self) -> str:
        match self:
            case MoveErrorKind.AMBIGUOUS:
                return "ambiguous"
            case MoveErrorKind.ILLEGAL:
                return "ILLEGAL"


class MoveError(Exception):
    move_text: str
    kind: MoveErrorKind

    def __init__(self, move_text: str, kind: MoveErrorKind) -> None:
        self.move_text = move_text
        self.kind = kind

    def __eq__(self, other: Any) -> bool:
        match other:
            case MoveError():
                return self.move_text == other.move_text and self.kind == other.kind
            case _:
                return False


_MOVE_PATTERN: Final = re.compile(
    r"^ *(?:([Rr][Ee][Ss][Ii][Gg][Nn])|(?:([Oo0](?:-[Oo0]){1,2}|[KQRBNkqrbn]?[a-h]?[1-8]?x?[a-h][1-8](?:\=[QRBNqrbn])?[+#]?)|([a-h][1-8][a-h][1-8][KQRBNkqrbn]?))( +[Dd][Rr][Aa][Ww])?)"
)


def move_for_comment(
    comment: str,
    board: Board,
) -> Move | MoveError | None:
    first_line = comment.partition("\n")[0]
    m = _MOVE_PATTERN.search(first_line)
    match m:
        case None:
            return None
        case re.Match():
            match m.groups():
                case (str(), None, None, None):
                    return MoveResign()
                case (None, str() as san, None, None):
                    return _san_move(board, san, False)
                case (None, str() as san, None, str()):
                    return _san_move(board, san, True)
                case (None, None, str() as uci, None):
                    return _uci_move(board, uci, False)
                case (None, None, str() as uci, str()):
                    return _uci_move(board, uci, True)
                case _:
                    raise Exception("Unexpected regex match groups")
        case _:
            assert_never(m)


def _san_move(
    board: Board,
    san: str,
    offer_draw: bool,
) -> MoveNormal | MoveError | None:
    san = (
        san.replace("k", "K")
        .replace("q", "Q")
        .replace("r", "R")
        .replace("b", "B")
        .replace("n", "N")
        .replace("o", "O")
    )
    return _try_parse_move(Board.parse_san, board, san, offer_draw)


def _uci_move(
    board: Board,
    uci: str,
    offer_draw: bool,
) -> MoveNormal | MoveError | None:
    return _try_parse_move(Board.parse_uci, board, uci, offer_draw)


def _try_parse_move(
    f: Callable[[Board, str], chess.Move],
    board: Board,
    move_text: str,
    offer_draw: bool,
) -> MoveNormal | MoveError | None:
    try:
        return MoveNormal(f(board, move_text), offer_draw)
    except chess.InvalidMoveError:
        return None
    except chess.AmbiguousMoveError:
        return MoveError(move_text, MoveErrorKind.AMBIGUOUS)
    except chess.IllegalMoveError:
        return MoveError(move_text, MoveErrorKind.ILLEGAL)
