import argparse
from enum import StrEnum, auto
from typing import NamedTuple
from chessbot.schedule import Schedule, ScheduleTimeout, ScheduleUtc


class LogLevel(StrEnum):
    DEBUG = auto()
    INFO = auto()
    WARN = auto()
    ERROR = auto()
    CRITICAL = auto()


class AuthMethod(StrEnum):
    PRAW = auto()
    ENV = auto()


class Arguments(NamedTuple):
    log: LogLevel
    schedule: Schedule
    database: str
    auth_method: AuthMethod
    subreddit: str


def parse() -> Arguments:
    parser = argparse.ArgumentParser(prog="CommunityChess Server")

    parser.add_argument(
        "-l",
        "--log",
        type=str,
        choices=["debug", "info", "warn", "error", "critical"],
        default="warn",
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
        required=True,
        metavar="NAME",
        help="The subreddit to make posts in",
    )

    args = parser.parse_args()

    match (
        args.log,
        args.timeout,
        args.utc,
        args.database,
        args.auth_method,
        args.subreddit,
    ):
        case (
            str() as log,
            (int() | None) as timeout,
            (int() | None) as utc,
            str() as database,
            str() as auth_method,
            str() as subreddit,
        ):
            return Arguments(
                LogLevel(log),
                schedule(utc, timeout),
                database,
                AuthMethod(auth_method),
                subreddit,
            )
        case _:
            raise Exception("Invalid program arguments")


def schedule(utc: int | None, timeout: int | None) -> Schedule:
    match (utc, timeout):
        case (int() as utc, None):
            return ScheduleUtc(utc)
        case (None, int() as timeout):
            return ScheduleTimeout(timeout)
        case (int(), int()):
            print("Set --utc or --timeout but not both")
            exit(1)
        case (None, None):
            print("Set either --utc or --timeout")
            exit(1)
        case _:
            raise Exception("Unreachable")
