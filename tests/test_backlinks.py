"""Tests for the backlinks module."""

##############################################################################
# Python imports.
import datetime as dt
import re
from pathlib import Path

##############################################################################
# Third-party imports.
from markupsafe import Markup

##############################################################################
# Application imports.
from blogmore.backlinks import (
    Backlink,
    _extract_snippet,
    _find_links,
    _normalize_url_path,
    _to_path,
    build_backlink_map,
)
from blogmore.parser import Post

##############################################################################
# Helpers.


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
    post = Post(
        path=Path(f"{slug}.md"),
        title=title,
        content=content,
        html_content=f"<p>{content}</p>",
        date=date,
    )
    post.url_path = url_path
    return post


##############################################################################
# _extract_snippet block-level Markdown stripping tests.
# (These verify that block-level Markdown syntax is cleaned from snippets.
# Unit tests for the shared markdown_to_plain_text utility live in
# tests/test_plain_text.py.)


class TestExtractSnippetBlockStripping:
    """Verify that block-level Markdown is cleaned from backlink snippets."""

    def test_blockquote_syntax_not_in_snippet(self) -> None:
        """A blockquote `>` marker is stripped from the snippet."""
        content = "Before [link](/post.html) after.\n\n> This is a blockquote."
        m = re.search(r"\[link\]\(/post\.html\)", content)
        assert m is not None
        snippet = _extract_snippet(content, m.start(), m.end())
        assert ">" not in snippet

    def test_fenced_code_backticks_not_in_snippet(self) -> None:
        """Fenced code block delimiters (```) are stripped from the snippet."""
        content = "See [link](/post.html).\n\n```python\nprint('hi')\n```\n"
        m = re.search(r"\[link\]\(/post\.html\)", content)
        assert m is not None
        snippet = _extract_snippet(content, m.start(), m.end())
        assert "```" not in snippet

    def test_heading_hash_not_in_snippet(self) -> None:
        """ATX heading `#` markers are stripped from the snippet context."""
        content = "## Introduction\n\nSee [link](/post.html) for more."
        m = re.search(r"\[link\]\(/post\.html\)", content)
        assert m is not None
        snippet = _extract_snippet(content, m.start(), m.end())
        assert "#" not in snippet

    def test_fenced_code_block_opening_before_window_not_in_snippet(self) -> None:
        """A fenced code block whose opening fence is outside the window is still cleaned.

        This is the core regression case: the code block starts well before the
        link, so only its body and closing fence fall inside a simple substring
        window.  By converting the full document we parse the fence in context
        and the snippet contains no raw backtick fence markers.
        """
        preamble = "Some intro text.\n\n"
        code_block = "```diff\n--- a/expando.el\n+++ b/expando.el\n```\n\n"
        link_sentence = "After the code block, see [the link](/post.html) here."
        content = preamble + code_block + link_sentence
        m = re.search(r"\[the link\]\(/post\.html\)", content)
        assert m is not None
        snippet = _extract_snippet(content, m.start(), m.end(), "the link")
        # The raw fenced-code fence markers must not appear in the snippet.
        assert "```" not in snippet
        assert "```diff" not in snippet


##############################################################################
# _find_links tests.


