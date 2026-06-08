"""JSON dumping utility for blog posts."""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from blogmore.backlinks import find_links, find_post_links, normalize_url_path
from blogmore.markdown.external_links import is_external_link
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


def post_to_dict(
    post: Post,
    content_dir: Path,
    normalized_to_post: dict[str, Post] | None = None,
    site_url: str = "",
) -> dict[str, Any]:
    """Convert a [`Post`][blogmore.parser.Post] object into a dictionary for JSON serialization.

    Args:
        post: The post to convert.
        content_dir: The directory containing markdown posts, used to determine
            the relative path IDs.
        normalized_to_post: An optional mapping from normalized URL paths to Post
            objects. If provided, internal post links will be identified.
        site_url: The site's base URL, used to determine whether links are
            internal or external to the blog.

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

    # Map internal post links to their relative path IDs
    internal_links: list[str] = []
    seen_internal: set[str] = set()
    if normalized_to_post:
        for _, _, _, _, target_post in find_post_links(
            post.html_content,
            normalized_to_post,
            site_url,
            post,
        ):
            target_id = str(
                target_post.path.resolve().relative_to(content_dir_resolved)
            )
            if target_id not in seen_internal:
                seen_internal.add(target_id)
                internal_links.append(target_id)

    # Extract and resolve external links

    site_domain: str | None = None
    if site_url:
        try:
            parsed = urlparse(site_url)
            site_domain = parsed.netloc.lower()
        except Exception:
            pass

    external_links: list[str] = []
    seen_external: set[str] = set()
    for raw_url, _, _, _ in find_links(post.html_content):
        if is_external_link(raw_url, site_domain) and raw_url not in seen_external:
            seen_external.add(raw_url)
            external_links.append(raw_url)

    return {
        "id": post_id,
        "path": str(post.path),
        "title": post.title,
        "content": post.content,
        "html_content": post.html_content,
        "date": date_str,
        "category": post.category,
        "tags": post.tags if post.tags is not None else [],
        "series": post.series,
        "draft": post.draft,
        "metadata": post.metadata if post.metadata is not None else {},
        "url_path": post.url_path,
        "related_posts": related_ids,
        "internal_links": internal_links,
        "external_links": external_links,
        "slug": post.slug,
        "url": post.url,
        "safe_category": post.safe_category,
        "safe_tags": post.safe_tags(),
        "sorted_tag_pairs": post.sorted_tag_pairs(),
        "safe_series": post.safe_series(),
        "series_pairs": post.series_pairs(),
        "description": post.description,
        "prose_text": post.prose_text,
        "word_count": post.word_count,
        "reading_time": post.reading_time,
        "gfi": post.gfi,
        "modified_date": modified_date_str,
    }


def dump_posts(posts: list[Post], content_dir: Path, site_url: str = "") -> None:
    """Dump all posts to stdout as JSON in posting time order.

    Args:
        posts: The list of posts to dump.
        content_dir: The directory containing markdown posts.
        site_url: The site's base URL, used to determine whether links are
            internal or external to the blog.
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

    normalized_to_post = {normalize_url_path(post.url): post for post in posts}

    post_dicts = [
        post_to_dict(post, content_dir, normalized_to_post, site_url)
        for post in sorted_posts
    ]

    json.dump(post_dicts, sys.stdout, indent=2, cls=BlogmoreJSONEncoder)
    sys.stdout.write("\n")


def dump_categories(posts: list[Post]) -> None:
    """Dump all categories found in posts to stdout as a JSON structure.

    The structure is a list of pairs, where the first item is the URL-safe slug
    for the category, and the second is the most common text for that category.
    The order of the categories matches the category cloud page (sorted
    case-insensitively by the display name).

    Args:
        posts: The list of posts to process.
    """
    from blogmore.generator.grouping import group_posts_by_category
    from blogmore.parser import sanitize_for_url

    posts_by_category = group_posts_by_category(posts)

    category_pairs: list[tuple[str, str]] = []
    for category_lower, (category_display, _) in posts_by_category.items():
        slug = sanitize_for_url(category_lower)
        category_pairs.append((slug, category_display))

    # Sort case-insensitively by display name to match the category cloud page
    category_pairs.sort(key=lambda pair: pair[1].lower())

    json.dump(category_pairs, sys.stdout, indent=2)
    sys.stdout.write("\n")
