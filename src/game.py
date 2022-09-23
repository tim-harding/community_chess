import chess
import chess.svg
import cairosvg
import pathlib
import typing


class Game:
    def __init__(self, moves: typing.List[str]):
        self.board = chess.Board()
        for move in moves:
            self.board.push_san(move)

    def render(self):
        pathlib.Path("generated").mkdir(exist_ok=True)
        svg = chess.svg.board(self.board, size=1024)
        cairosvg.svg2png(svg, write_to="generated/board.png")


if __name__ == "__main__":
    moves = [
        'e2e4',
        'e7e5',
        'd1h5',
        'b8c6',
        'f1c4',
        'g8f6',
        'h5f7',
    ]
    game = Game(moves)
    game.render()
