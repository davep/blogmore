"""Graph data generation for BlogMore.

Builds a force-directed graph data structure from posts, connecting them
via internal links, shared tags, and shared categories.  This module is
only consulted when ``with_graph`` is enabled in the site configuration.
When the feature is disabled none of these functions are called, so users
pay no cost for a feature they do not use.

Link scanning and URL normalisation are delegated to the shared utilities
in :mod:`blogmore.backlinks` to avoid code duplication.
"""

##############################################################################
# Python imports.
import json
from dataclasses import dataclass, field
from typing import Any

##############################################################################
# Local imports.
from blogmore.backlinks import _find_links, _normalize_url_path, _to_path
from blogmore.parser import Post, sanitize_for_url


@dataclass
class GraphData:
    """Data for the post-relationship force-directed graph.

    Attributes:
        nodes: List of node dicts.  Each node always has ``id``, ``label``,
            ``type``, and ``url`` keys.  Post nodes additionally carry
            ``date`` (ISO date string or ``None``), ``description`` (str),
            and ``cover`` (URL string or ``None``).  Tag and category nodes
            additionally carry ``post_count`` (int).
        links: List of edge dicts, each with ``source`` and ``target`` keys
            corresponding to node ``id`` values.
    """

    nodes: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)

    # Node dict shapes (informational — not enforced at runtime):
    #
    # Post node:
    #   id, label, type="post", url, date (str|None), description (str),
    #   cover (str|None)
    #
    # Tag node:
    #   id, label, type="tag", url, post_count (int)
    #
    # Category node:
    #   id, label, type="category", url, post_count (int)

    def to_json(self) -> str:
        """Serialise the graph data to a JSON string.

        Returns:
            A JSON string of the form ``{"nodes": [...], "links": [...]}``.
        """
        return json.dumps({"nodes": self.nodes, "links": self.links})


def build_graph_data(
    posts: list[Post],
    tag_dir: str = "tag",
    category_dir: str = "category",
    site_url: str = "",
) -> GraphData:
    """Build force-directed graph data from a list of posts.

    Creates one node for every post, for every unique tag encountered across
    all posts, and for every unique category encountered across all posts.
    Adds edges for:

    * Post -> tag relationships (one edge per post-tag pair).
    * Post -> category relationships (one edge per post that has a category).
    * Post -> post internal links (one edge per unique directed link found in
      Markdown content, discovered by scanning inline and reference-style
      Markdown links via :func:`~blogmore.backlinks._find_links`).

    Args:
        posts: All published posts for the site.
        tag_dir: URL path segment used for tag archive pages.  Defaults to
            ``"tag"``.
        category_dir: URL path segment used for category archive pages.
            Defaults to ``"category"``.
        site_url: The site's base URL (e.g. ``"https://example.com"``).
            Used to recognise full URLs that point back to this site when
            scanning post content for internal links.  May be empty.

    Returns:
        A :class:`GraphData` instance populated with nodes and links.
    """
    graph = GraphData()

    # Build a normalised-path -> post URL mapping for efficient link resolution.
    normalized_to_url: dict[str, str] = {}
    for post in posts:
        normalized_to_url[_normalize_url_path(post.url)] = post.url

    # --- Post nodes -----------------------------------------------------------
    for post in posts:
        raw_cover: str | None = (
            str(post.metadata["cover"])
            if post.metadata and post.metadata.get("cover")
            else None
        )
        # Normalise cover to a URL the browser can resolve from any page.
        # Absolute URLs (http/https) are left untouched; paths that already
        # start with "/" are root-relative and also left untouched; anything
        # else is a bare relative path that must be made root-absolute so the
        # tooltip <img> is not broken regardless of the current page location.
        if raw_cover is None:
            cover: str | None = None
        elif raw_cover.startswith(("http://", "https://", "/")):
            cover = raw_cover
        else:
            cover = f"/{raw_cover}"
        graph.nodes.append(
            {
                "id": post.url,
                "label": post.title,
                "type": "post",
                "url": post.url,
                "date": post.date.strftime("%Y-%m-%d") if post.date else None,
                "description": post.description,
                "cover": cover,
            }
        )

    # --- Tag nodes and post->tag edges ----------------------------------------

    # Count posts per tag so the tooltip can display the tally.
    tag_post_counts: dict[str, int] = {}
    for post in posts:
        if post.tags:
            for tag in post.tags:
                safe = sanitize_for_url(tag)
                tag_post_counts[safe] = tag_post_counts.get(safe, 0) + 1

    seen_tags: dict[str, str] = {}  # safe_tag -> display tag
    for post in posts:
        if post.tags:
            for tag in post.tags:
                safe = sanitize_for_url(tag)
                tag_node_id = f"tag:{safe}"
                if safe not in seen_tags:
                    seen_tags[safe] = tag
                    graph.nodes.append(
                        {
                            "id": tag_node_id,
                            "label": tag,
                            "type": "tag",
                            "url": f"/{tag_dir}/{safe}/",
                            "post_count": tag_post_counts[safe],
                        }
                    )
                graph.links.append({"source": post.url, "target": tag_node_id})

    # --- Category nodes and post->category edges ------------------------------

    # Count posts per category so the tooltip can display the tally.
    cat_post_counts: dict[str, int] = {}
    for post in posts:
        if post.category:
            safe_cat = sanitize_for_url(post.category)
            cat_post_counts[safe_cat] = cat_post_counts.get(safe_cat, 0) + 1

    seen_categories: dict[str, str] = {}  # safe_category -> display category
    for post in posts:
        if post.category:
            safe_cat = sanitize_for_url(post.category)
            cat_node_id = f"category:{safe_cat}"
            if safe_cat not in seen_categories:
                seen_categories[safe_cat] = post.category
                graph.nodes.append(
                    {
                        "id": cat_node_id,
                        "label": post.category,
                        "type": "category",
                        "url": f"/{category_dir}/{safe_cat}/",
                        "post_count": cat_post_counts[safe_cat],
                    }
                )
            graph.links.append({"source": post.url, "target": cat_node_id})

    # --- Post->post edges from internal links ---------------------------------
    # Reuse the link-scanning logic from the backlinks module: _find_links
    # returns (url, match_start, match_end, link_text) tuples; only the URL
    # is needed here for graph edge construction.
    link_pairs: set[tuple[str, str]] = set()
    for source_post in posts:
        for raw_url, _, _, _ in _find_links(source_post.content):
            path = _to_path(raw_url, site_url)
            if path is None:
                continue
            normalized = _normalize_url_path(path)
            target_url = normalized_to_url.get(normalized)
            if target_url is None or target_url == source_post.url:
                continue
            pair = (source_post.url, target_url)
            if pair not in link_pairs:
                link_pairs.add(pair)
                graph.links.append({"source": source_post.url, "target": target_url})

    return graph


### graph.py ends here
