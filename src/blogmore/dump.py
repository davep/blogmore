"""JSON dumping utility for blog posts."""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from blogmore.parser import Post


class BlogmoreJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime, date, and Path objects."""

    def default(self, o: Any) -> Any:
        """Convert non-serializable objects to serializable formats.

        Args:
            o: The object to convert.

        Returns:
            The serialized representation of the object.
        """
        if isinstance(o, (dt.datetime, dt.date)):
            return o.isoformat()
        if isinstance(o, Path):
            return str(o)
        return super().default(o)


def post_to_dict(post: Post, content_dir: Path) -> dict[str, Any]:
    """Convert a [`Post`][blogmore.parser.Post] object into a dictionary for JSON serialization.

    Args:
        post: The post to convert.
        content_dir: The directory containing markdown posts, used to determine
            the relative path IDs.

    Returns:
        A dictionary representation of the post.
    """
    content_dir_resolved = content_dir.resolve()
    post_id = str(post.path.resolve().relative_to(content_dir_resolved))

    # Convert datetime values to ISO format strings or None
    date_str = post.date.isoformat() if post.date else None
    modified_date_str = post.modified_date.isoformat() if post.modified_date else None

    # Map related posts to their relative path IDs
    related_ids = [
        str(rel.path.resolve().relative_to(content_dir_resolved))
        for rel in post.related_posts
    ]

    return {
        "id": post_id,
        "path": str(post.path),
        "title": post.title,
        "content": post.content,
        "html_content": post.html_content,
        "date": date_str,
        "category": post.category,
        "tags": post.tags if post.tags is not None else [],
        "draft": post.draft,
        "metadata": post.metadata if post.metadata is not None else {},
        "url_path": post.url_path,
        "related_posts": related_ids,
        "slug": post.slug,
        "url": post.url,
        "safe_category": post.safe_category,
        "safe_tags": post.safe_tags(),
        "sorted_tag_pairs": post.sorted_tag_pairs(),
        "description": post.description,
        "prose_text": post.prose_text,
        "word_count": post.word_count,
        "reading_time": post.reading_time,
        "gfi": post.gfi,
        "modified_date": modified_date_str,
    }


def dump_posts(posts: list[Post], content_dir: Path) -> None:
    """Dump all posts to stdout as JSON in posting time order.

    Args:
        posts: The list of posts to dump.
        content_dir: The directory containing markdown posts.
    """

    # Sort posts chronologically (oldest first, posting time order)
    # Posts without dates sort to the end of the list
    def chronological_key(p: Post) -> float:
        if p.date is None:
            return float("inf")
        if p.date.tzinfo:
            return p.date.timestamp()
        return p.date.replace(tzinfo=dt.UTC).timestamp()

    sorted_posts = sorted(posts, key=chronological_key)

    post_dicts = [post_to_dict(post, content_dir) for post in sorted_posts]

    json.dump(post_dicts, sys.stdout, indent=2, cls=BlogmoreJSONEncoder)
    sys.stdout.write("\n")
