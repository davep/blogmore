"""Logic for grouping posts by tags, categories, etc."""

from collections.abc import Callable
from typing import Any

from blogmore.parser import Post


def group_posts_by_attribute(
    posts: list[Post],
    get_values: Callable[[Post], list[str]],
) -> dict[str, tuple[str, list[Post]]]:
    """Group posts by a string attribute (case-insensitive).

    The first occurrence of each value is used as the display name; all
    subsequent occurrences of the same value (compared case-insensitively)
    are accumulated under the same key.

    Args:
        posts: List of posts to group.
        get_values: Callable that returns the list of attribute values for
            a single post (e.g. the post's tags or a single-element list
            containing the post's category).

    Returns:
        Dictionary mapping the lowercase attribute value to a
        `(display_name, posts)` tuple.
    """
    result: dict[str, tuple[str, list[Post]]] = {}
    for post in posts:
        for value in get_values(post):
            value_lower = value.lower()
            if value_lower not in result:
                # Store the first occurrence as the display name.
                result[value_lower] = (value, [])
            result[value_lower][1].append(post)
    return result


def group_posts_by_tag(posts: list[Post]) -> dict[str, tuple[str, list[Post]]]:
    """Group posts by tag (case-insensitive)."""
    return group_posts_by_attribute(posts, lambda post: post.tags or [])


def group_posts_by_category(posts: list[Post]) -> dict[str, tuple[str, list[Post]]]:
    """Group posts by category (case-insensitive)."""
    return group_posts_by_attribute(
        posts, lambda post: [post.category] if post.category else []
    )


def calculate_cloud_font_sizes(
    data: list[dict[str, Any]],
    min_size: float = 1.0,
    max_size: float = 2.5,
) -> None:
    """Assign `font_size` to every item in a word-cloud data list.

    Uses linear interpolation between `min_size` and `max_size` based on
    each item's `count` field relative to the minimum and maximum
    counts in the list.  When all items share the same count, the midpoint
    size is used for every item.

    Mutates each dict in `data` in-place by adding a `font_size` key.

    Args:
        data: List of dicts, each containing at least a `count` key
            with an integer value.
        min_size: The minimum font size (em units) for the least-frequent
            item.
        max_size: The maximum font size (em units) for the most-frequent
            item.
    """
    if not data:
        return

    counts = [item["count"] for item in data]
    min_count = min(counts)
    max_count = max(counts)

    if max_count > min_count:
        for item in data:
            ratio = (item["count"] - min_count) / (max_count - min_count)
            item["font_size"] = min_size + ratio * (max_size - min_size)
    else:
        midpoint = (min_size + max_size) / 2
        for item in data:
            item["font_size"] = midpoint
