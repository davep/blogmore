"""Pagination path resolution for configurable index page output paths."""

##############################################################################
# Python imports.
from typing import Final

##############################################################################
# Local imports.
from blogmore.content_path import resolve_path, validate_path_template

##############################################################################
# Default pagination path templates.
DEFAULT_PAGE_1_PATH = "index.html"
DEFAULT_PAGE_N_PATH = "page/{page}.html"

##############################################################################
# The set of variable names that may appear in a pagination path template.
ALLOWED_PAGE_PATH_VARIABLES: Final[set[str]] = {"page"}


##############################################################################
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
    validate_path_template(
        template,
        "page_1_path",
        ALLOWED_PAGE_PATH_VARIABLES,
        "index page",
    )


##############################################################################
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
    validate_path_template(
        template,
        "page_n_path",
        ALLOWED_PAGE_PATH_VARIABLES,
        "subsequent page",
        required_variables=ALLOWED_PAGE_PATH_VARIABLES,
    )


##############################################################################
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
    return resolve_path({"page": str(page)}, template, "pagination path")


### pagination_path.py ends here
