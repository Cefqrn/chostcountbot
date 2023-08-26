from notify import ping, set_webhook
from login import login
from post import Post, PostStatus, PostContent

from datetime import datetime, timedelta, timezone
from pathlib import Path
from json import load

import logging

PROJECT_NAME = "chostcount"

FOLDER_PATH = Path(__file__).parent
ID_FILE_PATH = FOLDER_PATH / "ids.txt"
CREDENTIALS_FILE_PATH = FOLDER_PATH / "credentials.json"


def main() -> int:
    with open(CREDENTIALS_FILE_PATH) as f:
        credentials = load(f)

    # log in
    try:
        login(credentials["email"], credentials["password"])
    except KeyError:
        logging.fatal("missing credentials")
        return 1
    else:
        logging.info("logged in successfully")

    # make a post to get the latest id
    current_post: Post = PostContent(
        headline="",
        body=""
    ).post(PROJECT_NAME, status=PostStatus.draft)
    logging.info(f"posted successfully: id {current_post.id}")

    # make sure the file exists before opening it
    ID_FILE_PATH.touch()

    # get the id of previous posts
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
    last_week_post_count_ratio = (post_count - last_week_post_count) / last_week_post_count

    week_average_post_count = (previous_post_id - last_week_previous_post_id) / 7
    week_average_post_count_ratio = (post_count - week_average_post_count) / week_average_post_count

    # add delay to get the correct date
    curr_date = datetime.now(timezone.utc) - timedelta(hours=1)

    # edit the post to put in the information
    current_post.edit(
        PostContent(
            headline=curr_date.strftime("%Y-%m-%d"),
            body=f"there have been {post_count} posts today\n\nthat's {abs(last_week_post_count_ratio):.2%} {'more' if last_week_post_count_ratio >= 0 else 'less'} than [last week's count](/{PROJECT_NAME}/post/{last_week_bot_post_id}-{(curr_date - timedelta(days=7)).strftime('%Y-%m-%d')}) and {abs(week_average_post_count_ratio):.2%} {'more' if week_average_post_count_ratio >= 0 else 'less'} than the past week's average, {week_average_post_count:.2f}",
        ),
        new_status=PostStatus.public
    )
    logging.info("edited successfully")

    post_link = current_post.link
    logging.info(post_link)

    try:
        set_webhook(credentials["webhook"])
    except KeyError:
        logging.warn("could not fetch webhook")
    else:
        ping(post_link)

    return 0


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

    logging.info("started")
    try:
        exit_code = main()
    except Exception as e:
        logging.fatal(f"encountered an error ({type(e).__name__}): {e}")
        exit_code = 1
    else:
        logging.info("ended successfully")

    raise SystemExit(exit_code)
