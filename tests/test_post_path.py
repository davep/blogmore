"""Tests for the post_path module."""

##############################################################################
# Standard-library imports.
import datetime as dt
from pathlib import Path

##############################################################################
# Third-party imports.
import pytest

##############################################################################
# Application imports.
from blogmore.parser import Post
from blogmore.post_path import (
    ALLOWED_PATH_VARIABLES,
    DEFAULT_POST_PATH,
    compute_output_path,
    resolve_post_path,
    validate_post_path_template,
)


##############################################################################
# Fixtures.

@pytest.fixture
def dated_post() -> Post:
    """Return a post with a full date and metadata."""
    return Post(
        path=Path("2024-01-15-my-great-article.md"),
        title="My Great Article",
        content="Content here.",
        html_content="<p>Content here.</p>",
        date=dt.datetime(2024, 1, 15, 9, 30, 5, tzinfo=dt.UTC),
        category="Python",
        tags=["python", "blog"],
        draft=False,
        metadata={"title": "My Great Article", "author": "Dave Pearson"},
    )


@pytest.fixture
def undated_post() -> Post:
    """Return a post with no date."""
    return Post(
        path=Path("timeless-post.md"),
        title="Timeless",
        content="Content.",
        html_content="<p>Content.</p>",
        date=None,
        category=None,
        tags=[],
        draft=False,
        metadata={"title": "Timeless"},
    )


##############################################################################
# validate_post_path_template tests.


