from enum import Enum, auto
from .moves import (
    MoveErrorAmbiguous,
    MoveErrorIllegal,
    MoveNormal,
    MoveResign,
    move_for_comment,
)

from . import database
from .database import NoRowsException, Outcome

from asyncpraw import Reddit
from asyncpraw.objector import datetime
from asyncpraw.reddit import Submission
from asyncpraw.models import Comment

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
from asyncio import Queue
from typing import NamedTuple, assert_never
from datetime import timedelta


class Player(Enum):
    WHITE = auto()
    BLACK = auto()

    def __str__(self):
        match self:
            case Player.WHITE:
                return "white"
            case Player.BLACK:
                return "black"
            case _:
                assert_never(self)


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
        utc = datetime.utcnow()
        today = datetime.combine(utc.date(), datetime.min.time())
        seconds_per_post = 24 * 60 * 60 / self.posts_per_day
        seconds_today = (utc - today).total_seconds()
        elapsed_posts = seconds_today / seconds_per_post
        next_post = elapsed_posts.__ceil__() * seconds_per_post
        next_post_time = today + timedelta(seconds=next_post)
        return (next_post_time - utc).total_seconds()


Schedule = ScheduleTimeout | ScheduleUtc


def main() -> None:
    parser = argparse.ArgumentParser(prog="CommunityChess Server")
    parser.add_argument(
        "-l",
        "--log",
        choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
        default="WARN",
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
    args = parser.parse_args()
    logging.basicConfig(level=args.log)

    database.prepare()
    try:
        database.current_game()
    except NoRowsException:
        database.insert_game()

    schedule: Schedule = ScheduleUtc(args.utc)
    if args.timeout:
        schedule = ScheduleTimeout(args.timeout)

    logging.info("About to run async_main")
    asyncio.run(async_main(schedule))


async def async_main(schedule: Schedule) -> None:
    logging.info("Entering async_main")
    reddit = Reddit()
    queue: MsgQueue = Queue()

    tasks = [
        asyncio.create_task(send_play_move_notifications(queue, schedule)),
        asyncio.create_task(forward_comments(reddit, queue)),
        asyncio.create_task(handle_messages(reddit, queue)),
    ]
    for task in tasks:
        await task


async def handle_messages(reddit: Reddit, queue: MsgQueue) -> None:
    logging.info("entered handle_messages")

    board = Board()
    for move in database.moves():
        board.push(move.move)

    try:
        logging.info("Checking for last post existence")
        database.last_post()
    except NoRowsException:
        logging.info("Making initial post")
        await make_post(reddit, board, Outcome.ONGOING)

    current_post = await reddit.submission(database.last_post())
    logging.info("Entering message queue loop")
    while True:
        msg = await queue.get()
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
    sub = await reddit.subreddit("CommunityChess")
    async for comment in sub.stream.comments(skip_existing=True):
        TOP_LEVEL_COMMENT_PREFIX = "t3_"
        is_top_level = comment.parent_id[:3] == TOP_LEVEL_COMMENT_PREFIX
        is_current_post = comment.parent_id[3:] == database.last_post()
        if is_top_level and is_current_post and not comment.is_submitter:
            logging.info("Sending comment")
            await queue.put(comment)


async def send_play_move_notifications(queue: MsgQueue, schedule: Schedule) -> None:
    logging.info("entered send_play_move_notifications")
    while True:
        seconds = schedule.next_post_seconds()
        logging.info(f"Next post scheduled in {seconds} seconds")
        await asyncio.sleep(seconds)
        logging.info("Sending play move notification")
        await queue.put(NotifyPlayMove())


def reply_for_comment(comment: str, board: Board) -> str:
    res = move_for_comment(comment, board)
    match res:
        case MoveNormal(move, draw_offer):
            if draw_offer:
                return f"I found the move {move} in your comment."
            else:
                return f"I found the move {move} with a draw offer in your comment."
        case MoveResign():
            return "I found the suggestion to resign in your comment."
        case None:
            return "I did not find a valid move in your comment. Make sure to put valid SAN or UCI notation in the first line to suggest a move."
        case MoveErrorAmbiguous():
            return f"The move {res.move_text} is ambiguous."
        case MoveErrorIllegal():
            return f"The move {res.move_text} is illegal."
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
        case MoveNormal():
            database.insert_move(move)
            board.push(move.move)
            outcome = outcome_for_move(move, board)
            match outcome:
                case Outcome.ONGOING:
                    pass
                case _:
                    await new_game(reddit, board, outcome)
        case MoveResign():
            await new_game(reddit, board, resignation_for_board(board))
        case _:
            assert_never(move)
    return await make_post(reddit, board, Outcome.ONGOING)


def resignation_for_board(board: Board) -> Outcome:
    player = to_play(board.ply())
    match player:
        case Player.WHITE:
            return Outcome.RESIGNATION_WHITE
        case Player.BLACK:
            return Outcome.RESIGNATION_BLACK
        case _:
            assert_never(player)


async def new_game(reddit: Reddit, board: Board, outcome: Outcome):
    await make_post(reddit, board, outcome)
    database.set_game_outcome(outcome)
    database.insert_game()
    board.reset()


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
                        case _:
                            assert_never(outcome.winner)
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
                case _:
                    assert_never(outcome.termination)


async def select_move(board: Board, post: Submission) -> MoveNormal | MoveResign | None:
    top_score = 0
    selected = None
    await post.load()
    for comment in post.comments:
        if comment.score > top_score:
            move = move_for_comment(comment.body, board)
            match move:
                case MoveNormal() | MoveResign():
                    selected = move
                    top_score = comment.score
                case None | MoveErrorAmbiguous() | MoveErrorIllegal():
                    pass
                case _:
                    assert_never(move)
    return selected


async def make_post(reddit: Reddit, board: Board, outcome: Outcome) -> Submission:
    _, path = tempfile.mkstemp(".png")
    svg = chess.svg.board(board, size=1024)
    cairosvg.svg2png(svg, write_to=path)

    title = title_for_outcome(outcome, board.ply())
    sub = await reddit.subreddit("CommunityChess")
    post = await sub.submit_image(title, path)
    os.remove(path)
    await post.reply(f"PGN:\n{board_pgn(board)}\n\nFEN:\n\n{board.fen()}")

    database.insert_post(post.id, database.current_game())
    return post


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
