"""Shared utility helpers for the site generator."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from blogmore.parser import Post


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
        Nothing — the caller performs the work inside the ``with`` block.
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


def minified_filename(source: str | Path) -> str:
    """Compute the minified output filename for a given source filename.

    Args:
        source: Source filename.

    Returns:
        The corresponding minified filename.
    """
    if isinstance(source, str) and not source:
        return source
    if (source := Path(source)).suffix:
        source = source.with_suffix(f".min{source.suffix}")
    return str(source)


def paginate_posts(posts: list[Post], posts_per_page: int) -> list[list[Post]]:
    """Split a list of posts into pages.

    Args:
        posts: List of posts to paginate
        posts_per_page: Number of posts per page

    Returns:
        List of pages, where each page is a list of posts
    """
    if not posts:
        return []
    if posts_per_page <= 0:
        return [posts]

    pages = []
    for i in range(0, len(posts), posts_per_page):
        pages.append(posts[i : i + posts_per_page])
    return pages


### utils.py ends here
