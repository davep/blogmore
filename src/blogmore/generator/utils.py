"""Utility functions for the site generator."""

from pathlib import Path

from blogmore.parser import Post


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
