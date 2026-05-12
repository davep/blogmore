"""Tests for the backlinks module."""

##############################################################################
# Python imports.
import datetime as dt
import re
import time
from pathlib import Path

##############################################################################
# Third-party imports.
from markupsafe import Markup

##############################################################################
# Application imports.
from blogmore.backlinks import (
    Backlink,
    _extract_snippets,
    _find_links,
    _normalize_url_path,
    _to_path,
    build_backlink_map,
)
from blogmore.parser import Post, PostParser

##############################################################################
# Helpers.

_parser = PostParser()


def _extract_single_snippet(
    html_content: str, start: int, end: int, link_text: str = ""
) -> Markup:
    """Helper to test extraction for a single link using the new _extract_snippets logic."""
    # Create a dummy target post for the internal call
    dummy_post = _make_post("dummy", "", "/dummy.html")
    results = _extract_snippets(html_content, [(start, end, link_text, dummy_post)])
    return results[0][1] if results else Markup("")


def _make_post(
    slug: str,
    content: str,
    url_path: str,
    title: str = "Test Post",
    date: dt.datetime | None = None,
) -> Post:
    """Create a minimal Post fixture with the given slug and URL path.

    Args:
        slug: Used to build a unique file path.
        content: Raw Markdown content.
        url_path: The URL path to assign (mimics generator output).
        title: Optional title override.
        date: Optional publication date.

    Returns:
        A Post object suitable for backlink tests.
    """
    html_content = _parser.markdown.convert(content)
    post = Post(
        path=Path(f"{slug}.md"),
        title=title,
        content=content,
        html_content=html_content,
        date=date,
    )
    post.url_path = url_path
    return post


##############################################################################
# _extract_snippet block-level HTML stripping tests.


class TestExtractSnippetBlockStripping:
    """Verify that block-level HTML is cleaned from backlink snippets."""

    def test_blockquote_syntax_not_in_snippet(self) -> None:
        """A blockquote tag is stripped from the snippet."""
        html = '<p>Before <a href="/post.html">link</a> after.</p><blockquote>This is some text.</blockquote>'
        m = re.search(r'<a href="/post\.html">link</a>', html)
        assert m is not None
        snippet = _extract_single_snippet(html, m.start(), m.end())
        assert "blockquote" not in snippet

    def test_fenced_code_not_in_snippet(self) -> None:
        """Code block tags are stripped from the snippet."""
        html = "<p>See <a href=\"/post.html\">link</a>.</p><pre><code>print('hi')</code></pre>"
        m = re.search(r'<a href="/post\.html">link</a>', html)
        assert m is not None
        snippet = _extract_single_snippet(html, m.start(), m.end())
        assert "<pre>" not in snippet
        assert "<code>" not in snippet

    def test_heading_not_in_snippet(self) -> None:
        """Heading tags are stripped from the snippet context."""
        html = '<h2>Introduction</h2><p>See <a href="/post.html">link</a> for more.</p>'
        m = re.search(r'<a href="/post\.html">link</a>', html)
        assert m is not None
        snippet = _extract_single_snippet(html, m.start(), m.end())
        assert "h2" not in snippet

    def test_code_block_opening_before_window_not_in_snippet(self) -> None:
        """A code block whose opening tag is outside the window is still cleaned."""
        preamble = "<p>Some intro text.</p>"
        code_block = "<pre><code>--- a/expando.el\n+++ b/expando.el</code></pre>"
        link_sentence = (
            '<p>After the code block, see <a href="/post.html">the link</a> here.</p>'
        )
        html = preamble + code_block + link_sentence
        m = re.search(r'<a href="/post\.html">the link</a>', html)
        assert m is not None
        snippet = _extract_single_snippet(html, m.start(), m.end(), "the link")
        # The HTML tags must not appear in the snippet.
        assert "<pre>" not in snippet
        assert "<code>" not in snippet


##############################################################################
# _find_links tests.


