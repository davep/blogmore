"""Unit tests for the links module."""

import unittest.mock
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from blogmore.links import check_external_links, dump_external_links, should_ignore_link
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


def test_should_ignore_link() -> None:
    """Test should_ignore_link helper."""
    ignore_list = ["google.com", "https://github.com/davep"]

    # Bare domain match
    assert should_ignore_link("https://google.com/search", ignore_list)
    assert should_ignore_link("http://google.com/", ignore_list)
    assert should_ignore_link("https://sub.google.com/path", ignore_list)
    assert not should_ignore_link("https://notgoogle.com", ignore_list)

    # Prefix match
    assert should_ignore_link("https://github.com/davep", ignore_list)
    assert should_ignore_link("https://github.com/davep/blogmore", ignore_list)
    assert not should_ignore_link("https://github.com/davep2", ignore_list)
    assert not should_ignore_link("https://github.com/other", ignore_list)


def test_check_external_links_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test check_external_links when all links are working."""
    post = Post(
        path=Path("post.md"),
        title="Post",
        content="",
        html_content='<p><a href="https://external1.com">link1</a></p>',
    )

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__.return_value = mock_response

    mock_urlopen = MagicMock(return_value=mock_response)
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = check_external_links([post])

    assert result == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert mock_urlopen.call_count == 1
    req = mock_urlopen.call_args[0][0]
    assert req.method == "HEAD"
    assert req.headers.get("User-agent") is not None


def test_check_external_links_fallback_get(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test fallback from HEAD (405) to GET (200)."""
    post = Post(
        path=Path("post.md"),
        title="Post",
        content="",
        html_content='<p><a href="https://external1.com">link1</a></p>',
    )

    err = urllib.error.HTTPError(
        "https://external1.com",
        405,
        "Method Not Allowed",
        Message(),
        None,
    )

    mock_success_response = MagicMock()
    mock_success_response.status = 200
    mock_success_response.__enter__.return_value = mock_success_response

    calls = 0

    def side_effect(
        req: urllib.request.Request, *args: Any, **kwargs: Any
    ) -> MagicMock:
        nonlocal calls
        calls += 1
        if req.method == "HEAD":
            raise err
        elif req.method == "GET":
            return mock_success_response
        raise ValueError("Unexpected request method")

    mock_urlopen = MagicMock(side_effect=side_effect)
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = check_external_links([post])

    assert result == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert calls == 2


def test_check_external_links_rate_limit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test domain off-limits after HTTP 429."""
    post = Post(
        path=Path("post.md"),
        title="Post",
        content="",
        html_content='<p><a href="https://external1.com/a">link1</a> <a href="https://external1.com/b">link2</a></p>',
    )

    err = urllib.error.HTTPError(
        "https://external1.com/a",
        429,
        "Too Many Requests",
        Message(),
        None,
    )

    def side_effect(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        raise err

    mock_urlopen = MagicMock(side_effect=side_effect)
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = check_external_links([post])

    assert result == 1
    captured = capsys.readouterr()
    assert (
        "post.md: https://external1.com/a - HTTP 429 Too Many Requests" in captured.out
    )
    assert mock_urlopen.call_count == 1


def test_check_external_links_caching(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test duplicate links reuse cached result, reporting again if broken."""
    post1 = Post(
        path=Path("post1.md"),
        title="Post 1",
        content="",
        html_content='<p><a href="https://broken.com">link1</a></p>',
    )
    post2 = Post(
        path=Path("post2.md"),
        title="Post 2",
        content="",
        html_content='<p><a href="https://broken.com">link2</a></p>',
    )

    err = urllib.error.HTTPError(
        "https://broken.com",
        404,
        "Not Found",
        Message(),
        None,
    )

    def side_effect(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        raise err

    mock_urlopen = MagicMock(side_effect=side_effect)
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = check_external_links([post1, post2])

    assert result == 1
    captured = capsys.readouterr()
    assert "post1.md: https://broken.com - HTTP 404: Not Found" in captured.out
    assert "post2.md: https://broken.com - HTTP 404: Not Found" in captured.out
    assert mock_urlopen.call_count == 1


def test_check_external_links_timeout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test network timeout handling."""
    post = Post(
        path=Path("post.md"),
        title="Post",
        content="",
        html_content='<p><a href="https://timeout.com">link</a></p>',
    )

    err = urllib.error.URLError(TimeoutError("timed out"))

    def side_effect(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        raise err

    mock_urlopen = MagicMock(side_effect=side_effect)
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = check_external_links([post])

    assert result == 1
    captured = capsys.readouterr()
    assert "post.md: https://timeout.com - Connection timed out" in captured.out


def test_check_external_links_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test check_external_links honors delay parameter."""
    import time

    post = Post(
        path=Path("post.md"),
        title="Post",
        content="",
        html_content='<p><a href="https://external1.com">link1</a> <a href="https://external2.com">link2</a></p>',
    )

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__.return_value = mock_response

    monkeypatch.setattr(
        urllib.request, "urlopen", MagicMock(return_value=mock_response)
    )

    mock_sleep = MagicMock()
    monkeypatch.setattr(time, "sleep", mock_sleep)

    result = check_external_links([post], delay=1.5)

    assert result == 0
    assert mock_sleep.call_count == 2
    mock_sleep.assert_has_calls([unittest.mock.call(1.5), unittest.mock.call(1.5)])


def test_check_external_links_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test KeyboardInterrupt exits gracefully."""
    post = Post(
        path=Path("post.md"),
        title="Post",
        content="",
        html_content='<p><a href="https://external1.com">link1</a></p>',
    )

    def side_effect(req: urllib.request.Request, *args: Any, **kwargs: Any) -> Any:
        raise KeyboardInterrupt()

    monkeypatch.setattr(urllib.request, "urlopen", MagicMock(side_effect=side_effect))

    result = check_external_links([post])

    assert result == 1
    captured = capsys.readouterr()
    assert "Link checking interrupted by user" in captured.err


def test_check_external_links_custom_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test check_external_links passes the custom timeout parameter to urlopen."""
    post = Post(
        path=Path("post.md"),
        title="Post",
        content="",
        html_content='<p><a href="https://external1.com">link1</a></p>',
    )

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__.return_value = mock_response

    mock_urlopen = MagicMock(return_value=mock_response)
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    # Call with a custom timeout of 12.3 seconds
    result = check_external_links([post], timeout=12.3)

    assert result == 0
    assert mock_urlopen.call_count == 1
    # Check that timeout parameter was passed to urlopen
    kwargs = mock_urlopen.call_args[1]
    assert kwargs.get("timeout") == 12.3
