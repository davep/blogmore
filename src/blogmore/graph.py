"""Graph data generation for BlogMore.

Builds a force-directed graph data structure from posts, connecting them
via internal links, shared tags, and shared categories.  This module is
only consulted when ``with_graph`` is enabled in the site configuration.
When the feature is disabled none of these functions are called, so users
pay no cost for a feature they do not use.
"""

##############################################################################
# Python imports.
import json
import re
from dataclasses import dataclass, field
from typing import Any

##############################################################################
# Local imports.
from blogmore.parser import Post, sanitize_for_url

##############################################################################
# Compiled regular expressions for Markdown link detection.

# Inline links: [link text](url) or [link text](url "optional title")
_INLINE_LINK_RE: re.Pattern[str] = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

# Reference-style link definitions: [id]: url  (at the start of any line)
_LINK_DEF_RE: re.Pattern[str] = re.compile(r"^\[([^\]]+)\]:\s+(\S+)", re.MULTILINE)

# Reference-style links: [text][ref] or [text][] (implicit ref = text)
_REF_LINK_RE: re.Pattern[str] = re.compile(r"\[([^\]]+)\]\[([^\]]*)\]")


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


def _extract_link_url(raw_url: str) -> str:
    """Extract only the URL from a raw Markdown link target string.

    Strips an optional title attribute (text in quotes following a space
    after the URL).

    Args:
        raw_url: The raw URL string as captured from Markdown source.

    Returns:
        The URL portion with any trailing title attribute removed.
    """
    return raw_url.split()[0] if raw_url.strip() else raw_url


def _find_link_urls(content: str) -> list[str]:
    """Find all hyperlink target URLs in Markdown source content.

    Recognises inline links (``[text](url)``) and reference-style links
    (``[text][ref]`` with a ``[ref]: url`` definition).

    Args:
        content: Raw Markdown source to scan.

    Returns:
        A list of URL strings found in the content.
    """
    urls: list[str] = []

    # Collect reference link definitions first.
    refs: dict[str, str] = {}
    for definition in _LINK_DEF_RE.finditer(content):
        refs[definition.group(1).lower()] = definition.group(2).strip()

    # Inline links: [text](url)
    for match in _INLINE_LINK_RE.finditer(content):
        url = _extract_link_url(match.group(2))
        if url:
            urls.append(url)

    # Reference-style links: [text][ref] or [text][]
    for match in _REF_LINK_RE.finditer(content):
        ref_id = match.group(2).lower() or match.group(1).lower()
        url = refs.get(ref_id, "")
        if url:
            urls.append(url)

    return urls


def _to_root_relative(url: str, site_url: str) -> str | None:
    """Convert a URL to a root-relative path if it targets this site.

    Handles absolute paths (``/path``), full URLs that begin with
    ``site_url``, and rejects genuinely external links, relative paths,
    and fragment-only references.

    Args:
        url: The raw URL from a Markdown link.
        site_url: The site's base URL (e.g. ``https://example.com``), used
            to recognise full URLs pointing back to this site.

    Returns:
        The root-relative path starting with ``/``, or ``None`` if the URL
        does not target this site.
    """
    url = url.strip()
    if not url or url.startswith("#"):
        return None
    # Strip fragment and query string.
    url = url.split("#")[0].split("?")[0]
    if not url:
        return None
    if url.startswith("/"):
        return url
    if "://" in url:
        if site_url:
            stripped_site = site_url.rstrip("/")
            if url.startswith(stripped_site + "/") or url == stripped_site:
                return "/" + url[len(stripped_site) :].lstrip("/")
        return None
    # Relative path — skip; too ambiguous to resolve safely.
    return None


def _normalize_path(path: str) -> str:
    """Normalise a URL path for comparison.

    Strips ``index.html``, ``.html`` extensions, and trailing slashes so
    that paths can be compared regardless of whether ``clean_urls`` is
    enabled.

    Args:
        path: The URL path to normalise.

    Returns:
        The normalised path without a trailing slash, ``.html`` extension,
        or ``/index.html`` suffix.
    """
    path = path.rstrip("/")
    if path.endswith("/index.html"):
        path = path[: -len("/index.html")]
    elif path.endswith(".html"):
        path = path[: -len(".html")]
    return path


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

    * Post → tag relationships (one edge per post-tag pair).
    * Post → category relationships (one edge per post that has a category).
    * Post → post internal links (one edge per unique directed link found in
      Markdown content, discovered by scanning inline and reference-style
      Markdown links).

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

    # Build a normalised-path → post URL mapping for efficient link resolution.
    normalized_to_url: dict[str, str] = {}
    for post in posts:
        normalized_to_url[_normalize_path(post.url)] = post.url

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

    # --- Tag nodes and post→tag edges ----------------------------------------
    seen_tags: dict[str, str] = {}  # safe_tag → display tag
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

    # --- Category nodes and post→category edges ------------------------------
    seen_categories: dict[str, str] = {}  # safe_category → display category
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

    # --- Post→post edges from internal links ---------------------------------
    link_pairs: set[tuple[str, str]] = set()
    for source_post in posts:
        for raw_url in _find_link_urls(source_post.content):
            path = _to_root_relative(raw_url, site_url)
            if path is None:
                continue
            normalized = _normalize_path(path)
            target_url = normalized_to_url.get(normalized)
            if target_url is None or target_url == source_post.url:
                continue
            pair = (source_post.url, target_url)
            if pair not in link_pairs:
                link_pairs.add(pair)
                graph.links.append({"source": source_post.url, "target": target_url})

    return graph


### graph.py ends here
