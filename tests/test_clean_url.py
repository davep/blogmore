"""Tests for the clean_url module."""

##############################################################################
# Third-party imports.
import pytest

##############################################################################
# Application imports.
from blogmore.clean_url import CLEAN_URL_INDEX_FILES, make_url_clean


##############################################################################
# CLEAN_URL_INDEX_FILES tests.


class TestCleanUrlIndexFiles:
    """Tests for the CLEAN_URL_INDEX_FILES constant."""

    def test_contains_index_html(self) -> None:
        """CLEAN_URL_INDEX_FILES includes 'index.html'."""
        assert "index.html" in CLEAN_URL_INDEX_FILES

    def test_contains_index_htm(self) -> None:
        """CLEAN_URL_INDEX_FILES includes 'index.htm'."""
        assert "index.htm" in CLEAN_URL_INDEX_FILES

    def test_is_frozenset(self) -> None:
        """CLEAN_URL_INDEX_FILES is a frozenset."""
        assert isinstance(CLEAN_URL_INDEX_FILES, frozenset)


##############################################################################
# make_url_clean tests.


class TestMakeUrlClean:
    """Tests for make_url_clean."""

    def test_strips_bare_index_html(self) -> None:
        """A bare 'index.html' with no leading slash has the filename removed."""
        assert make_url_clean("index.html") == ""

    def test_strips_bare_index_htm(self) -> None:
        """A bare 'index.htm' with no leading slash has the filename removed."""
        assert make_url_clean("index.htm") == ""

    # ------------------------------------------------------------------
    # Standard cases: index filename IS the sole path component
    # ------------------------------------------------------------------

    def test_strips_index_html_after_slash(self) -> None:
        """A URL ending with /index.html has the filename removed."""
        assert make_url_clean("/posts/my-post/index.html") == "/posts/my-post/"

    def test_strips_index_htm_after_slash(self) -> None:
        """A URL ending with /index.htm has the filename removed."""
        assert make_url_clean("/posts/my-post/index.htm") == "/posts/my-post/"

    def test_strips_root_index_html(self) -> None:
        """The root index file /index.html is stripped to /."""
        assert make_url_clean("/index.html") == "/"

    def test_strips_root_index_htm(self) -> None:
        """The root index file /index.htm is stripped to /."""
        assert make_url_clean("/index.htm") == "/"

    def test_strips_deeply_nested_index_html(self) -> None:
        """A deeply nested index.html URL is stripped correctly."""
        assert (
            make_url_clean("/a/b/c/d/index.html") == "/a/b/c/d/"
        )

    def test_strips_single_segment_index_html(self) -> None:
        """A single-segment path ending in /index.html is stripped."""
        assert make_url_clean("/posts/index.html") == "/posts/"

    # ------------------------------------------------------------------
    # Non-stripping cases: index filename is a *suffix* of a longer name
    # ------------------------------------------------------------------

    def test_does_not_strip_search_index_html(self) -> None:
        """A URL ending with search-index.html is returned unchanged."""
        assert make_url_clean("/search-index.html") == "/search-index.html"

    def test_does_not_strip_my_index_html(self) -> None:
        """A URL ending with my-index.html is returned unchanged."""
        assert make_url_clean("/my-index.html") == "/my-index.html"

    def test_does_not_strip_long_prefix_index_html(self) -> None:
        """A filename that ends in index.html but is not exactly index.html is unchanged."""
        assert (
            make_url_clean("/posts/page-index.html") == "/posts/page-index.html"
        )

    def test_does_not_strip_search_index_htm(self) -> None:
        """A URL ending with search-index.htm is returned unchanged."""
        assert make_url_clean("/search-index.htm") == "/search-index.htm"

    def test_does_not_strip_my_index_htm(self) -> None:
        """A filename that ends in index.htm but is not exactly index.htm is unchanged."""
        assert make_url_clean("/my-index.htm") == "/my-index.htm"

    # ------------------------------------------------------------------
    # No-op cases: URL does not end with any index filename
    # ------------------------------------------------------------------

    def test_leaves_non_index_html_unchanged(self) -> None:
        """A URL ending with a non-index HTML file is returned unchanged."""
        assert make_url_clean("/posts/my-post.html") == "/posts/my-post.html"

    def test_leaves_already_clean_url_unchanged(self) -> None:
        """A URL already ending with a trailing slash is returned unchanged."""
        assert make_url_clean("/posts/my-post/") == "/posts/my-post/"

    def test_leaves_non_html_url_unchanged(self) -> None:
        """A URL for a non-HTML asset (e.g. .xml) is returned unchanged."""
        assert make_url_clean("/sitemap.xml") == "/sitemap.xml"

    def test_leaves_empty_string_unchanged(self) -> None:
        """An empty string is returned unchanged."""
        assert make_url_clean("") == ""

    def test_leaves_root_slash_unchanged(self) -> None:
        """The root URL '/' is returned unchanged."""
        assert make_url_clean("/") == "/"

    # ------------------------------------------------------------------
    # my-index.html vs my/index.html — the core correctness contrast
    # ------------------------------------------------------------------

    def test_directory_index_html_is_stripped(self) -> None:
        """my/index.html (index as sole filename) has the filename stripped."""
        assert make_url_clean("/my/index.html") == "/my/"

    def test_prefixed_index_html_is_not_stripped(self) -> None:
        """my-index.html (index as suffix) is NOT stripped."""
        assert make_url_clean("/my-index.html") == "/my-index.html"

    def test_directory_index_htm_is_stripped(self) -> None:
        """my/index.htm (index as sole filename) has the filename stripped."""
        assert make_url_clean("/my/index.htm") == "/my/"

    def test_prefixed_index_htm_is_not_stripped(self) -> None:
        """my-index.htm (index as suffix) is NOT stripped."""
        assert make_url_clean("/my-index.htm") == "/my-index.htm"


### test_clean_url.py ends here
