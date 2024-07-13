from config import PROJECT_NAME, ID_FILENAME, CREDENTIALS_FILENAME, DELAY_OVERRIDE

from chostcountbot import Day, get_final_post_content
from notify import ping
from login import login
from post import PostContent, PostStatus

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from json import load
from time import sleep
import logging
import csv

from collections.abc import Generator
from typing import Optional

FOLDER_PATH = Path(__file__).parent
ID_FILE_PATH = FOLDER_PATH / ID_FILENAME
CREDENTIALS_FILE_PATH = FOLDER_PATH / CREDENTIALS_FILENAME


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


def create_post(cookie: str):
    # read in the data from previous days
    data = {}
    with (
        log_action(
            start_message="reading from database",
            fail_message="could not read from database"
        ),
        ID_FILE_PATH.open("r+", newline="") as f
    ):
        reader = csv.DictReader(f)
        for day in map(Day.from_dict, reader):
            data[day.date] = day

    # get the current date
    now = datetime.now(timezone.utc)
    current_date = now.date()

    # wait until midnight
    if DELAY_OVERRIDE is None:
        midnight = (now + timedelta(1)).replace(hour=0, minute=0, second=0, microsecond=0)
        time_to_tomorrow = (midnight - now).total_seconds()
    else:
        time_to_tomorrow = DELAY_OVERRIDE

    sleep(time_to_tomorrow)

    # make a post to get the latest id
    with log_action(
        start_message="posting initial post",
        fail_message="could not post"
    ):
        post = PostContent(
            headline="",
            body=""
        ).post(cookie, PROJECT_NAME, status=PostStatus.draft)

    today = Day(current_date, post.id, post.id)
    data[current_date] = today

    # add the new data to the database
    with (
        log_action(
            start_message="updating database",
            fail_message="could not update database"
        ),
        ID_FILE_PATH.open("a", newline="") as f
    ):
        writer = csv.DictWriter(f, fieldnames=Day._fields)
        writer.writerow(today.to_dict())

    # edit the post to put in the information
    with log_action(
        start_message="editing post",
        fail_message="could not edit post"
    ):
        post.edit(
            cookie,
            get_final_post_content(PROJECT_NAME, data, current_date),
            PostStatus.public
        )

    logging.info(post.link)

    return post


def main():
    with (
        log_action(
            start_message="logging in",
            success_message="logged in successfully",
            fail_message="couldn't log in"
        ),
        CREDENTIALS_FILE_PATH.open() as f
    ):
        credentials = load(f)
        cookie = login(credentials["email"], credentials["password"])

    post = None
    with log_action(
        start_message="posting",
        success_message="posted successfully",
        fail_message="couldn't post"
    ):
        post = create_post(cookie)

    with log_action(
        start_message="pushing to webhook",
        success_message="pushed successfully",
        fail_message="couldn't push to webhook",
        bubble_exception=False
    ):
        webhook = credentials["webhook"]

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
