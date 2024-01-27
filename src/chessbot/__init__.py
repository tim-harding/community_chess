from enum import IntEnum, auto
from .moves import (
    MoveError,
    MoveNormal,
    MoveResign,
    move_for_comment,
)

from . import database
from .database import NoInitialPostException, Outcome

from asyncpraw.reddit import Reddit
from asyncpraw.models.reddit.subreddit import Subreddit
from asyncpraw.models.reddit.submission import Submission
from asyncpraw.models.reddit.comment import Comment

import chess
from chess import (
    Board,
    Termination,
)
import chess.svg
import chess.pgn

import argparse
import os
import tempfile
import asyncio
import cairosvg
import logging
from asyncio import CancelledError, Queue
from typing import NamedTuple, assert_never
from datetime import timedelta, datetime, UTC


class Player(IntEnum):
    WHITE = auto()
    BLACK = auto()

    def __str__(self) -> str:
        match self:
            case Player.WHITE:
                return "white"
            case Player.BLACK:
                return "black"


class NotifyPlayMove:
    pass


MsgQueue = Queue[Comment | NotifyPlayMove]


class ScheduleTimeout(NamedTuple):
    seconds: int

    def next_post_seconds(self) -> float:
        return self.seconds


class ScheduleUtc(NamedTuple):
    posts_per_day: int

    def next_post_seconds(self) -> float:
        utc = datetime.now(UTC)
        today = datetime.combine(utc.date(), datetime.min.time(), UTC)
        seconds_per_post = 24 * 60 * 60 / self.posts_per_day
        seconds_today = (utc - today).total_seconds()
        elapsed_posts = seconds_today / seconds_per_post
        next_post = elapsed_posts.__ceil__() * seconds_per_post
        next_post_time = today + timedelta(seconds=next_post)
        return (next_post_time - utc).total_seconds()


Schedule = ScheduleTimeout | ScheduleUtc


class AuthMethod(IntEnum):
    PRAW = auto()
    ENV = auto()


class MakePostException(Exception):
    def __init__(self) -> None:
        super().__init__("Failed to make a post")


def main() -> None:
    parser = argparse.ArgumentParser(prog="CommunityChess Server")

    parser.add_argument(
        "-l",
        "--log",
        type=str,
        choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
        default="WARN",
        metavar="LEVEL",
        help="Sets the logging verbosity level",
    )

    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        metavar="SECONDS",
        help="Attempt to make a move every SECONDS",
    )

    parser.add_argument(
        "-u",
        "--utc",
        type=int,
        default=2,
        metavar="TIMES",
        help="Attempt to make a move TIMES per day, starting from UTC 00:00",
    )

    parser.add_argument(
        "-d",
        "--database",
        type=str,
        default="communitychess.db",
        metavar="PATH",
        help="The file to use for the sqlite database",
    )

    parser.add_argument(
        "-a",
        "--auth-method",
        type=str,
        choices=["praw", "env"],
        default="praw",
        metavar="METHOD",
        help="Whether to use praw.ini or environment variables for Reddit authentication",
    )

    parser.add_argument(
        "-s",
        "--subreddit",
        type=str,
        metavar="NAME",
        help="The subreddit to make posts in",
    )

    args = parser.parse_args()
    logging.basicConfig(level=args.log)

    schedule: Schedule = ScheduleUtc(args.utc)
    if args.timeout:
        schedule = ScheduleTimeout(args.timeout)

    match args.auth_method:
        case "praw":
            auth_method = AuthMethod.PRAW
        case "env":
            auth_method = AuthMethod.ENV
        case _:
            raise Exception("Invalid auth method")

    logging.info("About to run async_main")
    asyncio.run(async_main(schedule, auth_method, args.subreddit, args.database))


async def async_main(
    schedule: Schedule, auth_method: AuthMethod, subreddit_name: str, database_name: str
) -> None:
    logging.info("Entering async_main")

    match auth_method:
        case AuthMethod.PRAW:
            reddit = Reddit()
        case AuthMethod.ENV:
            reddit = Reddit(
                client_id=os.environ["CLIENT_ID"],
                client_secret=os.environ["CLIENT_SECRET"],
                refresh_token=os.environ["REFRESH_TOKEN"],
                user_agent=os.environ["USER_AGENT"],
            )

    try:
        subreddit = await reddit.subreddit(subreddit_name)
    except CancelledError:
        logging.info("Cancelling forward_comments")
        return

    queue: MsgQueue = Queue()
    tasks = []
    try:
        async with asyncio.TaskGroup() as group:
            tasks = [
                group.create_task(send_play_move_notifications(queue, schedule)),
                group.create_task(forward_comments(subreddit, queue)),
                group.create_task(
                    handle_messages(reddit, subreddit, database_name, queue)
                ),
            ]
    except CancelledError:
        for task in tasks:
            task.cancel()
        await reddit.close()


