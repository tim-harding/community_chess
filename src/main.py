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
    database.insert_move("e4")
    database.insert_move("e5")
    make_post()


def make_post():
    board = chess.Board()
    for move in database.moves():
        board.push_san(move)
    _, path = tempfile.mkstemp(".png")
    svg = chess.svg.board(board, size=1024)
    cairosvg.svg2png(svg, write_to=path)

    reddit = praw.Reddit()
    sub = reddit.subreddit("communitychess")
    sub.submit_image("Test", path)


if __name__ == "__main__":
    main()
