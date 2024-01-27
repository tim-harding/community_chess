from typing import NamedTuple
from datetime import timedelta, datetime, UTC


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
