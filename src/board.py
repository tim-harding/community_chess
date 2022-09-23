import chess
import chess.svg
import cairosvg
import pathlib
import typing


def from_moves(moves: typing.List[str]):
    board = chess.Board()
    for move in moves:
        board.push_san(move)
    return board


def render(board: chess.Board):
    pathlib.Path("generated").mkdir(exist_ok=True)
    svg = chess.svg.board(board, size=1024)
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
    board = from_moves(moves)
    render(board)
