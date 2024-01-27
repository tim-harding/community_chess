from enum import IntEnum, auto
import chess
from chess import Board, Termination
from chessbot.moves import MoveNormal


class Outcome(IntEnum):
    ONGOING = auto()
    DRAW = auto()
    STALEMATE = auto()
    VICTORY_WHITE = auto()
    VICTORY_BLACK = auto()
    RESIGNATION_WHITE = auto()
    RESIGNATION_BLACK = auto()


def for_move(move: MoveNormal, board: Board, moves: list[MoveNormal]) -> Outcome:
    print(move, moves)
    return (
        Outcome.DRAW
        if len(moves) > 0 and moves[-1].offer_draw and move.offer_draw
        else _for_board(board)
    )


def _for_board(board: Board) -> Outcome:
    outcome = board.outcome(claim_draw=True)
    match outcome:
        case None:
            return Outcome.ONGOING
        case chess.Outcome():
            match outcome.termination:
                case Termination.CHECKMATE:
                    match outcome.winner:
                        case True:
                            return Outcome.VICTORY_WHITE
                        case False:
                            return Outcome.VICTORY_BLACK
                        case None:
                            raise Exception("Expected a winner")
                case Termination.STALEMATE:
                    return Outcome.STALEMATE
                case (
                    Termination.INSUFFICIENT_MATERIAL
                    | Termination.SEVENTYFIVE_MOVES
                    | Termination.FIVEFOLD_REPETITION
                    | Termination.FIFTY_MOVES
                    | Termination.THREEFOLD_REPETITION
                ):
                    return Outcome.DRAW
                case (
                    Termination.VARIANT_WIN
                    | Termination.VARIANT_LOSS
                    | Termination.VARIANT_DRAW
                ):
                    raise Exception("Unexpected variant termination")
