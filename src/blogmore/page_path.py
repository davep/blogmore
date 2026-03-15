"""Page path resolution for configurable output file paths."""

##############################################################################
# Standard-library imports.
import re
from pathlib import Path
from string import Formatter

##############################################################################
# Application imports.
from blogmore.parser import Page

##############################################################################
# Default page path template (matches historical BlogMore behaviour).
DEFAULT_PAGE_PATH = "{slug}.html"

##############################################################################
# The set of variable names that may appear in a page_path template.
# Pages have no date, category, or author metadata, so the only meaningful
# variable is the page slug.
ALLOWED_PAGE_PATH_VARIABLES = frozenset({"slug"})


def validate_page_path_template(template: str) -> None:
    """Validate a page_path format string.

    Checks that the template string is well-formed and only references
    variables from the allowed set.

    Args:
        template: The page_path format string to validate.

    Raises:
        ValueError: If the template is empty, contains no ``{slug}``
            placeholder, or references an unknown variable name.
    """
    if not template:
        raise ValueError("page_path must not be empty")

    # Extract field names using the standard Formatter parser.
    try:
        field_names = [
            field_name
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name is not None
        ]
    except (ValueError, KeyError) as error:
        raise ValueError(
            f"page_path '{template}' contains an invalid placeholder: {error}"
        ) from error

    unknown = set(field_names) - ALLOWED_PAGE_PATH_VARIABLES
    if unknown:
        raise ValueError(
            f"page_path '{template}' contains unknown variable(s): "
            + ", ".join(sorted(unknown))
            + f". Allowed variables are: {', '.join(sorted(ALLOWED_PAGE_PATH_VARIABLES))}"
        )

    if "slug" not in field_names:
        raise ValueError(
            f"page_path '{template}' must contain the {{slug}} variable so that "
            "each page can be uniquely identified"
        )


def resolve_page_path(page: Page, template: str) -> str:
    """Resolve a page_path template for a given page.

    Substitutes the ``{slug}`` placeholder in *template* with the page's
    slug.  Multiple consecutive forward slashes are collapsed to a single
    slash, and any leading slash is removed so that the result can safely
    be joined onto an output directory path.

    Args:
        page: The page whose slug is used to fill the template.
        template: A format string containing ``{slug}`` placeholder.

    Returns:
        A relative path string (no leading slash) derived by substituting
        the template variables with the page's values.

    Raises:
        ValueError: If the template references an unknown variable or is
            otherwise malformed.
    """
    variables = {"slug": page.slug}

    try:
        result = template.format_map(variables)
    except (KeyError, ValueError) as error:
        raise ValueError(
            f"Failed to resolve page_path template '{template}': {error}"
        ) from error

    # Collapse multiple consecutive forward slashes.
    result = re.sub(r"/+", "/", result)

    # Remove any leading slash so the result can be safely joined onto a
    # Path with the / operator.
    return result.lstrip("/")


def compute_page_output_path(output_dir: Path, page: Page, template: str) -> Path:
    """Compute the safe, absolute output file path for a page.

    Resolves *template* using the page's slug and joins the result onto
    *output_dir*.  The resolved path is checked to ensure it does not escape
    the output directory (preventing accidental path-traversal writes).

    Args:
        output_dir: The root output directory for the generated site.
        page: The page to compute the output path for.
        template: A page_path format string.

    Returns:
        The absolute, resolved output file path for the page.

    Raises:
        ValueError: If the resolved path escapes the output directory.
    """
    relative = resolve_page_path(page, template)
    candidate = (output_dir / relative).resolve()
    output_resolved = output_dir.resolve()

    if not candidate.is_relative_to(output_resolved):
        raise ValueError(
            f"The resolved page path '{relative}' escapes the output directory. "
            "Ensure the page_path template does not contain '..' segments."
        )

    return candidate


### page_path.py ends here
