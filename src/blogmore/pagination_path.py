"""Pagination path resolution for configurable index page output paths."""

##############################################################################
# Python imports.
import re
from string import Formatter

##############################################################################
# Default pagination path templates (match historical BlogMore behaviour).
DEFAULT_PAGE_1_PATH = "index.html"
DEFAULT_PAGE_N_PATH = "page/{page}.html"

##############################################################################
# The set of variable names that may appear in a pagination path template.
# The only meaningful variable is the page number.
ALLOWED_PAGE_1_PATH_VARIABLES = frozenset({"page"})
ALLOWED_PAGE_N_PATH_VARIABLES = frozenset({"page"})


def validate_page_1_path_template(template: str) -> None:
    """Validate a page_1_path format string.

    Checks that the template string is well-formed and only references
    variables from the allowed set.  The ``{page}`` placeholder is
    allowed but not required in ``page_1_path`` (since the default
    ``index.html`` does not use it).

    Args:
        template: The page_1_path format string to validate.

    Raises:
        ValueError: If the template is empty or references an unknown
            variable name.
    """
    if not template:
        raise ValueError("page_1_path must not be empty")

    try:
        field_names = [
            field_name
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name is not None
        ]
    except (ValueError, KeyError) as error:
        raise ValueError(
            f"page_1_path '{template}' contains an invalid placeholder: {error}"
        ) from error

    unknown = set(field_names) - ALLOWED_PAGE_1_PATH_VARIABLES
    if unknown:
        raise ValueError(
            f"page_1_path '{template}' contains unknown variable(s): "
            + ", ".join(sorted(unknown))
            + f". Allowed variables are: {', '.join(sorted(ALLOWED_PAGE_1_PATH_VARIABLES))}"
        )


def validate_page_n_path_template(template: str) -> None:
    """Validate a page_n_path format string.

    Checks that the template string is well-formed, only references
    variables from the allowed set, and includes the required
    ``{page}`` placeholder so that each page can be uniquely
    identified.

    Args:
        template: The page_n_path format string to validate.

    Raises:
        ValueError: If the template is empty, contains no ``{page}``
            placeholder, or references an unknown variable name.
    """
    if not template:
        raise ValueError("page_n_path must not be empty")

    try:
        field_names = [
            field_name
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name is not None
        ]
    except (ValueError, KeyError) as error:
        raise ValueError(
            f"page_n_path '{template}' contains an invalid placeholder: {error}"
        ) from error

    unknown = set(field_names) - ALLOWED_PAGE_N_PATH_VARIABLES
    if unknown:
        raise ValueError(
            f"page_n_path '{template}' contains unknown variable(s): "
            + ", ".join(sorted(unknown))
            + f". Allowed variables are: {', '.join(sorted(ALLOWED_PAGE_N_PATH_VARIABLES))}"
        )

    if "page" not in field_names:
        raise ValueError(
            f"page_n_path '{template}' must contain the {{page}} variable so that "
            "each subsequent page can be uniquely identified"
        )


def resolve_pagination_page_path(template: str, page: int) -> str:
    """Resolve a pagination path template for a given page number.

    Substitutes the ``{page}`` placeholder in *template* with the
    supplied page number.  Multiple consecutive forward slashes that
    may appear after substitution are collapsed to a single slash, and
    any leading slash is removed so that the result can safely be
    joined onto a base directory path.

    Args:
        template: A format string optionally containing a ``{page}``
            placeholder.
        page: The 1-based page number to substitute.

    Returns:
        A relative path string (no leading slash) derived from the
        template.
    """
    try:
        result = template.format(page=page)
    except (KeyError, ValueError) as error:
        raise ValueError(
            f"Failed to resolve pagination path template '{template}': {error}"
        ) from error

    result = re.sub(r"/+", "/", result)
    return result.lstrip("/")


### pagination_path.py ends here
