from chessbot.arguments import Arguments, AuthMethod
from chessbot.player import Player
from chessbot.schedule import Schedule
from .moves import (
    Move,
    MoveDraw,
    MoveError,
    MoveNormal,
    MoveResign,
    move_for_comment,
)
from chessbot.outcome import Outcome, for_move as outcome_for_move

from . import database
from .database import Database, NeedsInitialPost

from asyncpraw.reddit import Reddit
from asyncpraw.models.reddit.subreddit import Subreddit
from asyncpraw.models.reddit.submission import Submission
from asyncpraw.models.reddit.comment import Comment

import chess
from chess import Board
import chess.svg
import chess.pgn

import os
import tempfile
import asyncio
import cairosvg
import logging
from asyncio import CancelledError, Queue
from typing import assert_never


class NotifyPlayMove:
    pass


MsgQueue = Queue[Comment | NotifyPlayMove]


class MakePostException(Exception):
    def __init__(self) -> None:
        super().__init__("Failed to make a post")


def main() -> None:
    args = Arguments.parse()
    logging.basicConfig(level=str(args.log).upper())
    asyncio.run(async_main(args))


async def async_main(args: Arguments) -> None:
    logging.info("Entering async_main")

    match args.auth_method:
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
        subreddit = await reddit.subreddit(args.subreddit)
    except CancelledError:
        logging.info("Cancelling forward_comments")
        return

    queue: MsgQueue = Queue()
    tasks = []
    try:
        async with asyncio.TaskGroup() as group:
            tasks = [
                group.create_task(send_play_move_notifications(queue, args.schedule)),
                group.create_task(forward_comments(subreddit, queue)),
                group.create_task(handle_messages(reddit, subreddit, queue, args)),
            ]
    except CancelledError:
        for task in tasks:
            task.cancel()
        await reddit.close()


async def handle_messages(
    reddit: Reddit, subreddit: Subreddit, queue: MsgQueue, args: Arguments
) -> None:
    logging.info("Entered handle_messages")
    board = Board()

    try:
        database = await open_database(args, subreddit)
    except MakePostException:
        raise Exception("Failed to make initial post")

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
                    await play_move(reddit, subreddit, board, database)
                except CancelledError:
                    break

            case Comment() as comment:
                reply = reply_for_comment(
                    comment.body, board, was_draw_offered(database)
                )

                try:
                    await comment.reply(reply)
                except CancelledError:
                    break

                logging.info(f"Responded to comment '{comment.body}' with '{reply}'")


async def open_database(args: Arguments, subreddit: Subreddit) -> Database:
    opened = database.open(args.database, reset=args.reset)
    match opened:
        case Database() as db:
            return db
        case NeedsInitialPost(db):
            post = await make_post(subreddit, Board(), Outcome.ONGOING, False)
            db.insert_post(post.id)
            return db
        case _:
            assert_never(opened)


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
            break

        logging.info("Sending play move notification")
        try:
            await queue.put(NotifyPlayMove())
        except CancelledError:
            break


def reply_for_comment(comment: str, board: Board, has_draw_offer: bool) -> str:
    res = move_for_comment(comment, board)
    match res:
        case MoveNormal(move, draw_offer):
            if draw_offer:
                return f"I found the move {move} with a draw offer in your comment."
            else:
                return f"I found the move {move} in your comment."
        case MoveResign():
            return "I found the suggestion to resign in your comment."
        case MoveDraw():
            if has_draw_offer:
                return "I found the suggestion to accept a draw"
            else:
                return "Since the opponent hasn't offered a draw, I need you to also offer a move in case they don't accept."
        case None:
            return "I did not find a valid move in your comment. Make sure to put valid SAN or UCI notation in the first line to suggest a move."
        case MoveError():
            return f"The move {res.move_text} is {res.kind}."


async def play_move(
    reddit: Reddit, subreddit: Subreddit, board: Board, database: Database
) -> None:
    last_post = await reddit.submission(database.previous_post())
    assert isinstance(last_post, Submission)
    move = await select_move(board, last_post)
    logging.info(f"Playing move {move}")
    match move:
        case None:
            return None

        case MoveNormal():
            board.push(move.move)
            outcome = outcome_for_move(move, board, database.moves())
            match outcome:
                case Outcome.ONGOING:
                    try:
                        next_post = await make_post(
                            subreddit, board, Outcome.ONGOING, move.offer_draw
                        )
                    except MakePostException:
                        logging.error(f"Failed to make post for move {move}")
                        board.pop()
                        return

                    database.play_move(move, next_post.id)

                case (
                    Outcome.DRAW
                    | Outcome.STALEMATE
                    | Outcome.VICTORY_WHITE
                    | Outcome.VICTORY_BLACK
                ):
                    try:
                        await new_game(subreddit, board, outcome, database)
                    except MakePostException:
                        logging.error(f"Failed to make post for move {move}")
                        board.pop()
                        return

                    board.reset()

                case Outcome.RESIGNATION_WHITE | Outcome.RESIGNATION_BLACK:
                    raise Exception("Unreachable")

        case MoveDraw():
            try:
                await new_game(subreddit, board, Outcome.DRAW, database)
            except MakePostException:
                logging.error(f"Failed to make post for move {move}")
                return

            board.reset()

        case MoveResign():
            try:
                await new_game(
                    subreddit,
                    board,
                    Player.to_play(board.ply()).resignation(),
                    database,
                )
            except MakePostException:
                logging.error(f"Failed to make post for move {move}")


async def new_game(
    subreddit: Subreddit, board: Board, outcome: Outcome, database: Database
) -> None:
    final_post = await make_post(subreddit, board, outcome, False)
    first_post = await make_post(subreddit, Board(), Outcome.ONGOING, False)
    database.new_game(final_post.id, outcome, first_post.id)


async def select_move(board: Board, post: Submission) -> Move | None:
    top_score = 0
    selected = None
    async for comment in post.comments:
        if comment.score <= top_score or comment.is_submitter:
            continue
        move = move_for_comment(comment.body, board)
        match move:
            case MoveNormal() | MoveResign() | MoveDraw():
                selected = move
                top_score = comment.score
            case None | MoveError():
                pass
    return selected


async def make_post(
    subreddit: Subreddit, board: Board, outcome: Outcome, draw_offer: bool
) -> Submission:
    _, path = tempfile.mkstemp(".png")
    svg = chess.svg.board(board, size=1024)
    cairosvg.svg2png(svg, write_to=path)

    title = title_for_outcome(outcome, board.ply(), draw_offer)
    post = await subreddit.submit_image(title, path)
    os.remove(path)
    match post:
        case Submission():
            await post.reply(f"PGN:\n\n{board_pgn(board)}\n\nFEN:\n\n{board.fen()}")
            return post
        case None:
            raise MakePostException()
        case _:
            assert_never(post)


def title_for_outcome(outcome: Outcome, half_moves: int, is_draw_offered: bool) -> str:
    match outcome:
        case Outcome.ONGOING:
            to_play = Player.to_play(half_moves)
            draw_offer = (
                f", {to_play.opponent()} offers a draw" if is_draw_offered else ""
            )
            return f"Move {move_number(half_moves)}, {to_play} to play{draw_offer}"
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


def was_draw_offered(database: Database) -> bool:
    moves = database.moves()
    return len(moves) > 0 and moves[-1].offer_draw


if __name__ == "__main__":
    main()