async def handle_messages(
    reddit: Reddit, subreddit: Subreddit, database_name: str, queue: MsgQueue
) -> None:
    logging.info("Entered handle_messages")
    board = Board()

    try:
        database.open(database_name)
    except NoInitialPostException:
        await make_post(subreddit, board, Outcome.ONGOING)

    for move in database.moves():
        board.push(move.move)

    while True:
        try:
            msg = await queue.get()
        except CancelledError:
            break

        match msg:
            case NotifyPlayMove():
                try:
                    await play_move(reddit, subreddit, board)
                except CancelledError:
                    break

            case Comment() as comment:
                reply = reply_for_comment(comment.body, board)
                try:
                    await comment.reply(reply)
                except CancelledError:
                    break
                logging.info(f"Responded to comment '{comment.body}' with '{reply}'")


async def forward_comments(subreddit: Subreddit, queue: MsgQueue) -> None:
    logging.info("Entered forward_comments")
    async for comment in subreddit.stream.comments(skip_existing=True):
        TOP_LEVEL_COMMENT_PREFIX = "t3_"
        is_top_level = comment.parent_id[:3] == TOP_LEVEL_COMMENT_PREFIX
        if is_top_level and not comment.is_submitter:
            logging.info("Sending comment")
            try:
                await queue.put(comment)
            except CancelledError:
                break


async def send_play_move_notifications(queue: MsgQueue, schedule: Schedule) -> None:
    logging.info("Entered send_play_move_notifications")
    while True:
        seconds = schedule.next_post_seconds()
        logging.info(f"Next post scheduled in {seconds} seconds")
        try:
            await asyncio.sleep(seconds)
        except CancelledError:
            logging.info("Cancelling send_play_move_notifications")
            break

        logging.info("Sending play move notification")
        try:
            await queue.put(NotifyPlayMove())
        except CancelledError:
            logging.info("Cancelling send_play_move_notifications")
            break


def reply_for_comment(comment: str, board: Board) -> str:
    res = move_for_comment(comment, board)
    match res:
        case MoveNormal(move, draw_offer):
            if draw_offer:
                return f"I found the move {move} with a draw offer in your comment."
            else:
                return f"I found the move {move} in your comment."
        case MoveResign():
            return "I found the suggestion to resign in your comment."
        case None:
            return "I did not find a valid move in your comment. Make sure to put valid SAN or UCI notation in the first line to suggest a move."
        case MoveError():
            return f"The move {res.move_text} is {res.kind}."


async def play_move(reddit: Reddit, subreddit: Subreddit, board: Board) -> None:
    last_post = reddit.submission(database.last_post_for_game())
    assert isinstance(last_post, Submission)
    move = await select_move(board, last_post)
    logging.info(f"Playing move {move}")
    match move:
        case None:
            return None

        case MoveNormal():
            board.push(move.move)
            outcome = outcome_for_move(move, board)
            match outcome:
                case Outcome.ONGOING:
                    try:
                        next_post = await make_post(subreddit, board, Outcome.ONGOING)
                    except MakePostException:
                        logging.error(f"Failed to make post for move {move}")
                        board.pop()
                        return

                    database.insert_post(next_post.id)

                case (
                    Outcome.DRAW
                    | Outcome.STALEMATE
                    | Outcome.VICTORY_WHITE
                    | Outcome.VICTORY_BLACK
                ):
                    try:
                        await new_game(subreddit, board, outcome)
                    except MakePostException:
                        logging.error(f"Failed to make post for move {move}")
                        board.pop()
                        return

                    board.reset()

                case Outcome.RESIGNATION_WHITE | Outcome.RESIGNATION_BLACK:
                    raise Exception("Unreachable")

        case MoveResign():
            try:
                await new_game(subreddit, board, resignation_for_board(board))
            except MakePostException:
                logging.error(f"Failed to make post for move {move}")


