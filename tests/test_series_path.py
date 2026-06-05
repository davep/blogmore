"""Tests for the series_path module."""

from pathlib import Path

import pytest

from blogmore.series_path import (
    ALLOWED_SERIES_PATH_VARIABLES,
    DEFAULT_SERIES_PATH,
    compute_series_output_path,
    resolve_series_path,
    validate_series_path_template,
)


class TestValidateSeriesPathTemplate:
    """Tests for validate_series_path_template."""

    def test_default_template_is_valid(self) -> None:
        """The default template must pass validation without errors."""
        validate_series_path_template(DEFAULT_SERIES_PATH)

    def test_slug_only_template_is_valid(self) -> None:
        """A minimal template containing only {slug} is valid."""
        validate_series_path_template("{slug}.html")

    def test_nested_slug_template_is_valid(self) -> None:
        """A template nesting {slug} in a subdirectory is valid."""
        validate_series_path_template("series/{slug}/index.html")

    def test_empty_template_raises(self) -> None:
        """An empty template string raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            validate_series_path_template("")

    def test_missing_slug_raises(self) -> None:
        """A template without {slug} raises ValueError."""
        with pytest.raises(ValueError, match=r"\{slug\}"):
            validate_series_path_template("series/index.html")

    def test_unknown_variable_raises(self) -> None:
        """A template with an unknown variable name raises ValueError."""
        with pytest.raises(ValueError, match="unknown variable"):
            validate_series_path_template("{year}/{slug}.html")

    def test_allowed_variables_constant_is_correct(self) -> None:
        """ALLOWED_SERIES_PATH_VARIABLES contains exactly the documented variable names."""
        assert {"slug"} == ALLOWED_SERIES_PATH_VARIABLES


class TestResolveSeriesPath:
    """Tests for resolve_series_path."""

    def test_default_template(self) -> None:
        """Default template produces series/slug/index.html."""
        result = resolve_series_path("my-series", DEFAULT_SERIES_PATH)
        assert result == "series/my-series/index.html"

    def test_nested_series_directory(self) -> None:
        """A template with a subdirectory prefix resolves correctly."""
        result = resolve_series_path("my-series", "series/{slug}.html")
        assert result == "series/my-series.html"

    def test_leading_slash_removed(self) -> None:
        """A template beginning with / produces a result without a leading slash."""
        result = resolve_series_path("my-series", "/series/{slug}.html")
        assert not result.startswith("/")
        assert result == "series/my-series.html"


class TestComputeSeriesOutputPath:
    """Tests for compute_series_output_path."""

    def test_default_template(self, tmp_path: Path) -> None:
        """Default template produces the expected file in the output directory."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = compute_series_output_path(output_dir, "my-series", DEFAULT_SERIES_PATH)

        assert path == (output_dir / "series" / "my-series" / "index.html").resolve()

    def test_path_is_within_output_dir(self, tmp_path: Path) -> None:
        """The resolved path is always within the output directory."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = compute_series_output_path(output_dir, "my-series", DEFAULT_SERIES_PATH)

        assert path.is_relative_to(output_dir.resolve())

    def test_path_traversal_raises(self, tmp_path: Path) -> None:
        """A template that would escape the output directory raises ValueError."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with pytest.raises(ValueError, match="escapes the output directory"):
            compute_series_output_path(
                output_dir, "my-series", "../../../etc/passwd/{slug}.html"
            )
