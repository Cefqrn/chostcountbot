from config import PROJECT_NAME, ID_FILENAME, CREDENTIALS_FILENAME
from notify import ping, set_webhook
from login import login
from post import Post, PostStatus, PostContent

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from json import load
from time import sleep

import logging

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

        yield None
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


def main() -> None:
    # log in
    with log_action(
        start_message="logging in",
        fail_message="failed to log in",
        success_message="logged in successfully"
    ):
        with open(CREDENTIALS_FILE_PATH) as f:
            credentials = load(f)

        login(credentials["email"], credentials["password"])

    # wait till midnight to post
    # (the script should be run before midnight e.g. 23:59)
    tomorrow = (
        (datetime.now(timezone.utc) + timedelta(hours=23))
        .replace(hour=0, minute=0, second=0, microsecond=0)
    )
    delay = (tomorrow - datetime.now(timezone.utc)).total_seconds()

    logging.info(f"waiting {delay} seconds before posting")
    sleep(delay)

    # make a post to get the latest id
    with log_action(
        start_message="posting",
        success_message="posted successfully"
    ):
        current_post: Post = PostContent(
            headline="",
            body=""
        ).post(PROJECT_NAME, status=PostStatus.draft)

    logging.info(f"post id: {current_post.id}")

    # get the ids of previous posts
    ID_FILE_PATH.touch()
    with ID_FILE_PATH.open("r+") as f:
        lines = tuple(tuple(map(int, line.split())) for line in f.readlines())

        previous_post_id = lines[-1][0] if lines else 0

        last_week_post_id, last_week_bot_post_id = lines[-7] if len(lines) >= 7 else (0, 0)
        last_week_previous_post_id = lines[-8][0] if len(lines) >= 8 else 0

        # append the current post id to the end of the file
        # 1st is the id of the last post of the day / first post of the next day
        # 2nd is the id of the bot's post (makes manual days easier)
        print(current_post.id, current_post.id, file=f)

    post_count = current_post.id - previous_post_id

    last_week_post_count = last_week_post_id - last_week_previous_post_id
    last_week_post_count_ratio = (post_count - last_week_post_count) / (last_week_post_count or 1)

    week_average_post_count = (previous_post_id - last_week_previous_post_id) / 7
    week_average_post_count_ratio = (post_count - week_average_post_count) / (week_average_post_count or 1)

    # add delay to get the correct date
    curr_date = datetime.now(timezone.utc) - timedelta(hours=1)

    # edit the post to put in the information
    with log_action(
        start_message="editing post",
        success_message="edited post successfully",
        fail_message="could not edit post"
    ):
        current_post.edit(
            PostContent(
                headline=curr_date.strftime("%Y-%m-%d"),
                body=f"there have been {post_count} posts today\n\nthat's {abs(last_week_post_count_ratio):.2%} {'more' if last_week_post_count_ratio >= 0 else 'less'} than [last week's count](/{PROJECT_NAME}/post/{last_week_bot_post_id}-{(curr_date - timedelta(days=7)).strftime('%Y-%m-%d')}) and {abs(week_average_post_count_ratio):.2%} {'more' if week_average_post_count_ratio >= 0 else 'less'} than the past week's average, {week_average_post_count:.2f}",
            ),
            new_status=PostStatus.public
        )

    logging.info(current_post.link)

    with log_action(
        start_message="pushing to webhook",
        success_message="pushed successfully",
        fail_message="could not push to webhook",
        bubble_exception=False
    ):
        set_webhook(credentials["webhook"])
        ping(current_post.link)


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
        fail_message="encountered an error",
        bubble_exception=False
    ):
        main()
