import tempfile
import sys
import chess.svg
import cairosvg
import chess
import praw
import praw.models
from comment import BadMove, move_for_comment
import database

reddit = praw.Reddit()


def main():
    database.prepare()
    play_move()


def play_move():
    board = current_board()
    match select_move(board):
        case None:
            print("No move to play", file=sys.stderr)
        case move:
            database.insert_move(move)
            board.push_san(move)
            make_post(board)
            if board.result() != "*":
                database.insert_game()
                make_post(chess.Board())


def select_move(board: chess.Board) -> str | None:
    post = reddit.submission(database.last_post())
    top_score = 0
    selected = None
    for comment in post.comments:
        move = move_for_comment(board, comment.body)
        match move:
            case (
                BadMove.AMBIGUOUS
                | BadMove.ILLEGAL
                | BadMove.INVALID
                | BadMove.UNKNOWN
            ):
                pass
            case move:
                if comment.score > top_score:
                    selected = move
                    top_score = comment.score
    return selected


def make_post(board: chess.Board):
    _, path = tempfile.mkstemp(".png")
    svg = chess.svg.board(board, size=1024)
    cairosvg.svg2png(svg, write_to=path)

    title = None
    if board.result() == "1-0":
        title = "White wins"
    elif board.result() == "0-1":
        title = "Black wins"
    elif board.result() == "*":
        move_number = board.ply() // 2 + 1
        to_play = "white" if board.ply() % 2 == 0 else "black"
        title = f"Move {move_number}, {to_play} to play"

    sub = reddit.subreddit("communitychess")
    post = sub.submit_image(title, path)
    database.insert_post(post.id, database.current_game())


def current_board() -> chess.Board:
    board = chess.Board()
    for move in database.moves():
        board.push_san(move)
    return board


if __name__ == "__main__":
    main()