class TestFindLinks:
    """Tests for _find_links."""

    def test_no_links(self) -> None:
        """Content with no links returns an empty list."""
        assert _find_links("<p>Just some plain text.</p>") == []

    def test_html_link(self) -> None:
        """A single HTML link is found with the correct URL."""
        links = _find_links(
            '<p>See <a href="/2024/01/post.html">my post</a> for details.</p>'
        )
        assert len(links) == 1
        url, start, end, link_text = links[0]
        assert url == "/2024/01/post.html"
        assert start < end
        assert link_text == "my post"

    def test_html_link_with_attributes(self) -> None:
        """An HTML link with extra attributes returns only the URL."""
        links = _find_links('<a class="foo" href="/foo.html" id="bar">text</a>')
        assert len(links) == 1
        assert links[0][0] == "/foo.html"
        assert links[0][3] == "text"

    def test_multiple_html_links(self) -> None:
        """Multiple HTML links are all detected."""
        html = '<p>See <a href="/a.html">A</a> and <a href="/b.html">B</a>.</p>'
        links = _find_links(html)
        urls = [url for url, _, _, _ in links]
        assert "/a.html" in urls
        assert "/b.html" in urls

    def test_match_positions_span_full_syntax(self) -> None:
        """start/end positions span the full <a> tag syntax."""
        html = 'pre <a href="/url">text</a> post'
        links = _find_links(html)
        assert len(links) == 1
        _, start, end, _ = links[0]
        assert html[start:end] == '<a href="/url">text</a>'

    def test_url_with_parentheses(self) -> None:
        """A URL containing parentheses is captured in full."""
        html = '<a href="/2016/11/15/seen_by_davep_(the_return).html">photoblogging</a>'
        links = _find_links(html)
        assert len(links) == 1
        url, _, _, link_text = links[0]
        assert url == "/2016/11/15/seen_by_davep_(the_return).html"
        assert link_text == "photoblogging"


##############################################################################
# _normalize_url_path tests.


class TestNormalizeUrlPath:
    """Tests for _normalize_url_path."""

    def test_strips_html_extension(self) -> None:
        """A .html extension is removed."""
        assert _normalize_url_path("/2024/01/post.html") == "/2024/01/post"

    def test_strips_trailing_slash(self) -> None:
        """A trailing slash is removed."""
        assert _normalize_url_path("/2024/01/post/") == "/2024/01/post"

    def test_strips_index_html(self) -> None:
        """/index.html at the end is removed entirely."""
        assert _normalize_url_path("/2024/01/post/index.html") == "/2024/01/post"

    def test_plain_path_unchanged(self) -> None:
        """A path with no extension or trailing slash is unchanged."""
        assert _normalize_url_path("/2024/01/post") == "/2024/01/post"

    def test_matching_regular_and_clean_url(self) -> None:
        """Both URL forms for the same post normalise to the same string."""
        regular = _normalize_url_path("/2024/01/post.html")
        clean = _normalize_url_path("/2024/01/post/")
        assert regular == clean


##############################################################################
# _to_path tests.


class TestToPath:
    """Tests for _to_path."""

    def test_absolute_path(self) -> None:
        """An absolute root-relative path is returned unchanged."""
        assert _to_path("/2024/01/post.html", "") == "/2024/01/post.html"

    def test_fragment_only_returns_none(self) -> None:
        """A fragment-only link (#section) returns None."""
        assert _to_path("#section", "") is None

    def test_empty_url_returns_none(self) -> None:
        """An empty URL returns None."""
        assert _to_path("", "") is None

    def test_external_url_no_site_url(self) -> None:
        """An external URL with no site_url configured returns None."""
        assert _to_path("https://example.com/post.html", "") is None

    def test_full_url_matching_site_url(self) -> None:
        """A full URL matching site_url is converted to a root-relative path."""
        result = _to_path(
            "https://example.com/2024/01/post.html", "https://example.com"
        )
        assert result == "/2024/01/post.html"

    def test_full_url_not_matching_site_url(self) -> None:
        """A full URL not matching site_url returns None."""
        assert _to_path("https://other.com/post.html", "https://example.com") is None

    def test_relative_path_returns_none(self) -> None:
        """A relative path (../foo) returns None (too ambiguous)."""
        assert _to_path("../2024/post.html", "") is None

    def test_fragment_stripped_from_path(self) -> None:
        """Fragment is stripped before returning the path."""
        assert _to_path("/2024/01/post.html#section", "") == "/2024/01/post.html"

    def test_query_stripped_from_path(self) -> None:
        """Query string is stripped before returning the path."""
        assert _to_path("/2024/01/post.html?ref=feed", "") == "/2024/01/post.html"


