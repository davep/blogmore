"""Search index generation for static site search."""

import json
import re
from pathlib import Path
from typing import Any

from blogmore.parser import Post


def strip_html(html: str) -> str:
    """Strip HTML tags from a string, returning plain text.

    Replaces tags with spaces to preserve word boundaries, then collapses
    multiple whitespace characters into a single space.

    Args:
        html: HTML string to strip.

    Returns:
        Plain text without HTML tags.
    """
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_search_index(posts: list[Post]) -> list[dict[str, Any]]:
    """Build a search index from a list of posts.

    Each entry in the returned list contains the post title, URL, date,
    and a plain-text representation of the post body suitable for
    client-side full-text search.

    Args:
        posts: List of posts to index.

    Returns:
        List of dictionaries, each representing a searchable post entry.
    """
    index: list[dict[str, Any]] = []
    for post in posts:
        entry: dict[str, Any] = {
            "title": post.title,
            "url": post.url,
            "date": post.date.strftime("%Y-%m-%d") if post.date else "",
            "content": strip_html(post.html_content),
        }
        index.append(entry)
    return index


def write_search_index(posts: list[Post], output_dir: Path) -> None:
    """Write the search index JSON file to the output directory.

    The file is written as ``search_index.json`` at the root of the
    output directory.  It is a JSON array of objects as produced by
    :func:`build_search_index`.

    Args:
        posts: List of posts to index.
        output_dir: Output directory to write the index into.
    """
    index = build_search_index(posts)
    output_path = output_dir / "search_index.json"
    output_path.write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