class TestFindLinks:
    """Tests for _find_links."""

    def test_no_links(self) -> None:
        """Content with no links returns an empty list."""
        assert _find_links("Just some plain text.") == []

    def test_inline_link(self) -> None:
        """A single inline link is found with the correct URL."""
        links = _find_links("See [my post](/2024/01/post.html) for details.")
        assert len(links) == 1
        url, start, end, link_text = links[0]
        assert url == "/2024/01/post.html"
        assert start < end
        assert link_text == "my post"

    def test_inline_link_with_title(self) -> None:
        """An inline link with a title attribute returns only the URL."""
        links = _find_links('[text](/foo.html "My Title")')
        assert len(links) == 1
        assert links[0][0] == "/foo.html"

    def test_multiple_inline_links(self) -> None:
        """Multiple inline links are all detected."""
        content = "See [A](/a.html) and [B](/b.html)."
        links = _find_links(content)
        urls = [url for url, _, _, _ in links]
        assert "/a.html" in urls
        assert "/b.html" in urls

    def test_reference_style_link(self) -> None:
        """A reference-style link is resolved to its URL."""
        content = "See [my post][ref].\n\n[ref]: /2024/01/post.html"
        links = _find_links(content)
        assert any(url == "/2024/01/post.html" for url, _, _, _ in links)

    def test_implicit_reference_link(self) -> None:
        """A [text][] implicit reference link is resolved using the text as the ID."""
        content = "See [my post][].\n\n[my post]: /2024/01/post.html"
        links = _find_links(content)
        assert any(url == "/2024/01/post.html" for url, _, _, _ in links)

    def test_match_positions_span_full_syntax(self) -> None:
        """start/end positions span the full [text](url) syntax."""
        content = "pre [text](/url) post"
        links = _find_links(content)
        assert len(links) == 1
        _, start, end, _ = links[0]
        assert content[start:end] == "[text](/url)"

    def test_inline_link_url_with_parentheses(self) -> None:
        """A URL containing parentheses is captured in full."""
        links = _find_links(
            "[photoblogging](/2016/11/15/seen_by_davep_(the_return).html)."
        )
        assert len(links) == 1
        url, _, _, link_text = links[0]
        assert url == "/2016/11/15/seen_by_davep_(the_return).html"
        assert link_text == "photoblogging"

    def test_inline_link_url_with_parentheses_and_title(self) -> None:
        """A URL containing parentheses followed by a title is parsed correctly."""
        links = _find_links('[text](/path_(foo).html "My Title")')
        assert len(links) == 1
        url, _, _, _ = links[0]
        assert url == "/path_(foo).html"


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
        content = "Hello [world](/foo.html) end."
        m = re.search(r"\[world\]\(/foo\.html\)", content)
        assert m is not None
        snippet = _extract_snippet(content, m.start(), m.end(), "world")
        # No ellipsis — content is short.
        assert "Hello" in snippet
        assert "world" in snippet
        assert "end." in snippet

    def test_long_prefix_adds_ellipsis(self) -> None:
        """A snippet whose prefix exceeds 100 chars gets a leading ellipsis."""
        prefix = "x" * 200
        content = f"{prefix} [link](/foo.html) end"
        m = re.search(r"\[link\]\(/foo\.html\)", content)
        assert m is not None
        snippet = _extract_snippet(content, m.start(), m.end())
        assert snippet.startswith("…")

    def test_long_suffix_adds_ellipsis(self) -> None:
        """A snippet whose suffix exceeds 100 chars gets a trailing ellipsis."""
        suffix = "y" * 200
        content = f"start [link](/foo.html) {suffix}"
        m = re.search(r"\[link\]\(/foo\.html\)", content)
        assert m is not None
        snippet = _extract_snippet(content, m.start(), m.end())
        assert snippet.endswith("…")

    def test_link_text_appears_in_snippet(self) -> None:
        """The link text (not the URL) appears in the snippet."""
        content = "See [interesting article](/post.html) for more."
        m = re.search(r"\[interesting article\]\(/post\.html\)", content)
        assert m is not None
        snippet = _extract_snippet(content, m.start(), m.end(), "interesting article")
        assert "interesting article" in snippet
        assert "/post.html" not in snippet

    def test_link_text_highlighted_when_provided(self) -> None:
        """When link_text is supplied, the stripped form is wrapped in <strong>."""
        content = "See [the article](/post.html) for more."
        m = re.search(r"\[the article\]\(/post\.html\)", content)
        assert m is not None
        snippet = _extract_snippet(content, m.start(), m.end(), "the article")
        assert isinstance(snippet, Markup)
        assert '<strong class="backlink-link-text">the article</strong>' in snippet

    def test_link_text_not_highlighted_in_containing_word(self) -> None:
        """The link text is highlighted at its exact position, not inside a longer word.

        Regression test for the Scunthorpe-style false positive: when the link
        text ("more") also appears as a substring of a nearby word ("blogmore"),
        only the standalone occurrence that corresponds to the actual link must
        be wrapped in <strong>, not the first occurrence found by substring
        search.
        """
        content = (
            "After kicking off [blogmore.el](/other.html), and then tinkering "
            "with it [more](/2026/03/20/post.html) and more."
        )
        m = re.search(r"\[more\]\(/2026/03/20/post\.html\)", content)
        assert m is not None
        snippet = _extract_snippet(content, m.start(), m.end(), "more")
        assert isinstance(snippet, Markup)
        # The highlighted <strong> must wrap the standalone "more" that was the
        # link text, not the "more" embedded inside "blogmore.el".
        strong_tag = '<strong class="backlink-link-text">more</strong>'
        assert strong_tag in snippet
        # The preceding text "blog" must NOT be immediately followed by the
        # strong tag (which would mean the "more" in "blogmore" was highlighted).
        assert f"blog{strong_tag}" not in snippet

    def test_snippet_is_markup_instance(self) -> None:
        """_extract_snippet always returns a Markup instance."""
        content = "Hello [world](/foo.html) end."
        m = re.search(r"\[world\]\(/foo\.html\)", content)
        assert m is not None
        snippet = _extract_snippet(content, m.start(), m.end())
        assert isinstance(snippet, Markup)


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

    def test_multiple_posts_linking_to_same_target(self) -> None:
        """Multiple posts linking to the same post all appear in that post's backlinks."""
        target = _make_post("t", "Target content.", "/2024/01/t.html", title="Target")
        post_a = _make_post(
            "a", "See [t](/2024/01/t.html).", "/2024/01/a.html", title="A"
        )
        post_b = _make_post(
            "b", "Also [t](/2024/01/t.html).", "/2024/01/b.html", title="B"
        )
        result = build_backlink_map([target, post_a, post_b])

        sources = [bl.source_post for bl in result["/2024/01/t.html"]]
        assert post_a in sources
        assert post_b in sources

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
        # Post B has a regular .html URL.
        post_b = _make_post("b", "B content.", "/2024/01/b.html", title="B")
        # Post A links using the clean URL form.
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

    def test_snippet_contains_context_around_link(self) -> None:
        """The Backlink snippet includes plain-text context around the link."""
        post_b = _make_post("b", "B content.", "/2024/01/b.html", title="B")
        post_a = _make_post(
            "a",
            "Some context before [the linked post](/2024/01/b.html) and some after.",
            "/2024/01/a.html",
            title="A",
        )
        result = build_backlink_map([post_a, post_b])
        snippet = result["/2024/01/b.html"][0].snippet
        assert "the linked post" in snippet
        assert "/2024/01/b.html" not in snippet

    def test_page_links_not_included(self) -> None:
        """Links to URLs that don't match any post are not included."""
        post_a = _make_post(
            "a",
            "See [about](/about.html) page.",
            "/2024/01/a.html",
        )
        post_b = _make_post("b", "B content.", "/2024/01/b.html")
        # /about.html is not in the posts list — it's a static page.
        result = build_backlink_map([post_a, post_b])
        # No backlinks recorded (about is not a post URL in this list).
        assert result["/2024/01/a.html"] == []
        assert result["/2024/01/b.html"] == []

    def test_every_post_has_entry_in_map(self) -> None:
        """Every post appears as a key in the returned map, even with no backlinks."""
        posts = [
            _make_post("a", "Content.", "/2024/01/a.html"),
            _make_post("b", "Content.", "/2024/01/b.html"),
            _make_post("c", "Content.", "/2024/01/c.html"),
        ]
        result = build_backlink_map(posts)
        for each_post in posts:
            assert each_post.url in result

    def test_backlink_detected_for_url_with_parentheses(self) -> None:
        """A link whose URL contains parentheses creates the correct backlink.

        Regression test: a URL such as /2016/11/15/seen_by_davep_(the_return).html
        was previously truncated by the inline-link regex, causing the backlink
        to be silently dropped.
        """
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
