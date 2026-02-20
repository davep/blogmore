"""Unit tests for the search module."""

import datetime as dt
import json
from pathlib import Path

import pytest

from blogmore.parser import Post
from blogmore.search import build_search_index, strip_html, write_search_index


class TestStripHtml:
    """Tests for the strip_html helper."""

    def test_strips_simple_tag(self) -> None:
        """Plain tags are removed."""
        assert strip_html("<p>Hello</p>") == "Hello"

    def test_strips_nested_tags(self) -> None:
        """Nested tags are all removed."""
        assert strip_html("<div><p>Hello <em>world</em></p></div>") == "Hello world"

    def test_collapses_whitespace(self) -> None:
        """Multiple whitespace characters are collapsed to a single space."""
        assert strip_html("<p>Hello</p>   <p>world</p>") == "Hello world"

    def test_empty_string(self) -> None:
        """Empty input returns empty string."""
        assert strip_html("") == ""

    def test_no_tags(self) -> None:
        """Plain text is returned unchanged (modulo whitespace)."""
        assert strip_html("Hello world") == "Hello world"


class TestBuildSearchIndex:
    """Tests for build_search_index."""

    def _make_post(
        self,
        title: str = "Test",
        content: str = "content",
        html_content: str = "<p>content</p>",
        date: dt.datetime | None = None,
        slug: str = "test-post",
    ) -> Post:
        """Create a minimal Post for testing.

        Args:
            title: Post title.
            content: Raw markdown content.
            html_content: Rendered HTML content.
            date: Optional post date.
            slug: Used to form the post path.

        Returns:
            A Post instance.
        """
        return Post(
            path=Path(f"{slug}.md"),
            title=title,
            content=content,
            html_content=html_content,
            date=date,
            draft=False,
        )

    def test_empty_posts_returns_empty_list(self) -> None:
        """No posts produces an empty index."""
        assert build_search_index([]) == []

    def test_single_post_entry_keys(self) -> None:
        """Each index entry has title, url, date, and content keys."""
        post = self._make_post()
        index = build_search_index([post])
        assert len(index) == 1
        entry = index[0]
        assert set(entry.keys()) == {"title", "url", "date", "content"}

    def test_title_is_preserved(self) -> None:
        """Entry title matches the post title."""
        post = self._make_post(title="My Great Post")
        index = build_search_index([post])
        assert index[0]["title"] == "My Great Post"

    def test_content_has_no_html_tags(self) -> None:
        """Entry content is stripped of HTML tags."""
        post = self._make_post(html_content="<h2>Heading</h2><p>Body text</p>")
        index = build_search_index([post])
        assert "<" not in index[0]["content"]
        assert "Heading" in index[0]["content"]
        assert "Body text" in index[0]["content"]

    def test_date_formatted_as_iso_date(self) -> None:
        """Entry date is an ISO-formatted date string."""
        post = self._make_post(
            date=dt.datetime(2024, 3, 15, 10, 30, 0, tzinfo=dt.UTC)
        )
        index = build_search_index([post])
        assert index[0]["date"] == "2024-03-15"

    def test_post_without_date_has_empty_date(self) -> None:
        """Posts without a date get an empty date string."""
        post = self._make_post(date=None)
        index = build_search_index([post])
        assert index[0]["date"] == ""

    def test_url_matches_post_url(self) -> None:
        """Entry URL matches the post's .url property."""
        post = self._make_post(
            date=dt.datetime(2024, 1, 5, tzinfo=dt.UTC), slug="my-post"
        )
        index = build_search_index([post])
        assert index[0]["url"] == post.url

    def test_multiple_posts_all_indexed(self) -> None:
        """All posts appear in the index."""
        posts = [self._make_post(title=f"Post {i}", slug=f"post-{i}") for i in range(5)]
        index = build_search_index(posts)
        assert len(index) == 5
        titles = [entry["title"] for entry in index]
        for i in range(5):
            assert f"Post {i}" in titles


class TestWriteSearchIndex:
    """Tests for write_search_index."""

    def test_creates_search_index_file(self, tmp_path: Path) -> None:
        """search_index.json is created in the output directory."""
        post = Post(
            path=Path("test.md"),
            title="Hello",
            content="Hello world",
            html_content="<p>Hello world</p>",
            draft=False,
        )
        write_search_index([post], tmp_path)
        assert (tmp_path / "search_index.json").exists()

    def test_file_is_valid_json(self, tmp_path: Path) -> None:
        """The created file is valid JSON."""
        write_search_index([], tmp_path)
        data = json.loads((tmp_path / "search_index.json").read_text())
        assert isinstance(data, list)

    def test_file_contains_post_data(self, tmp_path: Path) -> None:
        """The JSON file contains the expected post data."""
        post = Post(
            path=Path("post.md"),
            title="My Post",
            content="Some content",
            html_content="<p>Some content</p>",
            date=dt.datetime(2024, 6, 1, tzinfo=dt.UTC),
            draft=False,
        )
        write_search_index([post], tmp_path)
        data = json.loads((tmp_path / "search_index.json").read_text())
        assert len(data) == 1
        assert data[0]["title"] == "My Post"
        assert data[0]["date"] == "2024-06-01"
        assert "Some content" in data[0]["content"]
