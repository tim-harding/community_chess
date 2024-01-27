from __future__ import annotations
from enum import IntEnum, auto
from chessbot.outcome import Outcome


class Player(IntEnum):
    WHITE = auto()
    BLACK = auto()

    def __str__(self) -> str:
        match self:
            case Player.WHITE:
                return "white"
            case Player.BLACK:
                return "black"

    def resignation(self) -> Outcome:
        match self:
            case Player.WHITE:
                return Outcome.RESIGNATION_WHITE
            case Player.BLACK:
                return Outcome.RESIGNATION_BLACK

    @staticmethod
    def to_play(half_moves: int) -> Player:
        return Player.WHITE if half_moves % 2 == 0 else Player.BLACK
