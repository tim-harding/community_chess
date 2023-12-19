import tempfile
import chess.svg
import cairosvg
import chess
import praw
import praw.models
import database


def main():
    database.prepare()
    database.insert_game()
    database.insert_move("f3")
    database.insert_move("e5")
    database.insert_move("g4")
    database.insert_move("Qh4")
    # database.insert_move("d4")
    # database.insert_move("f6")
    # database.insert_move("e4")
    # database.insert_move("g5")
    # database.insert_move("Qh5")
    make_post()


def make_post():
    board = chess.Board()
    for move in database.moves():
        board.push_san(move)
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

    reddit = praw.Reddit()
    sub = reddit.subreddit("communitychess")
    post = sub.submit_image(title, path)
    database.insert_post(post.id, database.current_game())


if __name__ == "__main__":
    main()
