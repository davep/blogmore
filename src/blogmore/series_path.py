"""Series path resolution for configurable output file paths."""

from pathlib import Path
from typing import Final

from blogmore.content_path import resolve_path, safe_output_path, validate_path_template

DEFAULT_SERIES_PATH = "series/{slug}/index.html"

ALLOWED_SERIES_PATH_VARIABLES: Final[set[str]] = {"slug"}


def validate_series_path_template(template: str) -> None:
    """Validate a series_path format string.

    Checks that the template string is well-formed and only references
    variables from the allowed set.

    Args:
        template: The series_path format string to validate.

    Raises:
        ValueError: If the template is empty, contains no `{slug}`
            placeholder, or references an unknown variable name.
    """
    validate_path_template(
        template,
        "series_path",
        ALLOWED_SERIES_PATH_VARIABLES,
        "series",
        ALLOWED_SERIES_PATH_VARIABLES,
    )


def resolve_series_path(slug: str, template: str) -> str:
    """Resolve a series_path template for a given series slug.

    Substitutes the `{slug}` placeholder in *template* with the series's
    slug. Multiple consecutive forward slashes are collapsed to a single
    slash, and any leading slash is removed so that the result can safely
    be joined onto an output directory path.

    Args:
        slug: The series slug.
        template: A format string containing `{slug}` placeholder.

    Returns:
        A relative path string (no leading slash) derived by substituting
        the template variables with the series slug.
    """
    return resolve_path({"slug": slug}, template, "series_path")


def compute_series_output_path(output_dir: Path, slug: str, template: str) -> Path:
    """Compute the safe, absolute output file path for a series.

    Resolves *template* using the series's slug and joins the result onto
    *output_dir*. The resolved path is checked to ensure it does not escape
    the output directory (preventing accidental path-traversal writes).

    Args:
        output_dir: The root output directory for the generated site.
        slug: The series slug to compute the output path for.
        template: A series_path format string.

    Returns:
        The absolute, resolved output file path for the series.
    """
    return safe_output_path(
        output_dir, resolve_series_path(slug, template), "series_path"
    )
