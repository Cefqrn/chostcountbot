from urllib.request import Request, urlopen
from json import dumps

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


webhook: str | None = None
def fetch_webhook() -> str:
    if webhook is None:
        raise WebhookNotFoundError
    
    return webhook


def set_webhook(new_webhook: str) -> None:
    global webhook
    webhook = new_webhook
