"""Tests for the graph module."""

##############################################################################
# Python imports.
import datetime as dt
import json
from pathlib import Path

##############################################################################
# Application imports.
from blogmore.graph import (
    GraphData,
    _extract_link_url,
    _find_link_urls,
    _normalize_path,
    _to_root_relative,
    build_graph_data,
)
from blogmore.parser import Post

##############################################################################
# Helpers.


def _make_post(
    slug: str,
    content: str,
    url_path: str,
    title: str = "Test Post",
    tags: list[str] | None = None,
    category: str | None = None,
    date: dt.datetime | None = None,
) -> Post:
    """Create a minimal Post fixture for graph tests.

    Args:
        slug: Used to build a unique file path.
        content: Raw Markdown content.
        url_path: The URL path to assign (mimics generator output).
        title: Optional title override.
        tags: Optional list of tag strings.
        category: Optional category string.
        date: Optional publication date.

    Returns:
        A Post object suitable for graph tests.
    """
    post = Post(
        path=Path(f"{slug}.md"),
        title=title,
        content=content,
        html_content=f"<p>{content}</p>",
        tags=tags,
        category=category,
        date=date,
    )
    post.url_path = url_path
    return post


##############################################################################
# GraphData tests.


class TestGraphData:
    """Tests for the GraphData dataclass."""

    def test_to_json_empty(self) -> None:
        """Empty GraphData serialises to JSON with empty nodes and links."""
        graph = GraphData()
        result = json.loads(graph.to_json())
        assert result == {"nodes": [], "links": []}

    def test_to_json_with_data(self) -> None:
        """GraphData with nodes and links serialises correctly."""
        graph = GraphData(
            nodes=[{"id": "/a.html", "label": "A", "type": "post", "url": "/a.html"}],
            links=[{"source": "/a.html", "target": "/b.html"}],
        )
        result = json.loads(graph.to_json())
        assert len(result["nodes"]) == 1
        assert len(result["links"]) == 1
        assert result["nodes"][0]["id"] == "/a.html"
        assert result["links"][0]["source"] == "/a.html"


##############################################################################
# _extract_link_url tests.


class TestExtractLinkUrl:
    """Tests for the _extract_link_url helper."""

    def test_plain_url(self) -> None:
        """A bare URL is returned unchanged."""
        assert _extract_link_url("/path/to/post.html") == "/path/to/post.html"

    def test_url_with_title(self) -> None:
        """A URL with a title attribute has the title stripped."""
        assert (
            _extract_link_url('/path/to/post.html "My Title"') == "/path/to/post.html"
        )

    def test_empty_string(self) -> None:
        """An empty string returns an empty string."""
        assert _extract_link_url("") == ""

    def test_whitespace_only(self) -> None:
        """Whitespace-only returns the original whitespace string unchanged."""
        assert _extract_link_url("   ") == "   "


##############################################################################
# _find_link_urls tests.


class TestFindLinkUrls:
    """Tests for the _find_link_urls helper."""

    def test_inline_link(self) -> None:
        """An inline Markdown link is detected."""
        content = "See [my post](/2024/01/01/post.html) for details."
        urls = _find_link_urls(content)
        assert "/2024/01/01/post.html" in urls

    def test_reference_link(self) -> None:
        """A reference-style Markdown link is detected."""
        content = "See [my post][post].\n\n[post]: /2024/01/01/post.html\n"
        urls = _find_link_urls(content)
        assert "/2024/01/01/post.html" in urls

    def test_multiple_links(self) -> None:
        """Multiple inline links are all detected."""
        content = "[A](/a.html) and [B](/b.html)"
        urls = _find_link_urls(content)
        assert "/a.html" in urls
        assert "/b.html" in urls

    def test_no_links(self) -> None:
        """Content with no links returns an empty list."""
        assert _find_link_urls("No links here.") == []

    def test_external_link_included(self) -> None:
        """External links are returned (filtering is done by _to_root_relative)."""
        content = "[GitHub](https://github.com/user/repo)"
        urls = _find_link_urls(content)
        assert "https://github.com/user/repo" in urls


##############################################################################
# _to_root_relative tests.


