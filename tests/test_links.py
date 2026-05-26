"""Unit tests for the links module."""

from pathlib import Path

import pytest

from blogmore.links import dump_external_links
from blogmore.markdown.external_links import is_external_link
from blogmore.parser import Post


def test_is_external_link() -> None:
    """Test is_external_link with different kinds of links."""
    # Absolute external links
    assert is_external_link("https://example.com")
    assert is_external_link("http://google.com/search")
    assert is_external_link("ftp://ftp.example.com")

    # Relative/internal links
    assert not is_external_link("/about.html")
    assert not is_external_link("posts/first.html")
    assert not is_external_link("#top")
    assert not is_external_link("")

    # Same domain check
    assert not is_external_link("https://example.com/about", site_domain="example.com")
    assert not is_external_link(
        "https://www.example.com/about", site_domain="example.com"
    )
    assert is_external_link(
        "https://subdomain.example.com/about", site_domain="example.com"
    )


def test_dump_external_links(capsys: pytest.CaptureFixture[str]) -> None:
    """Test dump_external_links outputs CSV correctly with deduplication."""
    post1 = Post(
        path=Path("post1.md"),
        title="Post One",
        content="[link1](https://external1.com) [link1 again](https://external1.com) [link2](https://external2.com)",
        html_content='<p><a href="https://external1.com">link1</a> <a href="https://external1.com">link1 again</a> <a href="https://external2.com">link2</a></p>',
    )
    post2 = Post(
        path=Path("post2.md"),
        title="Post Two",
        content="[link1](https://external1.com) [internal](/internal)",
        html_content='<p><a href="https://external1.com">link1</a> <a href="/internal">internal</a></p>',
    )

    dump_external_links([post1, post2], site_url="https://internal.com")

    captured = capsys.readouterr()
    expected_lines = [
        "https://external1.com,post1.md",
        "https://external2.com,post1.md",
        "https://external1.com,post2.md",
        "",
    ]
    # Normalize line endings to support any platform's terminators
    actual_lines = captured.out.replace("\r\n", "\n").split("\n")
    assert actual_lines == expected_lines
