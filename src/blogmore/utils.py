"""Utility functions for blogmore."""

from __future__ import annotations

import hashlib
import os
import re
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from blogmore.markdown.plain_text import html_to_plain_text


@contextmanager
def timed_step(label: str) -> Generator[None, None, None]:
    """Time a named generation step and print its wall-clock duration.

    Prints `label` immediately (without a trailing newline) so the elapsed
    time can be appended on the same line once the step finishes.  If the
    step raises an exception a bare newline is emitted before re-raising, so
    subsequent output always starts on a fresh line.

    Args:
        label: Human-readable description of the step, printed as it begins.

    Yields:
        Nothing — the caller performs the work inside the `with` block.
    """
    print(label, end="", flush=True)
    start = time.monotonic()
    try:
        yield
    except BaseException:
        print()  # ensure subsequent output starts on a fresh line
        raise
    elapsed = time.monotonic() - start
    print(f" [{elapsed:.2f}s]")


def get_user_cache_dir() -> Path:
    """Return the platform-specific user cache directory for blogmore.

    On Windows, this uses %LOCALAPPDATA%. On all other platforms (Unix/macOS),
    it follows the XDG Base Directory Specification (~/.cache).

    Returns:
        A Path object pointing to the user's cache directory for blogmore.
    """
    if sys.platform == "win32":
        # Windows: %LOCALAPPDATA%\blogmore\cache
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "blogmore" / "cache"

    # Unix-like (Linux, macOS, etc.): ~/.cache/blogmore or $XDG_CACHE_HOME/blogmore
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "blogmore"


def get_blog_cache_dir(content_dir: Path) -> Path:
    """Return a unique cache directory for a specific blog.

    The directory is unique to the absolute path of the blog's content directory,
    allowing multiple blogs to be managed on the same system without cache
    collisions.

    Args:
        content_dir: The blog's content directory.

    Returns:
        A Path object pointing to the blog-specific cache directory.
    """
    # Create a unique hash for the absolute path of the content directory
    path_hash = hashlib.sha256(str(content_dir.resolve()).encode("utf-8")).hexdigest()
    return get_user_cache_dir() / "blogs" / path_hash


def count_words_from_html(html_content: str) -> int:
    """Count the number of words in the given HTML content.

    Strips HTML tags (excluding fenced code blocks, which are not readable
    prose) before splitting on whitespace.

    Args:
        html_content: The HTML content to analyse.

    Returns:
        The number of words in the content.

    Examples:
        >>> count_words_from_html("<p>Hello world</p>")
        2
        >>> count_words_from_html("<p>word </p>" * 10)
        10
    """
    return len(
        [
            word
            for word in re.findall(
                r"\w+", html_to_plain_text(html_content, exclude_code_blocks=True)
            )
            if word
        ]
    )


def calculate_reading_time_from_html(
    html_content: str, words_per_minute: int = 200
) -> int:
    """Calculate the estimated reading time for HTML content in whole minutes.

    Args:
        html_content: The HTML content to analyse.
        words_per_minute: Average reading speed (default: 200 WPM)

    Returns:
        Estimated reading time in whole minutes (minimum 1 minute).

    Examples:
        >>> calculate_reading_time_from_html("<p>Hello world</p>")
        1
        >>> calculate_reading_time_from_html("<p>word </p>" * 400)
        2
    """
    return max(1, round(count_words_from_html(html_content) / words_per_minute))


def make_urls_absolute(html_content: str, base_url: str) -> str:
    """Rewrite root-relative URLs in HTML content to absolute URLs.

    Converts `src` and `href` attributes whose values begin with `/`
    to full absolute URLs by prepending *base_url*.  Attributes that already
    contain an absolute URL (i.e. they include a scheme such as `https://`)
    are left unchanged.

    Args:
        html_content: HTML string that may contain root-relative URL references.
        base_url: The absolute base URL to prepend (e.g. ``https://example.com``).
            Any trailing slash is ignored because root-relative paths already
            start with ``/``.

    Returns:
        HTML string with root-relative `src`/`href` values replaced by
        absolute URLs.

    Examples:
        >>> make_urls_absolute('<img src="/img/photo.jpg">', "https://example.com")
        '<img src="https://example.com/img/photo.jpg">'
        >>> make_urls_absolute('<a href="/about.html">About</a>', "https://example.com")
        '<a href="https://example.com/about.html">About</a>'
    """
    stripped = base_url.rstrip("/")

    def _replace(match: re.Match[str]) -> str:
        attr, quote, path = match.group(1), match.group(2), match.group(3)
        return f"{attr}={quote}{stripped}{path}{quote}"

    return re.sub(
        r'(src|href)=(["\'])(/[^"\']*)\2',
        _replace,
        html_content,
    )


def normalize_site_url(site_url: str) -> str:
    """Normalize a site URL by removing trailing slashes.

    This function ensures consistent URL handling by stripping trailing slashes
    from site URLs. This prevents double slashes in generated URLs when paths
    are concatenated with the site URL.

    Edge cases:
    - Empty string: Returns empty string (allows fallback URL to be used)
    - Single slash: Returns empty string (treated as equivalent to empty)
    - Multiple trailing slashes: All are removed

    Args:
        site_url: The site URL to normalize

    Returns:
        The normalized site URL without trailing slash, or empty string if empty

    Examples:
        >>> normalize_site_url("https://example.com/")
        "https://example.com"
        >>> normalize_site_url("https://example.com")
        "https://example.com"
        >>> normalize_site_url("")
        ""
        >>> normalize_site_url("/")
        ""
    """
    return site_url.rstrip("/") if site_url else ""


def simplify_html_for_feeds(html_content: str) -> str:
    """Simplify HTML content for better compatibility with RSS/Atom feed readers.

    Currently performs the following transformations:
    - Replaces `<picture>` elements with their nested `<img>` fallback tags,
      ensuring that images display correctly in readers that don't support
      the modern `<picture>` element.

    Args:
        html_content: The HTML content to simplify.

    Returns:
        Simplified HTML string.
    """
    # Replace <picture>...</picture> with just the nested <img> tag.
    # We look for <img ...> inside the picture tags and capture it.
    # The [^>]*? ensures we handle multi-line tags or attributes correctly.
    return re.sub(
        r"<picture\b[^>]*>.*?(<img\b[^>]*>).*?</picture>",
        r"\1",
        html_content,
        flags=re.DOTALL | re.IGNORECASE,
    )


### utils.py ends here
