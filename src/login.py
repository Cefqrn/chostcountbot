from __future__ import annotations

from config import USER_AGENT, HOST

from urllib.request import Request, urlopen
from urllib.parse import quote
from hashlib import pbkdf2_hmac
from base64 import b64encode, b64decode
from json import dumps, load

PBKDF_ITERATION_COUNT = 200_000
PBKDF_KEY_LENGTH = 128


def decode_salt(encoded_salt: bytes) -> bytes:
    unpadded_salt = encoded_salt.translate(bytes.maketrans(b"-_", b"AA"))
    padding = (-len(encoded_salt) % 4) * b"="

    return b64decode(unpadded_salt + padding)


def hash_password(password: bytes, salt: bytes) -> bytes:
    return b64encode(pbkdf2_hmac(
        hash_name="SHA384",
        password=password,
        salt=decode_salt(salt),
        iterations=PBKDF_ITERATION_COUNT,
        dklen=PBKDF_KEY_LENGTH
    ))


def login(email: str, password: str) -> str:
    # see https://cohost.org/iliana/post/180187-eggbug-rs-v0-1-3-d

    with urlopen(Request(
        f"{HOST}/api/v1/trpc/login.getSalt?batch=1&input=" \
            + quote(dumps({"0": {"email": email}}, separators=(',', ':'))),
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT
        }
    )) as f:
        salt: str = load(f)[0]["result"]["data"]["salt"]

    with urlopen(Request(
        url=f"{HOST}/api/v1/trpc/login.login?batch=1",
        data=dumps({"0": {
            "clientHash": hash_password(password.encode(), salt.encode()).decode(),
            "email": email
        }}, separators=(",", ":")).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST"
    )) as f:
        # ignore everything other than the sid
        cookie: str = next(filter(
            lambda s: s.startswith("connect.sid"),
            f.headers.get("set-cookie").split("; ")
        ))

    return cookie
