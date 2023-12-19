import tempfile
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
    database.insert_game()
    play_move()


def play_move():
    post = reddit.submission(database.last_post())
    board = current_board()
    top_score = 0
    selected = None
    for comment in post.comments:
        move = move_for_comment(board, comment.body)
        match move:
            case BadMove.AMBIGUOUS:
                pass
            case BadMove.ILLEGAL:
                pass
            case BadMove.INVALID:
                pass
            case BadMove.UNKNOWN:
                pass
            case move:
                if comment.score > top_score:
                    selected = move
                    top_score = comment.score
    print(f"Selected {selected}")


def current_board() -> chess.Board:
    board = chess.Board()
    for move in database.moves():
        board.push_san(move)
    return board


def make_post():
    board = current_board()
    _, path = tempfile.mkstemp(".png")
    svg = chess.svg.board(board, size=1024)
    cairosvg.svg2png(svg, write_to=path)

    title = None
    if board.result() == "1-0":
        title = "Black wins"
    elif board.result() == "0-1":
        title = "White wins"
    elif board.result() == "*":
        move_number = board.ply() // 2 + 1
        to_play = "white" if board.ply() % 2 == 0 else "black"
        title = f"Move {move_number}, {to_play} to play"

    sub = reddit.subreddit("communitychess")
    post = sub.submit_image(title, path)
    database.insert_post(post.id, database.current_game())


if __name__ == "__main__":
    main()
