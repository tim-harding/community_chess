import argparse
import tempfile
import asyncio
from asyncio import Queue
from typing import assert_never
from asyncpraw.reddit import Submission
from chess import AmbiguousMoveError, Board, IllegalMoveError, InvalidMoveError
import chess.svg
import cairosvg
import chess
from asyncpraw import Reddit
from asyncpraw.models import Comment
import database
from database import NoRowsException
import logging


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

    database.prepare()
    try:
        database.current_game()
    except NoRowsException:
        database.insert_game()

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

    board = Board()
    for move in database.moves():
        board.push_san(move)

    try:
        logging.info("Checking for last post existence")
        database.last_post()
    except NoRowsException:
        logging.info("Making initial post")
        await make_post(reddit, board)

    current_post = await reddit.submission(database.last_post())
    logging.info("Entering message queue loop")
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
        is_top_level = comment.parent_id[:3] == TOP_LEVEL_COMMENT_PREFIX
        is_current_post = comment.parent_id[3:] == database.last_post()
        if is_top_level and is_current_post:
            logging.info("Sending comment")
            await queue.put(comment)


async def send_play_move_notifications(queue: MsgQueue) -> None:
    logging.info("entered send_play_move_notifications")
    while True:
        # TODO: Play move at specific times
        await asyncio.sleep(5)
        logging.info("Sending play move notification")
        await queue.put(NotifyPlayMove())


def reply_for_comment(comment: str, board: Board) -> str:
    res = move_for_comment(comment, board)
    match res:
        case str() as move:
            return f"I found the move suggestion {move} in your comment."
        case InvalidMoveError():
            return "I did not find a valid move in your comment."
        case (str() as move, AmbiguousMoveError()):
            return f"The move {move} is ambiguous."
        case (str() as move, IllegalMoveError()):
            return f"The move {move} is illegal."
        case _:
            assert_never(res)


async def play_move(
    reddit: Reddit, board: Board, post: Submission
) -> Submission | None:
    move = await select_move(board, post)
    logging.info(f"Playing move {move}")
    match move:
        case None:
            return None
        case str():
            database.insert_move(move)
            board.push_san(move)
            if board.result() != "*":
                await make_post(reddit, board)
                database.insert_game()
                board.reset()
            return await make_post(reddit, board)
        case _:
            assert_never(move)


async def select_move(board: Board, post: Submission) -> str | None:
    top_score = 0
    selected = None
    await post.load()
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
) -> (
    str
    | InvalidMoveError
    | tuple[str, AmbiguousMoveError]
    | tuple[str, IllegalMoveError]
):
    candidates = comment.split()
    for candidate in candidates:
        try:
            board.parse_san(candidate)
        except chess.InvalidMoveError:
            continue
        except chess.AmbiguousMoveError as e:
            return (candidate, e)
        except chess.IllegalMoveError as e:
            return (candidate, e)
        return candidate
    return InvalidMoveError()


if __name__ == "__main__":
    main()
