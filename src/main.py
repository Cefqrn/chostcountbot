from config import PROJECT_NAME, ID_FILENAME, CREDENTIALS_FILENAME, DELAY_OVERRIDE
from notify import ping
from login import login
from post import Post, PostStatus, PostContent

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import NamedTuple
from json import load
from time import sleep

import logging

from collections.abc import Generator
from typing import Optional, TextIO

FOLDER_PATH = Path(__file__).parent
ID_FILE_PATH = FOLDER_PATH / ID_FILENAME
CREDENTIALS_FILE_PATH = FOLDER_PATH / CREDENTIALS_FILENAME


class DayPostIDs(NamedTuple):
    # last post of the day / first post of the next day.
    # used for finding the amount of posts posted
    last_post_ID: int
    # bot's post for that day
    # used for linking to previous days
    bot_post_ID: int


@contextmanager
def log_action(
    start_message: Optional[str]=None,
    success_message: Optional[str]=None,
    fail_message: Optional[str]=None,
    end_message: Optional[str]=None,
    bubble_exception: bool=True
) -> Generator[None, None, None]:
    try:
        if start_message is not None:
            logging.info(start_message)

        yield
    except Exception:
        if fail_message is not None:
            logging.exception(fail_message)

        if bubble_exception:
            raise
    else:
        if success_message is not None:
            logging.info(success_message)
    finally:
        if end_message is not None:
            logging.info(end_message)


def time_until_tomorrow() -> float:
    if DELAY_OVERRIDE is not None:
        return DELAY_OVERRIDE

    tomorrow = (
        (datetime.now(timezone.utc) + timedelta(hours=23))
        .replace(hour=0, minute=0, second=0, microsecond=0)
    )

    return (tomorrow - datetime.now(timezone.utc)).total_seconds()


def format_date(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


def get_final_post_content(id_file: TextIO, current_post_id: int, current_date: datetime) -> PostContent:
    with log_action(fail_message="couldn't get previous ids"):
        previous_ids = tuple(DayPostIDs(*map(int, line.split())) for line in id_file)

        previous_post_id = previous_ids[-1].last_post_ID if previous_ids else 0

        last_week_post_id, last_week_bot_post_id = previous_ids[-7] if len(previous_ids) >= 7 else (0, 0)
        last_week_previous_post_id = previous_ids[-8].last_post_ID if len(previous_ids) >= 8 else 0

        # append the current post ids to the end of the file
        print(current_post_id, current_post_id, file=id_file)

    post_count = current_post_id - previous_post_id

    last_week_post_count = last_week_post_id - last_week_previous_post_id
    last_week_post_count_ratio = (post_count - last_week_post_count) / (last_week_post_count or 1)

    week_average_post_count = (previous_post_id - last_week_previous_post_id) / 7
    week_average_post_count_ratio = (post_count - week_average_post_count) / (week_average_post_count or 1)

    return PostContent(
        headline=format_date(current_date),
        body=f"there have been {post_count} posts today\n\nthat's {abs(last_week_post_count_ratio):.2%} {'more' if last_week_post_count_ratio >= 0 else 'less'} than [last week's count](/{PROJECT_NAME}/post/{last_week_bot_post_id}-{format_date(current_date - timedelta(days=7))}) and {abs(week_average_post_count_ratio):.2%} {'more' if week_average_post_count_ratio >= 0 else 'less'} than the past week's average, {week_average_post_count:.2f}"
    )


def create_post(id_file: TextIO) -> Post:
    # get the current date
    current_date = datetime.now(timezone.utc)

    # wait until midnight
    delay = time_until_tomorrow()
    with log_action(f"waiting {delay} seconds before posting"):
        sleep(delay)

    # make a post to get the latest id
    with log_action(
        start_message="posting",
        success_message="posted successfully",
        fail_message="couldn't post"
    ):
        current_post: Post = PostContent(
            headline="",
            body=""
        ).post(PROJECT_NAME, status=PostStatus.draft)

    logging.info(f"post id: {current_post.id}")

    # edit the post to put in the information
    with log_action(
        start_message="editing post",
        success_message="edited post successfully",
        fail_message="couldn't edit post"
    ):
        current_post.edit(
            get_final_post_content(id_file, current_post.id, current_date),
            new_status=PostStatus.public
        )

    logging.info(current_post.link)

    return current_post


def main() -> None:
    with (
        log_action(
            start_message="logging in",
            fail_message="couldn't log in",
            success_message="logged in successfully"
        ),
        CREDENTIALS_FILE_PATH.open() as credentials_file
    ):
        credentials = load(credentials_file)
        login(credentials["email"], credentials["password"])

    webhook = None
    with log_action(fail_message="couldn't get webhook", bubble_exception=False):
        webhook = credentials["webhook"]

    post = None
    with (
        log_action(
            fail_message="couldn't post",
            bubble_exception=False
        ),
        ID_FILE_PATH.open("r+") as id_file
    ):
        post = create_post(id_file)

    with log_action(
        start_message="pushing to webhook",
        success_message="pushed successfully",
        fail_message="couldn't push to webhook",
        bubble_exception=False
    ):
        if post is None:
            id_b = "897120769".lower()
            id_a = "397120199".capitalize()
            ping(f"<@{id_a}{id_b}> failed to post", webhook)
        else:
            ping(post.link, webhook)


if __name__ == "__main__":
    from time import gmtime

    logging.basicConfig(
        format="{asctime},{msecs:0<3.0f}Z {levelname} {message}",
        datefmt="%Y-%m-%dT%H:%M:%S",
        style="{",
        filename="log.log",
        level=logging.INFO
    )
    logging.Formatter.converter = gmtime

    with log_action(
        start_message="starting",
        success_message="ended successfully",
        fail_message="encountered an error"
    ):
        main()
