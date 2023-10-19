from __future__ import annotations

from config import USER_AGENT, HOST

from urllib.request import Request, urlopen
from urllib.error import HTTPError
from dataclasses import dataclass, field
from enum import Enum
from json import dumps, load
from re import finditer

from typing import Optional

MAX_TITLE_LENGTH = 28


class CookieNotFoundError(Exception): ...

class PostError(Exception): ...
class ProjectNotFoundError(PostError): ...
class PostForbiddenError(PostError): ...
class PostDeletedError(PostError): ...


class PostStatus(Enum):
    """Status of a post."""
    draft   = 0
    public  = 1
    deleted = 2


@dataclass(frozen=True)
class PostContent:
    """Class representing the content of a post."""
    headline: str
    body: str
    adult_content: bool         = False
    tags: list[str]             = field(default_factory=list)
    content_warnings: list[str] = field(default_factory=list)

    def encode(self, status: PostStatus) -> bytes:
        """
        Convert the content into a `bytes` object.
        
        Used when sending requests to the api.
        """
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

    def post(self, cookie: str, project_name: str, status: PostStatus=PostStatus.public) -> Post:
        """
        Post the content under `project_name` with the status `status`.
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
                raise PostForbiddenError from e
            if e.code == 404:
                raise ProjectNotFoundError from e

            raise PostError from e
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
        """Last element in the link to the post."""
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
        cookie: str,
        new_content: Optional[PostContent]=None,
        new_status: Optional[PostStatus]=None
    ) -> None:
        """
        Modify the content and/or the status of the post.
        
        If `new_content` is `None`, the post keeps its current content.

        If `new_status` is `None`, the post keeps its current status.
        """
        if self.status is PostStatus.deleted:
            raise PostDeletedError("can't edit deleted post")

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
                raise PostForbiddenError from e
            
            raise PostError from e
        else:
            self.content = new_content
            self.status = new_status

    def delete(self, cookie: str) -> None:
        """Delete the post."""
        if self.status is PostStatus.deleted:
            raise PostDeletedError("post already deleted")

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
                raise PostForbiddenError from e

            raise PostError from e
        else:
            self.status = PostStatus.deleted
