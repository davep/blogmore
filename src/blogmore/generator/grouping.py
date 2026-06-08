"""Post-grouping and word-cloud helpers for the site generator."""

from collections.abc import Callable
from typing import Any

from blogmore.parser import Post


def group_posts_by_attribute(
    posts: list[Post],
    get_values: Callable[[Post], list[str]],
) -> dict[str, tuple[str, list[Post]]]:
    """Group posts by a string attribute (case-insensitive).

    The display name for each unique value (compared case-insensitively) is
    the most common (frequent) casing version of that value across all posts.
    If there is a tie, the first-occurring casing is used.

    Args:
        posts: List of posts to group.
        get_values: Callable that returns the list of attribute values for
            a single post (e.g. the post's tags or a single-element list
            containing the post's category).

    Returns:
        Dictionary mapping the lowercase attribute value to a
        ``(display_name, posts)`` tuple.
    """
    from collections import Counter

    # Raw results mapping: lowercase_value -> (casing_counts, unique_casings_in_order, posts)
    result_raw: dict[str, tuple[Counter[str], list[str], list[Post]]] = {}

    for post in posts:
        for value in get_values(post):
            value_lower = value.lower()
            if value_lower not in result_raw:
                result_raw[value_lower] = (Counter(), [], [])
            counter, order, posts_list = result_raw[value_lower]
            counter[value] += 1
            if value not in order:
                order.append(value)
            posts_list.append(post)

    result: dict[str, tuple[str, list[Post]]] = {}
    for value_lower, (counter, order, posts_list) in result_raw.items():
        # Find the most common casing with first-occurrence order as a tie-breaker.
        best_casing = min(
            order,
            key=lambda val: (-counter[val], order.index(val)),
        )
        result[value_lower] = (best_casing, posts_list)

    return result


def group_posts_by_tag(posts: list[Post]) -> dict[str, tuple[str, list[Post]]]:
    """Group posts by tag (case-insensitive).

    Args:
        posts: List of posts to group

    Returns:
        Dictionary mapping lowercase tag to (display_name, posts)
    """
    return group_posts_by_attribute(posts, lambda p: p.tags or [])


def group_posts_by_category(posts: list[Post]) -> dict[str, tuple[str, list[Post]]]:
    """Group posts by category (case-insensitive).

    Args:
        posts: List of posts to group

    Returns:
        Dictionary mapping lowercase category to (display_name, posts)
    """
    return group_posts_by_attribute(posts, lambda p: [p.category] if p.category else [])


def group_posts_by_series(posts: list[Post]) -> dict[str, tuple[str, list[Post]]]:
    """Group posts by series (case-insensitive).

    Args:
        posts: List of posts to group.

    Returns:
        Dictionary mapping lowercase series to (display_name, posts).
    """
    return group_posts_by_attribute(posts, lambda p: p.series)


def calculate_cloud_font_sizes(
    data: list[dict[str, Any]],
    min_size: float = 1.0,
    max_size: float = 2.5,
) -> None:
    """Assign ``font_size`` to every item in a word-cloud data list.

    Uses linear interpolation between *min_size* and *max_size* based on
    each item's ``"count"`` field relative to the minimum and maximum
    counts in the list.  When all items share the same count, the midpoint
    size is used for every item.

    Mutates each dict in *data* in-place by adding a ``"font_size"`` key.

    Args:
        data: List of dicts, each containing at least a ``"count"`` key
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
