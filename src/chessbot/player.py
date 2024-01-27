from __future__ import annotations
from enum import StrEnum, auto
from chessbot.outcome import Outcome


class Player(StrEnum):
    WHITE = auto()
    BLACK = auto()

    def opponent(self) -> Player:
        match self:
            case Player.WHITE:
                return Player.BLACK
            case Player.BLACK:
                return Player.WHITE

    def resignation(self) -> Outcome:
        match self:
            case Player.WHITE:
                return Outcome.RESIGNATION_WHITE
            case Player.BLACK:
                return Outcome.RESIGNATION_BLACK

    @staticmethod
    def to_play(half_moves: int) -> Player:
        return Player.WHITE if half_moves % 2 == 0 else Player.BLACK