class TestToRootRelative:
    """Tests for the _to_root_relative helper."""

    def test_root_relative_path(self) -> None:
        """A root-relative path is returned unchanged."""
        assert _to_root_relative("/post.html", "") == "/post.html"

    def test_full_url_matching_site(self) -> None:
        """A full URL matching site_url is converted to a root-relative path."""
        assert (
            _to_root_relative("https://example.com/post.html", "https://example.com")
            == "/post.html"
        )

    def test_external_full_url_rejected(self) -> None:
        """A full URL not matching site_url is rejected."""
        assert (
            _to_root_relative("https://other.com/page", "https://example.com") is None
        )

    def test_fragment_only_rejected(self) -> None:
        """A fragment-only URL is rejected."""
        assert _to_root_relative("#section", "") is None

    def test_relative_url_rejected(self) -> None:
        """A relative URL (no leading slash) is rejected."""
        assert _to_root_relative("../other.html", "") is None

    def test_fragment_stripped(self) -> None:
        """Fragment is stripped before comparison."""
        assert _to_root_relative("/post.html#section", "") == "/post.html"

    def test_query_string_stripped(self) -> None:
        """Query string is stripped before comparison."""
        assert _to_root_relative("/post.html?ref=nav", "") == "/post.html"

    def test_empty_after_stripping(self) -> None:
        """A URL that becomes empty after stripping fragments returns None."""
        assert _to_root_relative("#", "") is None


##############################################################################
# _normalize_path tests.


class TestNormalizePath:
    """Tests for the _normalize_path helper."""

    def test_plain_html(self) -> None:
        """A .html path has the extension removed."""
        assert _normalize_path("/post.html") == "/post"

    def test_index_html(self) -> None:
        """A path ending in index.html has it removed."""
        assert _normalize_path("/post/index.html") == "/post"

    def test_trailing_slash(self) -> None:
        """A path with trailing slash has it removed."""
        assert _normalize_path("/post/") == "/post"

    def test_clean_url(self) -> None:
        """A clean URL (no extension) is returned unchanged."""
        assert _normalize_path("/post") == "/post"


##############################################################################
# build_graph_data tests.