##############################################################################
# _extract_snippet tests.


class TestExtractSnippet:
    """Tests for _extract_snippet."""

    def test_short_content_no_ellipsis(self) -> None:
        """A snippet from short content has no ellipsis when not truncated."""
        html = '<p>Hello <a href="/foo.html">world</a> end.</p>'
        m = re.search(r'<a href="/foo\.html">world</a>', html)
        assert m is not None
        snippet = _extract_single_snippet(html, m.start(), m.end(), "world")
        # No ellipsis — content is short.
        assert "Hello" in snippet
        assert "world" in snippet
        assert "end." in snippet

    def test_long_prefix_adds_ellipsis(self) -> None:
        """A snippet whose prefix exceeds 100 chars gets a leading ellipsis."""
        prefix = "x" * 200
        html = f'<p>{prefix} <a href="/foo.html">link</a> end</p>'
        m = re.search(r'<a href="/foo\.html">link</a>', html)
        assert m is not None
        snippet = _extract_single_snippet(html, m.start(), m.end())
        assert snippet.startswith("…")

    def test_long_suffix_adds_ellipsis(self) -> None:
        """A snippet whose suffix exceeds 100 chars gets a trailing ellipsis."""
        suffix = "y" * 200
        html = f'<p>start <a href="/foo.html">link</a> {suffix}</p>'
        m = re.search(r'<a href="/foo\.html">link</a>', html)
        assert m is not None
        snippet = _extract_single_snippet(html, m.start(), m.end())
        assert snippet.endswith("…")

    def test_link_text_appears_in_snippet(self) -> None:
        """The link text (not the URL) appears in the snippet."""
        html = '<p>See <a href="/post.html">interesting article</a> for more.</p>'
        m = re.search(r'<a href="/post\.html">interesting article</a>', html)
        assert m is not None
        snippet = _extract_single_snippet(
            html, m.start(), m.end(), "interesting article"
        )
        assert "interesting article" in snippet
        assert "/post.html" not in snippet

    def test_link_text_highlighted_when_provided(self) -> None:
        """When link_text is supplied, the stripped form is wrapped in <strong>."""
        html = '<p>See <a href="/post.html">the article</a> for more.</p>'
        m = re.search(r'<a href="/post\.html">the article</a>', html)
        assert m is not None
        snippet = _extract_single_snippet(html, m.start(), m.end(), "the article")
        assert isinstance(snippet, Markup)
        assert '<strong class="backlink-link-text">the article</strong>' in snippet

    def test_link_text_not_highlighted_in_containing_word(self) -> None:
        """The link text is highlighted at its exact position, not inside a longer word."""
        html = (
            "<p>After kicking off blogmore.el, and then tinkering "
            'with it <a href="/2026/03/20/post.html">more</a> and more.</p>'
        )
        m = re.search(r'<a href="/2026/03/20/post\.html">more</a>', html)
        assert m is not None
        snippet = _extract_single_snippet(html, m.start(), m.end(), "more")
        assert isinstance(snippet, Markup)
        strong_tag = '<strong class="backlink-link-text">more</strong>'
        assert strong_tag in snippet
        assert f"blog{strong_tag}" not in snippet

    def test_snippet_is_markup_instance(self) -> None:
        """_extract_snippet always returns a Markup instance."""
        html = '<p>Hello <a href="/foo.html">world</a> end.</p>'
        m = re.search(r'<a href="/foo\.html">world</a>', html)
        assert m is not None
        snippet = _extract_single_snippet(html, m.start(), m.end())
        assert isinstance(snippet, Markup)

    def test_multiple_links_in_snippet_no_marker_leakage(self) -> None:
        """Other markers in a snippet window are replaced by their plain-text link text."""
        html = (
            '<p>First <a href="/1.html">Link 1</a> then <a href="/2.html">Link 2</a> '
            'then <a href="/3.html">Link 3</a> then more.</p>'
        )
        post1 = _make_post("post1", "Post 1", "/1.html")
        post2 = _make_post("post2", "Post 2", "/2.html")
        post3 = _make_post("post3", "Post 3", "/3.html")

        link1_m = re.search(r'<a href="/1\.html">Link 1</a>', html)
        link2_m = re.search(r'<a href="/2\.html">Link 2</a>', html)
        link3_m = re.search(r'<a href="/3\.html">Link 3</a>', html)
        assert link1_m and link2_m and link3_m

        link_data = [
            (link1_m.start(), link1_m.end(), "Link 1", post1),
            (link2_m.start(), link2_m.end(), "Link 2", post2),
            (link3_m.start(), link3_m.end(), "Link 3", post3),
        ]

        results = _extract_snippets(html, link_data)

        snippet2 = results[1][1]
        assert '<strong class="backlink-link-text">Link 2</strong>' in snippet2
        assert "Link 1" in snippet2
        assert "Link 3" in snippet2
        assert "BKLINK" not in str(snippet2)


