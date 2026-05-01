"""Tests for the pagination_path module."""

##############################################################################
# Python imports.
import re

##############################################################################
# Third-party imports.
import pytest

##############################################################################
# Application imports.
from blogmore.pagination_path import (
    DEFAULT_PAGE_1_PATH,
    DEFAULT_PAGE_N_PATH,
    resolve_pagination_page_path,
    validate_page_1_path_template,
    validate_page_n_path_template,
)

##############################################################################
# Tests for module-level constants.


class TestDefaults:
    """Tests for the default constant values."""

    def test_default_page_1_path(self) -> None:
        """The default page_1_path should be 'index.html'."""
        assert DEFAULT_PAGE_1_PATH == "index.html"

    def test_default_page_n_path(self) -> None:
        """The default page_n_path should be 'page/{page}.html'."""
        assert DEFAULT_PAGE_N_PATH == "page/{page}.html"


##############################################################################
# Tests for validate_page_1_path_template.


class TestValidatePage1PathTemplate:
    """Tests for validate_page_1_path_template."""

    def test_valid_simple_path(self) -> None:
        """A simple filename with no placeholders is valid."""
        assert validate_page_1_path_template("index.html") is None

    def test_valid_path_with_subdirectory(self) -> None:
        """A path with subdirectories is valid."""
        assert validate_page_1_path_template("pages/index.html") is None

    def test_valid_path_with_page_placeholder(self) -> None:
        """The {page} placeholder is allowed in page_1_path."""
        assert validate_page_1_path_template("page-{page}.html") is None

    def test_empty_template_raises(self) -> None:
        """An empty template raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            validate_page_1_path_template("")

    def test_unknown_variable_raises(self) -> None:
        """An unknown variable placeholder raises ValueError."""
        with pytest.raises(ValueError, match="unknown variable"):
            validate_page_1_path_template("{slug}.html")

    def test_multiple_unknown_variables_raises(self) -> None:
        """Multiple unknown variables are reported in the error message."""
        with pytest.raises(ValueError, match="unknown variable"):
            validate_page_1_path_template("{year}/{month}/index.html")


##############################################################################
# Tests for validate_page_n_path_template.


class TestValidatePageNPathTemplate:
    """Tests for validate_page_n_path_template."""

    def test_valid_path_with_page_placeholder(self) -> None:
        """A path containing {page} is valid."""
        assert validate_page_n_path_template("page/{page}.html") is None

    def test_valid_subdirectory_path_with_page(self) -> None:
        """A path with a subdirectory and {page} is valid."""
        assert validate_page_n_path_template("p/{page}/index.html") is None

    def test_empty_template_raises(self) -> None:
        """An empty template raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            validate_page_n_path_template("")

    def test_missing_page_placeholder_raises(self) -> None:
        """A template with no {page} placeholder raises ValueError."""
        with pytest.raises(
            ValueError,
            match=re.escape(
                "page_n_path 'pages.html' is missing required variable(s): {page}"
            ),
        ):
            validate_page_n_path_template("pages.html")

    def test_unknown_variable_raises(self) -> None:
        """An unknown variable placeholder raises ValueError."""
        with pytest.raises(ValueError, match="unknown variable"):
            validate_page_n_path_template("{page}/{slug}.html")


##############################################################################
# Tests for resolve_pagination_page_path.


class TestResolvePaginationPagePath:
    """Tests for resolve_pagination_page_path."""

    def test_default_page_1_path_resolves_without_substitution(self) -> None:
        """The default page_1_path resolves unchanged for page 1."""
        result = resolve_pagination_page_path(DEFAULT_PAGE_1_PATH, 1)
        assert result == "index.html"

    def test_default_page_n_path_resolves_page_2(self) -> None:
        """The default page_n_path resolves correctly for page 2."""
        result = resolve_pagination_page_path(DEFAULT_PAGE_N_PATH, 2)
        assert result == "page/2.html"

    def test_default_page_n_path_resolves_page_5(self) -> None:
        """The default page_n_path resolves correctly for page 5."""
        result = resolve_pagination_page_path(DEFAULT_PAGE_N_PATH, 5)
        assert result == "page/5.html"

    def test_leading_slash_is_stripped(self) -> None:
        """Leading slashes are stripped from the resolved path."""
        result = resolve_pagination_page_path("/page/{page}.html", 3)
        assert result == "page/3.html"

    def test_double_slashes_are_collapsed(self) -> None:
        """Double slashes in the template are collapsed to a single slash."""
        result = resolve_pagination_page_path("pages//{page}.html", 2)
        assert result == "pages/2.html"

    def test_simple_template_without_page(self) -> None:
        """A template without {page} resolves to the literal string."""
        result = resolve_pagination_page_path("start.html", 1)
        assert result == "start.html"

    def test_page_number_substituted_correctly(self) -> None:
        """The {page} placeholder is replaced with the given page number."""
        result = resolve_pagination_page_path("p{page}/index.html", 7)
        assert result == "p7/index.html"


### test_pagination_path.py ends here
