from notify import ping
from post import Post, PostStatus, PostContent

from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging

PROJECT_NAME = "chostcount"


def main() -> int:
    # make a post to get the latest id
    current_post: Post = PostContent(
        headline="",
        body=""
    ).post(PROJECT_NAME, status=PostStatus.draft)
    logging.info(f"Posted successfully: id {current_post.id}")

    # get the id of the previous post
    with open(Path(__file__).parent / "ids.txt", "r+") as f:
        lines = f.readlines()
        previous_post_id = int(lines[-1]) if lines else 0

        # append current post id to the end of the file
        print(current_post.id, file=f)

    # add delay to get the correct date
    curr_date = datetime.now(timezone.utc) - timedelta(hours=1)

    current_post.edit(
        PostContent(
            headline=curr_date.strftime("%Y-%m-%d"),
            body=f"There have been {current_post.id - previous_post_id} posts today",
        ),
        new_status=PostStatus.public
    )
    logging.info("Edited successfully")

    post_link = current_post.link
    logging.info(post_link)
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

    logging.info("Started")
    exit_code = main()
    logging.info("Ended successfully")

    raise SystemExit(exit_code)