##############################################################################
# build_backlink_map tests.


class TestBuildBacklinkMap:
    """Tests for build_backlink_map."""

    def test_empty_posts_returns_empty_map(self) -> None:
        """An empty post list returns an empty map."""
        result = build_backlink_map([])
        assert result == {}

    def test_single_post_no_internal_links(self) -> None:
        """A single post with no internal links has an empty backlinks list."""
        post = _make_post("a", "No links here.", "/2024/01/a.html")
        result = build_backlink_map([post])
        assert result == {"/2024/01/a.html": []}

    def test_self_link_excluded(self) -> None:
        """A post linking to itself does not appear in its own backlinks list."""
        post = _make_post("a", "See [myself](/2024/01/a.html).", "/2024/01/a.html")
        result = build_backlink_map([post])
        assert result["/2024/01/a.html"] == []

    def test_single_backlink_detected(self) -> None:
        """Post A linking to post B creates one Backlink entry for B."""
        post_a = _make_post(
            "a",
            "See [B's post](/2024/01/b.html) for details.",
            "/2024/01/a.html",
            title="Post A",
        )
        post_b = _make_post("b", "Post B content.", "/2024/01/b.html", title="Post B")
        result = build_backlink_map([post_a, post_b])

        assert len(result["/2024/01/b.html"]) == 1
        backlink = result["/2024/01/b.html"][0]
        assert isinstance(backlink, Backlink)
        assert backlink.source_post is post_a
        assert result["/2024/01/a.html"] == []

    def test_external_links_ignored(self) -> None:
        """Links to external sites are not treated as backlinks."""
        post_a = _make_post(
            "a",
            "See [external](https://example.com/other).",
            "/2024/01/a.html",
        )
        post_b = _make_post("b", "B content.", "/2024/01/b.html")
        result = build_backlink_map([post_a, post_b])
        assert result["/2024/01/b.html"] == []

    def test_clean_url_link_matches_regular_url(self) -> None:
        """A clean-URL link (/post/) matches a post with a .html URL."""
        post_b = _make_post("b", "B content.", "/2024/01/b.html", title="B")
        post_a = _make_post(
            "a",
            "See [B's post](/2024/01/b/) for details.",
            "/2024/01/a.html",
            title="A",
        )
        result = build_backlink_map([post_a, post_b])
        assert len(result["/2024/01/b.html"]) == 1
        assert result["/2024/01/b.html"][0].source_post is post_a

    def test_full_site_url_link_matched(self) -> None:
        """A link using the full site URL (https://…) is matched correctly."""
        post_b = _make_post("b", "B content.", "/2024/01/b.html", title="B")
        post_a = _make_post(
            "a",
            "See [B](https://example.com/2024/01/b.html).",
            "/2024/01/a.html",
            title="A",
        )
        result = build_backlink_map([post_a, post_b], site_url="https://example.com")
        assert len(result["/2024/01/b.html"]) == 1

    def test_backlink_detected_for_url_with_parentheses(self) -> None:
        """A link whose URL contains parentheses creates the correct backlink."""
        target = _make_post(
            "target",
            "Target post content.",
            "/2016/11/15/seen_by_davep_(the_return).html",
            title="Target",
        )
        source = _make_post(
            "source",
            "See [photoblogging](/2016/11/15/seen_by_davep_(the_return).html).",
            "/2017/03/08/source.html",
            title="Source",
        )
        result = build_backlink_map([target, source])
        backlinks = result["/2016/11/15/seen_by_davep_(the_return).html"]
        assert len(backlinks) == 1
        assert backlinks[0].source_post is source


### test_backlinks.py ends here
