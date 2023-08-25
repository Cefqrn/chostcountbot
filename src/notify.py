from urllib.request import Request, urlopen
from functools import cache
from json import dumps
from os import environ

USER_AGENT = "chostcountbot ( contact: cefqrn@gmail.com )"


class WebhookNotFoundError(Exception): ...


def ping(message: str):
    with urlopen(
        Request(
            url=fetch_webhook(),
            data=dumps({"content": message}, separators=(",", ":")).encode(),
            headers={
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT
            },
            method="POST"
        )
    ):
        pass


@cache
def fetch_webhook() -> str:
    try:
        return environ["CHOSTCOUNTBOT_DISCORD_WEBHOOK"]
    except KeyError:
        raise WebhookNotFoundError(
            "CHOSTCOUNTBOT_DISCORD_WEBHOOK environment variable not set."
        )
