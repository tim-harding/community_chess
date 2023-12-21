import argparse
import tempfile
import asyncio
from asyncio import Queue
from typing import assert_never
from asyncpraw.reddit import Submission
from asyncprawcore import logging
from chess import AmbiguousMoveError, Board, IllegalMoveError, InvalidMoveError
import chess.svg
import cairosvg
import chess
from asyncpraw import Reddit
from asyncpraw.models import Comment
import database


class NotifyPlayMove:
    pass


MsgQueue = Queue[Comment | NotifyPlayMove]


def main() -> None:
    parser = argparse.ArgumentParser(prog="CommunityChess Server")
    parser.add_argument(
        "-l",
        "--log",
        choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
        default="WARN",
        help="Sets the logging verbosity level",
    )
    args = parser.parse_args()
    logging.basicConfig(level=args.log)
    # TODO: Guarantee a game and post in the database
    database.prepare()
    asyncio.run(async_main())


async def async_main() -> None:
    logging.info("Entering async_main")
    reddit = Reddit()
    queue: MsgQueue = Queue()
    tasks = [
        asyncio.create_task(send_play_move_notifications(queue)),
        asyncio.create_task(forward_comments(reddit, queue)),
        asyncio.create_task(handle_messages(reddit, queue)),
    ]
    for task in tasks:
        await task


async def handle_messages(reddit: Reddit, queue: MsgQueue) -> None:
    logging.info("entered handle_messages")
    current_post = await reddit.submission(database.last_post())
    board = Board()
    for move in database.moves():
        board.push_san(move)

    while True:
        msg = await queue.get()
        logging.info(f"Got message {msg}")
        match msg:
            case NotifyPlayMove():
                match await play_move(reddit, board, current_post):
                    case None:
                        pass
                    case Submission() as post:
                        current_post = post
            case Comment() as comment:
                reply = reply_for_comment(comment.body, board)
                await comment.reply(reply)
                logging.info(f"Responded to comment '{comment.body}' with '{reply}'")


async def forward_comments(reddit: Reddit, queue: MsgQueue) -> None:
    logging.info("entered forward_comments")
    sub = await reddit.subreddit("communitychess")
    async for comment in sub.stream.comments(skip_existing=True):
        TOP_LEVEL_COMMENT_PREFIX = "t3_"
        if comment.parent_id[:3] == TOP_LEVEL_COMMENT_PREFIX:
            logging.info("Sending comment")
            await queue.put(comment)


async def send_play_move_notifications(queue: MsgQueue) -> None:
    logging.info("entered send_play_move_notifications")
    while True:
        # TODO: Play move at specific times
        await asyncio.sleep(60)
        logging.info("Sending play move notification")
        await queue.put(NotifyPlayMove())


def reply_for_comment(comment: str, board: Board) -> str:
    res = move_for_comment(comment, board)
    match res:
        case str() as move:
            return f"I found this move in your comment: {move}"
        case InvalidMoveError() | AmbiguousMoveError() | IllegalMoveError() as e:
            return str(e)
        case _:
            assert_never(res)


async def play_move(
    reddit: Reddit, board: Board, post: Submission
) -> Submission | None:
    res = select_move(board, post)
    logging.info(f"Playing move {res}")
    match res:
        case None:
            return None
        case str() as move:
            database.insert_move(move)
            board.push_san(move)
            if board.result() != "*":
                await make_post(reddit, board)
                database.insert_game()
                board.reset()
            return await make_post(reddit, board)
        case _:
            assert_never(res)


def select_move(board: Board, post: Submission) -> str | None:
    top_score = 0
    selected = None
    for comment in post.comments:
        if comment.score > top_score:
            match move_for_comment(comment.body, board):
                case str() as move:
                    selected = move
                    top_score = comment.score
                case _:
                    pass
    return selected


async def make_post(reddit: Reddit, board: Board) -> Submission:
    _, path = tempfile.mkstemp(".png")
    svg = chess.svg.board(board, size=1024)
    cairosvg.svg2png(svg, write_to=path)

    title = title_for_result(board.result(), board.ply())
    sub = await reddit.subreddit("communitychess")
    post = await sub.submit_image(title, path)
    database.insert_post(post.id, database.current_game())
    return post


def title_for_result(result: str, half_moves: int) -> str:
    match result:
        case "1-0":
            return "White wins"
        case "0-1":
            return "Black wins"
        case "*":
            move_number = half_moves // 2 + 1
            to_play = "white" if half_moves % 2 == 0 else "black"
            return f"Move {move_number}, {to_play} to play"
        case _:
            raise Exception("Unknown game result")


def move_for_comment(
    comment: str,
    board: chess.Board,
) -> str | chess.InvalidMoveError | chess.AmbiguousMoveError | chess.IllegalMoveError:
    # TODO: Find the first suggested move that may not be the first move
    candidate = comment.split(None, maxsplit=1)[0]
    try:
        board.parse_san(candidate)
    except chess.InvalidMoveError as e:
        return e
    except chess.AmbiguousMoveError as e:
        return e
    except chess.IllegalMoveError as e:
        return e
    return candidate


if __name__ == "__main__":
    main()
