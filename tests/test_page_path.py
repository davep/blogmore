"""Tests for the page_path module."""

##############################################################################
# Standard-library imports.
from pathlib import Path

##############################################################################
# Third-party imports.
import pytest

##############################################################################
# Application imports.
from blogmore.page_path import (
    ALLOWED_PAGE_PATH_VARIABLES,
    DEFAULT_PAGE_PATH,
    compute_page_output_path,
    resolve_page_path,
    validate_page_path_template,
)
from blogmore.parser import Page


##############################################################################
# Fixtures.


@pytest.fixture
def sample_page() -> Page:
    """Return a sample Page for testing."""
    return Page(
        path=Path("about.md"),
        title="About Me",
        content="About page content.",
        html_content="<p>About page content.</p>",
        metadata={"title": "About Me"},
    )


##############################################################################
# validate_page_path_template tests.


class TestValidatePagePathTemplate:
    """Tests for validate_page_path_template."""

    def test_default_template_is_valid(self) -> None:
        """The default template must pass validation without errors."""
        validate_page_path_template(DEFAULT_PAGE_PATH)

    def test_slug_only_template_is_valid(self) -> None:
        """A minimal template containing only {slug} is valid."""
        validate_page_path_template("{slug}.html")

    def test_nested_slug_template_is_valid(self) -> None:
        """A template nesting {slug} in a subdirectory is valid."""
        validate_page_path_template("pages/{slug}/index.html")

    def test_empty_template_raises(self) -> None:
        """An empty template string raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            validate_page_path_template("")

    def test_missing_slug_raises(self) -> None:
        """A template without {slug} raises ValueError."""
        with pytest.raises(ValueError, match=r"\{slug\}"):
            validate_page_path_template("pages/index.html")

    def test_unknown_variable_raises(self) -> None:
        """A template with an unknown variable name raises ValueError."""
        with pytest.raises(ValueError, match="unknown variable"):
            validate_page_path_template("{year}/{slug}.html")

    def test_multiple_unknown_variables_raises(self) -> None:
        """A template with multiple unknown variables raises ValueError."""
        with pytest.raises(ValueError, match="unknown variable"):
            validate_page_path_template("{category}/{author}/{slug}.html")

    def test_allowed_variables_constant_is_correct(self) -> None:
        """ALLOWED_PAGE_PATH_VARIABLES contains exactly the documented variable names."""
        assert ALLOWED_PAGE_PATH_VARIABLES == {"slug"}


##############################################################################
# resolve_page_path tests.


class TestResolvePagePath:
    """Tests for resolve_page_path."""

    def test_default_template(self, sample_page: Page) -> None:
        """Default template produces slug.html."""
        result = resolve_page_path(sample_page, DEFAULT_PAGE_PATH)
        assert result == "about.html"

    def test_nested_pages_directory(self, sample_page: Page) -> None:
        """A template with a subdirectory prefix resolves correctly."""
        result = resolve_page_path(sample_page, "pages/{slug}.html")
        assert result == "pages/about.html"

    def test_per_page_directory(self, sample_page: Page) -> None:
        """A template that puts each page in its own directory works."""
        result = resolve_page_path(sample_page, "{slug}/index.html")
        assert result == "about/index.html"

    def test_pages_subdirectory_with_index(self, sample_page: Page) -> None:
        """A template combining subdirectory and per-page directory works."""
        result = resolve_page_path(sample_page, "pages/{slug}/index.html")
        assert result == "pages/about/index.html"

    def test_leading_slash_removed(self, sample_page: Page) -> None:
        """A template beginning with / produces a result without a leading slash."""
        result = resolve_page_path(sample_page, "/{slug}.html")
        assert not result.startswith("/")
        assert result == "about.html"

    def test_result_has_no_double_slashes(self, sample_page: Page) -> None:
        """The resolved path contains no consecutive slashes."""
        result = resolve_page_path(sample_page, "pages/{slug}.html")
        assert "//" not in result


##############################################################################
# compute_page_output_path tests.


class TestComputePageOutputPath:
    """Tests for compute_page_output_path."""

    def test_default_template(self, sample_page: Page, tmp_path: Path) -> None:
        """Default template produces the expected flat file in the output directory."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = compute_page_output_path(output_dir, sample_page, DEFAULT_PAGE_PATH)

        assert path == (output_dir / "about.html").resolve()

    def test_nested_template(self, sample_page: Page, tmp_path: Path) -> None:
        """A template with subdirectory produces the expected nested path."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = compute_page_output_path(output_dir, sample_page, "pages/{slug}.html")

        assert path == (output_dir / "pages" / "about.html").resolve()

    def test_path_is_within_output_dir(self, sample_page: Page, tmp_path: Path) -> None:
        """The resolved path is always within the output directory."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = compute_page_output_path(output_dir, sample_page, DEFAULT_PAGE_PATH)

        assert path.is_relative_to(output_dir.resolve())

    def test_path_traversal_raises(self, sample_page: Page, tmp_path: Path) -> None:
        """A template that would escape the output directory raises ValueError."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with pytest.raises(ValueError, match="escapes the output directory"):
            compute_page_output_path(
                output_dir, sample_page, "../../../etc/passwd/{slug}.html"
            )


### test_page_path.py ends here
