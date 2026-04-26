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
        nodes: List of node dicts, each with ``id``, ``label``, ``type``,
            and ``url`` keys.
        links: List of edge dicts, each with ``source`` and ``target`` keys
            corresponding to node ``id`` values.
    """

    nodes: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)

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
        graph.nodes.append(
            {
                "id": post.url,
                "label": post.title,
                "type": "post",
                "url": post.url,
            }
        )

    # --- Tag nodes and post->tag edges ----------------------------------------
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
                        }
                    )
                graph.links.append({"source": post.url, "target": tag_node_id})

    # --- Category nodes and post->category edges ------------------------------
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
