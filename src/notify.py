from config import USER_AGENT

from urllib.request import Request, urlopen
from json import dumps


class WebhookNotFoundError(Exception): ...


def ping(message: str, webhook: str):
    with urlopen(
        Request(
            url=webhook,
            data=dumps({"content": message}, separators=(",", ":")).encode(),
            headers={
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT
            },
            method="POST"
        )
    ):
        pass