class TestBuildGraphData:
    """Tests for the build_graph_data function."""

    def test_empty_posts_list(self) -> None:
        """Empty post list produces a graph with no nodes or links."""
        graph = build_graph_data([])
        assert graph.nodes == []
        assert graph.links == []

    def test_post_nodes_created(self) -> None:
        """Each post produces a node with type 'post'."""
        posts = [
            _make_post("post-a", "Content A", "/a.html", title="Post A"),
            _make_post("post-b", "Content B", "/b.html", title="Post B"),
        ]
        graph = build_graph_data(posts)
        post_nodes = [n for n in graph.nodes if n["type"] == "post"]
        assert len(post_nodes) == 2
        ids = {n["id"] for n in post_nodes}
        assert "/a.html" in ids
        assert "/b.html" in ids

    def test_tag_nodes_created(self) -> None:
        """Tags produce nodes with type 'tag'."""
        posts = [
            _make_post("post-a", "Content", "/a.html", tags=["Python", "Testing"]),
        ]
        graph = build_graph_data(posts)
        tag_nodes = {n["label"] for n in graph.nodes if n["type"] == "tag"}
        assert "Python" in tag_nodes
        assert "Testing" in tag_nodes

    def test_duplicate_tags_produce_single_node(self) -> None:
        """The same tag across two posts produces only one tag node."""
        posts = [
            _make_post("post-a", "A", "/a.html", tags=["python"]),
            _make_post("post-b", "B", "/b.html", tags=["python"]),
        ]
        graph = build_graph_data(posts)
        tag_nodes = [n for n in graph.nodes if n["type"] == "tag"]
        assert len(tag_nodes) == 1

    def test_category_nodes_created(self) -> None:
        """Posts with categories produce category nodes."""
        posts = [
            _make_post("post-a", "Content", "/a.html", category="News"),
        ]
        graph = build_graph_data(posts)
        cat_nodes = [n for n in graph.nodes if n["type"] == "category"]
        assert len(cat_nodes) == 1
        assert cat_nodes[0]["label"] == "News"

    def test_duplicate_categories_produce_single_node(self) -> None:
        """The same category across two posts produces only one category node."""
        posts = [
            _make_post("post-a", "A", "/a.html", category="Tech"),
            _make_post("post-b", "B", "/b.html", category="Tech"),
        ]
        graph = build_graph_data(posts)
        cat_nodes = [n for n in graph.nodes if n["type"] == "category"]
        assert len(cat_nodes) == 1

    def test_post_tag_edges(self) -> None:
        """An edge is created from each post to each of its tag nodes."""
        posts = [
            _make_post("post-a", "Content", "/a.html", tags=["alpha", "beta"]),
        ]
        graph = build_graph_data(posts)
        link_targets = {link["target"] for link in graph.links}
        assert "tag:alpha" in link_targets
        assert "tag:beta" in link_targets

    def test_post_category_edge(self) -> None:
        """An edge is created from each post to its category node."""
        posts = [
            _make_post("post-a", "Content", "/a.html", category="Tech"),
        ]
        graph = build_graph_data(posts)
        link_targets = {link["target"] for link in graph.links}
        assert "category:tech" in link_targets

    def test_post_to_post_internal_link_edge(self) -> None:
        """An edge is created between two posts when one links to the other."""
        posts = [
            _make_post(
                "post-a",
                "See [post B](/b.html) for more.",
                "/a.html",
                title="Post A",
            ),
            _make_post("post-b", "Content B", "/b.html", title="Post B"),
        ]
        graph = build_graph_data(posts)
        post_to_post = [
            link
            for link in graph.links
            if link["source"] == "/a.html" and link["target"] == "/b.html"
        ]
        assert len(post_to_post) == 1

    def test_self_link_ignored(self) -> None:
        """A post that links to itself does not produce a self-referential edge."""
        posts = [
            _make_post(
                "post-a",
                "See [myself](/a.html).",
                "/a.html",
                title="Post A",
            ),
        ]
        graph = build_graph_data(posts)
        post_to_post = [
            link
            for link in graph.links
            if link["source"] == "/a.html" and link["target"] == "/a.html"
        ]
        assert len(post_to_post) == 0

    def test_duplicate_internal_links_produce_single_edge(self) -> None:
        """Multiple identical links between posts produce only one edge."""
        posts = [
            _make_post(
                "post-a",
                "See [B](/b.html) and again [B](/b.html).",
                "/a.html",
            ),
            _make_post("post-b", "Content B", "/b.html"),
        ]
        graph = build_graph_data(posts)
        edges = [
            link
            for link in graph.links
            if link["source"] == "/a.html" and link["target"] == "/b.html"
        ]
        assert len(edges) == 1

    def test_external_links_not_added(self) -> None:
        """External links in post content do not produce edges."""
        posts = [
            _make_post(
                "post-a",
                "Visit [GitHub](https://github.com).",
                "/a.html",
            ),
        ]
        graph = build_graph_data(posts)
        # Only the post node itself; no tag/category/post-to-post edges.
        assert len(graph.links) == 0

    def test_tag_url_uses_tag_dir(self) -> None:
        """Tag node URLs use the configured tag_dir."""
        posts = [_make_post("post-a", "Content", "/a.html", tags=["python"])]
        graph = build_graph_data(posts, tag_dir="tags")
        tag_node = next(n for n in graph.nodes if n["type"] == "tag")
        assert tag_node["url"] == "/tags/python/"

    def test_category_url_uses_category_dir(self) -> None:
        """Category node URLs use the configured category_dir."""
        posts = [_make_post("post-a", "Content", "/a.html", category="Tech")]
        graph = build_graph_data(posts, category_dir="categories")
        cat_node = next(n for n in graph.nodes if n["type"] == "category")
        assert cat_node["url"] == "/categories/tech/"

    def test_clean_url_link_resolved(self) -> None:
        """A post whose URL uses clean-URL form is still found as a link target."""
        posts = [
            _make_post(
                "post-a",
                "See [B](/b/).",
                "/a.html",
                title="Post A",
            ),
            _make_post("post-b", "Content B", "/b/index.html", title="Post B"),
        ]
        graph = build_graph_data(posts)
        # /b/ normalises to /b, and /b/index.html also normalises to /b — they match.
        post_to_post = [
            link
            for link in graph.links
            if link["source"] == "/a.html" and link["target"] == "/b/index.html"
        ]
        assert len(post_to_post) == 1

    def test_post_without_tags_no_tag_edges(self) -> None:
        """A post with no tags produces no tag edges."""
        posts = [_make_post("post-a", "Content", "/a.html")]
        graph = build_graph_data(posts)
        tag_edges = [link for link in graph.links if "tag:" in link.get("target", "")]
        assert len(tag_edges) == 0

    def test_post_without_category_no_category_edge(self) -> None:
        """A post with no category produces no category edge."""
        posts = [_make_post("post-a", "Content", "/a.html")]
        graph = build_graph_data(posts)
        cat_edges = [
            link for link in graph.links if "category:" in link.get("target", "")
        ]
        assert len(cat_edges) == 0

    def test_node_fields_complete(self) -> None:
        """Every node has the required id, label, type, and url fields."""
        posts = [
            _make_post("post-a", "Content", "/a.html", title="Post A", tags=["t"]),
        ]
        graph = build_graph_data(posts)
        for node in graph.nodes:
            assert "id" in node
            assert "label" in node
            assert "type" in node
            assert "url" in node

    def test_link_fields_complete(self) -> None:
        """Every link has the required source and target fields."""
        posts = [
            _make_post("post-a", "Content", "/a.html", tags=["t"], category="Cat"),
        ]
        graph = build_graph_data(posts)
        for link in graph.links:
            assert "source" in link
            assert "target" in link


### test_graph.py ends here