def resignation_for_board(board: Board) -> Outcome:
    player = to_play(board.ply())
    match player:
        case Player.WHITE:
            return Outcome.RESIGNATION_WHITE
        case Player.BLACK:
            return Outcome.RESIGNATION_BLACK


async def new_game(subreddit: Subreddit, board: Board, outcome: Outcome) -> None:
    final_post = await make_post(subreddit, board, outcome)
    first_post = await make_post(subreddit, Board(), Outcome.ONGOING)
    database.new_game(final_post.id, outcome, first_post.id)


def outcome_for_move(move: MoveNormal, board: Board) -> Outcome:
    moves = database.moves()
    if len(moves) > 0 and moves[-1].offer_draw and move.offer_draw:
        return Outcome.DRAW
    else:
        return outcome_for_board(board)


def outcome_for_board(board: Board) -> Outcome:
    outcome = board.outcome(claim_draw=True)
    match outcome:
        case None:
            return Outcome.ONGOING
        case _:
            match outcome.termination:
                case Termination.CHECKMATE:
                    match outcome.winner:
                        case True:
                            return Outcome.VICTORY_WHITE
                        case False:
                            return Outcome.VICTORY_BLACK
                        case None:
                            raise Exception("Expected a winner")
                case Termination.STALEMATE:
                    return Outcome.STALEMATE
                case (
                    Termination.INSUFFICIENT_MATERIAL
                    | Termination.SEVENTYFIVE_MOVES
                    | Termination.FIVEFOLD_REPETITION
                    | Termination.FIFTY_MOVES
                    | Termination.THREEFOLD_REPETITION
                ):
                    return Outcome.DRAW
                case (
                    Termination.VARIANT_WIN
                    | Termination.VARIANT_LOSS
                    | Termination.VARIANT_DRAW
                ):
                    raise Exception("Unexpected variant termination")


async def select_move(board: Board, post: Submission) -> MoveNormal | MoveResign | None:
    top_score = 0
    selected = None
    await post.load()  # type: ignore
    async for comment in post.comments:
        if comment.score <= top_score:
            continue
        move = move_for_comment(comment.body, board)
        match move:
            case MoveNormal() | MoveResign():
                selected = move
                top_score = comment.score
            case None | MoveError():
                pass
    return selected


async def make_post(subreddit: Subreddit, board: Board, outcome: Outcome) -> Submission:
    _, path = tempfile.mkstemp(".png")
    svg = chess.svg.board(board, size=1024)
    cairosvg.svg2png(svg, write_to=path)

    title = title_for_outcome(outcome, board.ply())
    post = await subreddit.submit_image(title, path)
    os.remove(path)
    match post:
        case Submission():
            comment = await post.reply(
                f"PGN:\n\n{board_pgn(board)}\n\nFEN:\n\n{board.fen()}"
            )

            match comment:
                case Comment():
                    await comment.mod.distinguish(sticky=True)
                case _:
                    pass

            return post

        case None:
            raise MakePostException()

        case _:
            assert_never(post)


def title_for_outcome(outcome: Outcome, half_moves: int) -> str:
    match outcome:
        case Outcome.ONGOING:
            return f"Move {move_number(half_moves)}, {to_play(half_moves)} to play"
        case Outcome.VICTORY_WHITE:
            return "White checkmate"
        case Outcome.VICTORY_BLACK:
            return "Black checkmate"
        case Outcome.STALEMATE:
            return "Stalemate"
        case Outcome.DRAW:
            return "Draw"
        case Outcome.RESIGNATION_WHITE:
            return "White resigns"
        case Outcome.RESIGNATION_BLACK:
            return "Black resigns"


def board_pgn(board: Board) -> str:
    game = chess.pgn.Game()
    node = game.root()
    for move in board.move_stack:
        node = node.add_main_variation(move)
    printer = chess.pgn.StringExporter(headers=False, variations=False, comments=False)
    pgn = game.accept(printer)
    match pgn:
        case str():
            return pgn
        case _:
            raise Exception("Expected a string")


def move_number(half_moves: int) -> int:
    return half_moves // 2 + 1


def to_play(half_moves: int) -> Player:
    return Player.WHITE if half_moves % 2 == 0 else Player.BLACK


if __name__ == "__main__":
    main()
