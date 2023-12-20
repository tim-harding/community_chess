import tempfile
import sys
import chess.svg
import cairosvg
import chess
import asyncpraw
import asyncpraw.models
from praw.reddit import asyncio
from comment import BadMove, move_for_comment
import database


def main():
    database.prepare()
    asyncio.run(async_main())


async def async_main():
    reddit = asyncpraw.Reddit()
    play_moves_regularly_task = asyncio.create_task(play_moves_regularly(reddit))
    await play_moves_regularly_task


async def play_moves_regularly(reddit: asyncpraw.Reddit):
    while True:
        await play_move(reddit)
        await asyncio.sleep(60)


async def play_move(reddit: asyncpraw.Reddit):
    board = current_board()
    match await select_move(board, reddit):
        case None:
            print("No move to play", file=sys.stderr)
        case move:
            database.insert_move(move)
            board.push_san(move)
            await make_post(board, reddit)
            if board.result() != "*":
                database.insert_game()
                await make_post(chess.Board(), reddit)


async def select_move(board: chess.Board, reddit: asyncpraw.Reddit) -> str | None:
    post = await reddit.submission(database.last_post())
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


async def make_post(board: chess.Board, reddit: asyncpraw.Reddit):
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

    sub = await reddit.subreddit("communitychess")
    post = await sub.submit_image(title, path)
    database.insert_post(post.id, database.current_game())


def current_board() -> chess.Board:
    board = chess.Board()
    for move in database.moves():
        board.push_san(move)
    return board


if __name__ == "__main__":
    main()
