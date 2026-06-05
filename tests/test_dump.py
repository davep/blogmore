"""Tests for the post JSON dumping utility."""

import datetime as dt
import json
from pathlib import Path

import pytest

from blogmore.dump import dump_posts, post_to_dict
from blogmore.parser import Post


def test_post_to_dict_basic() -> None:
    """Test post_to_dict returns expected dictionary fields."""
    post = Post(
        path=Path("posts/hello.md"),
        title="Hello World",
        content="Welcome.",
        html_content="<p>Welcome.</p>",
        date=dt.datetime(2026, 5, 31, 10, 0, tzinfo=dt.UTC),
        category="Tech",
        tags=["python", "blogging"],
        series=["My Series"],
        draft=False,
        url_path="/posts/hello/",
    )

    result = post_to_dict(post, content_dir=Path("."))
    assert result["id"] == "posts/hello.md"
    assert result["title"] == "Hello World"
    assert result["content"] == "Welcome."
    assert result["html_content"] == "<p>Welcome.</p>"
    assert result["date"] == "2026-05-31T10:00:00+00:00"
    assert result["category"] == "Tech"
    assert result["tags"] == ["python", "blogging"]
    assert result["series"] == ["My Series"]
    assert result["safe_series"] == ["my-series"]
    assert result["series_pairs"] == [("My Series", "my-series")]
    assert result["draft"] is False
    assert result["slug"] == "hello"
    assert result["url"] == "/posts/hello/"
    assert result["internal_links"] == []
    assert result["external_links"] == []


def test_post_to_dict_links() -> None:
    """Test post_to_dict extracts internal and external links."""
    content_dir = Path("my_blog")
    post1 = Post(
        path=content_dir / "posts/one.md",
        title="Post One",
        content="Link to [Post Two](/posts/two.html) and [External](https://google.com).",
        html_content=(
            '<p>Link to <a href="/posts/two.html">Post Two</a>, '
            'self <a href="/posts/one.html">Post One</a>, and '
            '<a href="https://google.com">External</a>.</p>'
        ),
        url_path="/posts/one.html",
    )
    post2 = Post(
        path=content_dir / "posts/two.md",
        title="Post Two",
        content="Nothing here.",
        html_content="<p>Nothing here.</p>",
        url_path="/posts/two.html",
    )

    from blogmore.backlinks import normalize_url_path

    normalized_to_post = {
        normalize_url_path(post1.url): post1,
        normalize_url_path(post2.url): post2,
    }

    result = post_to_dict(
        post1,
        content_dir=content_dir,
        normalized_to_post=normalized_to_post,
        site_url="https://myblog.com",
    )

    assert result["id"] == "posts/one.md"
    # Post one should link to post two (internal), but not to itself (self link is excluded),
    # and not to google.com (which is external)
    assert result["internal_links"] == ["posts/two.md"]
    assert result["external_links"] == ["https://google.com"]


def test_dump_posts(capsys: pytest.CaptureFixture[str]) -> None:
    """Test dump_posts writes sorted posts to stdout as JSON.

    Args:
        capsys: The pytest capture fixture.
    """
    content_dir = Path("content")
    post1 = Post(
        path=content_dir / "post1.md",
        title="Second",
        content="Link to [First](/post2.html)",
        html_content='<p><a href="/post2.html">First</a></p>',
        date=dt.datetime(2026, 5, 30, tzinfo=dt.UTC),
        url_path="/post1.html",
    )
    post2 = Post(
        path=content_dir / "post2.md",
        title="First",
        content="Empty",
        html_content="<p>Empty</p>",
        date=dt.datetime(2026, 5, 29, tzinfo=dt.UTC),
        url_path="/post2.html",
    )

    # Note: oldest should be first in posting time order, i.e. post2 first, then post1.
    dump_posts([post1, post2], content_dir, site_url="https://example.com")

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data) == 2
    assert data[0]["title"] == "First"
    assert data[0]["id"] == "post2.md"
    assert data[1]["title"] == "Second"
    assert data[1]["id"] == "post1.md"
    # Check internal/external link values in dump output
    assert data[0]["internal_links"] == []
    assert data[1]["internal_links"] == ["post2.md"]
