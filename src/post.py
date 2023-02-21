from __future__ import annotations

from urllib.request import Request, urlopen
from urllib.error import HTTPError
from dataclasses import dataclass, field
from enum import Enum
from json import dumps, load
from re import finditer
from os import environ

from typing import Optional

USER_AGENT = "chostcountbot ( contact: cefqrn@gmail.com )"
HOST = "https://cohost.org"

MAX_TITLE_LENGTH = 28


class PostStatus(Enum):
    """Status of a post."""

    draft   = 0
    public  = 1
    deleted = 2


class PostForbiddenError(Exception): ...
class PostDeletedError(Exception): ...
class ProjectNotFoundError(Exception): ...
class CookieNotFoundError(Exception): ...


try:
    cookie = environ["CHOSTCOUNTBOT_COHOST_COOKIE"]
except KeyError:
    raise CookieNotFoundError(
        "CHOSTCOUNTBOT_COHOST_COOKIE environment variable not set."
    )


@dataclass(frozen=True)
class PostContent:
    """Class representing the content of a post."""

    headline: str
    body: str
    adult_content: bool         = False
    tags: list[str]             = field(default_factory=list)
    content_warnings: list[str] = field(default_factory=list)

    def encode(self, status: PostStatus) -> bytes:
        if status is PostStatus.deleted:
            raise ValueError("Can't encode a post with deleted status")

        # if the headline is empty there needs to be at least one block
        blocks = [
            {
                "type": "markdown",
                "markdown": {"content": block}
            } for block in self.body.split("\n\n")
        ] if self.body or not self.headline else []

        return dumps({
            "postState": status.value,
            "headline": self.headline,
            "adultContent": self.adult_content,
            "blocks": blocks,
            "cws": self.content_warnings,
            "tags": self.tags
        }, separators=(",", ":")).encode()

    def post(self, project_name: str, status: PostStatus=PostStatus.public) -> Post:
        """
        Posts the content under `project_name` with the status `status`.

        Returns a `Post` object.
        """

        try:
            with urlopen(
                Request(
                    url=f"{HOST}/api/v1/project/{project_name}/posts",
                    data=self.encode(status),
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": USER_AGENT,
                        "Cookie": cookie
                    },
                    method="POST"
                )
            ) as f:
                post_id = load(f)["postId"]
        except HTTPError as e:
            if e.code == 403:
                raise PostForbiddenError
            if e.code == 404:
                raise ProjectNotFoundError

            # let the HTTPError crash the program if even we don't know what it is
            raise e
        else:
            return Post(
                id=post_id,
                author=project_name,
                content=self,
                status=status
            )


@dataclass
class Post:
    """
    Class representing a post on cohost.
    Should only be created using `PostContent.post`.
    """

    id: int
    author: str
    content: PostContent
    status: PostStatus
    
    @property
    def title(self):
        """Last element in the link to the post. Also used as a filename."""

        title = str(self.id)

        title_content = self.content.headline or self.content.body or "empty"
        for word in finditer(r"\w+", title_content):
            remaining_length = MAX_TITLE_LENGTH - len(title)

            # don't end on a hyphen
            if remaining_length <= 1:
                break

            title += "-" + word.group()[:remaining_length - 1].lower()
            
        return title
    
    @property
    def link(self):
        """The Legend of Eggbug: A Link to the Post."""

        return f"{HOST}/{self.author}/post/{self.title}"

    def edit(
        self,
        new_content: Optional[PostContent]=None,
        new_status: Optional[PostStatus]=None
    ) -> None:
        """
        Replace the content of the post with `new_content`
        and set its status to `new_status`.
        
        If `new_content` is `None`, the post keeps its current content.

        If `new_status` is `None`, the post keeps its current status.
        """
        
        if self.status is PostStatus.deleted:
            raise PostDeletedError("Can't edit deleted post")
        
        if new_status is PostStatus.deleted:
            raise ValueError(
                "Can't change status to deleted (Use Post.delete to delete a post)"
            )

        if new_content is None:
            new_content = self.content

        if new_status is None:
            new_status = self.status

        try:
            with urlopen(Request(
                    url=f"{HOST}/api/v1/project/{self.author}/posts/{self.id}",
                    data=new_content.encode(new_status),
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": USER_AGENT,
                        "Cookie": cookie
                    },
                    method="PUT")):
                pass
        except HTTPError as e:
            if e.code == 403:
                raise PostForbiddenError
            
            raise e
        else:
            self.content = new_content
            self.status = new_status

    def delete(self) -> None:
        """Delete the post."""

        if self.status is PostStatus.deleted:
            raise PostDeletedError("Post already deleted")

        try:
            with urlopen(
                Request(
                    url=f"{HOST}/api/v1/project/{self.author}/posts/{self.id}",
                    headers={
                        "User-Agent": USER_AGENT,
                        "Cookie": cookie
                    },
                    method="DELETE"
                )
            ):
                pass
        except HTTPError as e:
            if e.code == 403:
                raise PostForbiddenError

            raise e
        else:
            self.status = PostStatus.deleted