class TestValidatePostPathTemplate:
    """Tests for validate_post_path_template."""

    def test_default_template_is_valid(self) -> None:
        """The default template must pass validation without errors."""
        validate_post_path_template(DEFAULT_POST_PATH)

    def test_slug_only_template_is_valid(self) -> None:
        """A minimal template containing only {slug} is valid."""
        validate_post_path_template("{slug}.html")

    def test_all_variables_template_is_valid(self) -> None:
        """A template that uses every allowed variable is valid."""
        validate_post_path_template(
            "{year}/{month}/{day}/{hour}/{minute}/{second}/{category}/{author}/{slug}.html"
        )

    def test_empty_template_raises(self) -> None:
        """An empty template string raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            validate_post_path_template("")

    def test_missing_slug_raises(self) -> None:
        """A template without {slug} raises ValueError."""
        with pytest.raises(ValueError, match=r"\{slug\}"):
            validate_post_path_template("{year}/{month}/{day}/index.html")

    def test_unknown_variable_raises(self) -> None:
        """A template with an unknown variable name raises ValueError."""
        with pytest.raises(ValueError, match="unknown variable"):
            validate_post_path_template("{year}/{title}/{slug}.html")

    def test_multiple_unknown_variables_raises(self) -> None:
        """A template with multiple unknown variables raises ValueError."""
        with pytest.raises(ValueError, match="unknown variable"):
            validate_post_path_template("{year}/{foo}/{bar}/{slug}.html")

    def test_allowed_variables_constant_is_correct(self) -> None:
        """ALLOWED_PATH_VARIABLES contains exactly the documented variable names."""
        assert ALLOWED_PATH_VARIABLES == {
            "year", "month", "day",
            "hour", "minute", "second",
            "category", "author", "slug",
        }


##############################################################################
# resolve_post_path tests.


class TestResolvePostPath:
    """Tests for resolve_post_path."""

    def test_default_template_dated_post(self, dated_post: Post) -> None:
        """Default template produces expected year/month/day/slug.html path."""
        result = resolve_post_path(dated_post, DEFAULT_POST_PATH)
        assert result == "2024/01/15/my-great-article.html"

    def test_slug_removes_date_prefix(self, dated_post: Post) -> None:
        """The YYYY-MM-DD- date prefix is stripped from the slug."""
        result = resolve_post_path(dated_post, "{slug}.html")
        assert result == "my-great-article.html"

    def test_year_variable(self, dated_post: Post) -> None:
        """The {year} variable is the four-digit year."""
        result = resolve_post_path(dated_post, "{year}/{slug}.html")
        assert result.startswith("2024/")

    def test_month_variable_zero_padded(self, dated_post: Post) -> None:
        """The {month} variable is zero-padded to two digits."""
        result = resolve_post_path(dated_post, "{month}/{slug}.html")
        assert result.startswith("01/")

    def test_day_variable_zero_padded(self, dated_post: Post) -> None:
        """The {day} variable is zero-padded to two digits."""
        result = resolve_post_path(dated_post, "{day}/{slug}.html")
        assert result.startswith("15/")

    def test_hour_variable_zero_padded(self, dated_post: Post) -> None:
        """The {hour} variable is zero-padded to two digits."""
        result = resolve_post_path(dated_post, "{hour}/{slug}.html")
        assert result.startswith("09/")

    def test_minute_variable_zero_padded(self, dated_post: Post) -> None:
        """The {minute} variable is zero-padded to two digits."""
        result = resolve_post_path(dated_post, "{minute}/{slug}.html")
        assert result.startswith("30/")

    def test_second_variable_zero_padded(self, dated_post: Post) -> None:
        """The {second} variable is zero-padded to two digits."""
        result = resolve_post_path(dated_post, "{second}/{slug}.html")
        assert result.startswith("05/")

    def test_category_variable_slugified(self, dated_post: Post) -> None:
        """The {category} variable is slugified."""
        result = resolve_post_path(dated_post, "{category}/{slug}.html")
        assert result.startswith("python/")

    def test_author_variable_slugified(self, dated_post: Post) -> None:
        """The {author} variable is slugified."""
        result = resolve_post_path(dated_post, "{author}/{slug}.html")
        assert result.startswith("dave-pearson/")

    def test_post_with_own_directory(self, dated_post: Post) -> None:
        """A template that puts each post in its own directory works."""
        result = resolve_post_path(dated_post, "{year}/{month}/{day}/{slug}/index.html")
        assert result == "2024/01/15/my-great-article/index.html"

    def test_posts_under_single_directory(self, dated_post: Post) -> None:
        """A template that puts all posts under /posts/ works."""
        result = resolve_post_path(dated_post, "posts/{slug}.html")
        assert result == "posts/my-great-article.html"

    def test_leading_slash_removed(self, dated_post: Post) -> None:
        """A template beginning with / produces a result without a leading slash."""
        result = resolve_post_path(dated_post, "/{year}/{month}/{day}/{slug}.html")
        assert not result.startswith("/")
        assert result == "2024/01/15/my-great-article.html"

    def test_undated_post_date_vars_empty(self, undated_post: Post) -> None:
        """Date variables are empty strings for posts without a date."""
        result = resolve_post_path(undated_post, "{year}/{month}/{day}/{slug}.html")
        # Empty date segments collapse and leading slashes are stripped.
        assert "{" not in result
        assert "timeless-post" in result

    def test_undated_post_slug_only(self, undated_post: Post) -> None:
        """An undated post with a slug-only template resolves correctly."""
        result = resolve_post_path(undated_post, "{slug}.html")
        assert result == "timeless-post.html"

    def test_no_category_yields_empty_segment(self, undated_post: Post) -> None:
        """A post with no category produces an empty segment for {category}."""
        result = resolve_post_path(undated_post, "{category}/{slug}.html")
        # Consecutive slashes are collapsed.
        assert "//" not in result

    def test_consecutive_slashes_collapsed(self, undated_post: Post) -> None:
        """Multiple consecutive slashes from empty variables are collapsed."""
        result = resolve_post_path(undated_post, "{year}/{month}/{day}/{slug}.html")
        assert "//" not in result

    def test_no_author_in_metadata_yields_empty(self, dated_post: Post) -> None:
        """A post whose metadata has no author produces an empty author segment."""
        dated_post.metadata = {}
        result = resolve_post_path(dated_post, "{author}/{slug}.html")
        # Empty author + collapse means the result is just "slug.html"
        assert not result.startswith("/")
        assert "my-great-article.html" in result


##############################################################################
# compute_output_path tests.


class TestComputeOutputPath:
    """Tests for compute_output_path."""

    def test_default_template(self, dated_post: Post, tmp_path: Path) -> None:
        """Default template produces the expected nested directory structure."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = compute_output_path(output_dir, dated_post, DEFAULT_POST_PATH)

        assert path == output_dir / "2024" / "01" / "15" / "my-great-article.html"

    def test_path_is_within_output_dir(self, dated_post: Post, tmp_path: Path) -> None:
        """The resolved path is always within the output directory."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = compute_output_path(output_dir, dated_post, DEFAULT_POST_PATH)

        assert path.is_relative_to(output_dir.resolve())

    def test_path_traversal_raises(self, dated_post: Post, tmp_path: Path) -> None:
        """A template that would escape the output directory raises ValueError."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with pytest.raises(ValueError, match="escapes the output directory"):
            compute_output_path(output_dir, dated_post, "../../../etc/passwd/{slug}.html")

    def test_absolute_path_segments_contained(
        self, dated_post: Post, tmp_path: Path
    ) -> None:
        """Even with an absolute-looking resolved path the result stays in output_dir."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # The leading slash in the template is stripped before joining.
        path = compute_output_path(output_dir, dated_post, "/{slug}.html")
        assert path.is_relative_to(output_dir.resolve())

    def test_slug_only_template(self, dated_post: Post, tmp_path: Path) -> None:
        """A simple slug-only template resolves to a flat file in the output dir."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = compute_output_path(output_dir, dated_post, "{slug}.html")
        assert path == (output_dir / "my-great-article.html").resolve()


### test_post_path.py ends here
