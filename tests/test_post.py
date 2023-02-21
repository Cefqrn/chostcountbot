from src.post import Post, PostContent, PostStatus
import unittest


class TestPost(unittest.TestCase):
    def test_title(self):
        # empty
        self.assertEqual(Post(
            id=123,
            author="",
            content=PostContent(
                headline="",
                body="",
            ),
            status=PostStatus.draft
        ).title, "123-empty")

        # no clipping
        self.assertEqual(Post(
            id=123,
            author="",
            content=PostContent(
                headline="pineapple",
                body="",
            ),
            status=PostStatus.draft
        ).title, "123-pineapple")

        # clipping at 28 characters
        self.assertEqual(Post(
            id=123,
            author="",
            content=PostContent(
                headline="pineapple pizza is delicious",
                body="",
            ),
            status=PostStatus.draft
        ).title, "123-pineapple-pizza-is-delic")

        # ending with hyphen
        self.assertEqual(Post(
            id=12345678,
            author="",
            content=PostContent(
                headline="pineapple pizza is delicious",
                body="",
            ),
            status=PostStatus.draft
        ).title, "12345678-pineapple-pizza-is")

        # no headline
        self.assertEqual(Post(
            id=123,
            author="",
            content=PostContent(
                headline="",
                body="pineapple pizza is delicious",
            ),
            status=PostStatus.draft
        ).title, "123-pineapple-pizza-is-delic")

        # non-word characters
        self.assertEqual(Post(
            id=123,
            author="",
            content=PostContent(
                headline="",
                body="<p>pineapple pizza is delicious</p>",
            ),
            status=PostStatus.draft
        ).title, "123-p-pineapple-pizza-is-del")

        # capital letters
        self.assertEqual(Post(
            id=123,
            author="",
            content=PostContent(
                headline="Pineapple Pizza Is Delicious",
                body="",
            ),
            status=PostStatus.draft
        ).title, "123-pineapple-pizza-is-delic")


if __name__ == "__main__":
    unittest.main()
