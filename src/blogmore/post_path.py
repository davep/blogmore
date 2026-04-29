"""Post path resolution for configurable output file paths."""

##############################################################################
# Python imports.
from pathlib import Path

##############################################################################
# Application imports.
from blogmore.content_path import resolve_path, safe_output_path, validate_path_template
from blogmore.parser import Post, build_post_path_vars

##############################################################################
# Default post path template (matches historical BlogMore behaviour).
DEFAULT_POST_PATH = "{year}/{month}/{day}/{slug}.html"

##############################################################################
# The set of variable names that may appear in a post_path template.
ALLOWED_PATH_VARIABLES = frozenset(
    {
        "year",
        "month",
        "day",
        "hour",
        "minute",
        "second",
        "category",
        "author",
        "slug",
    }
)


def validate_post_path_template(template: str) -> None:
    """Validate a post_path format string.

    Checks that the template string is well-formed and only references
    variables from the allowed set.

    Args:
        template: The post_path format string to validate.

    Raises:
        ValueError: If the template is empty, contains no ``{slug}``
            placeholder, or references an unknown variable name.
    """
    validate_path_template(template, "post_path", ALLOWED_PATH_VARIABLES, "post")


def resolve_post_path(post: Post, template: str) -> str:
    """Resolve a post_path template for a given post.

    Substitutes all recognised variable placeholders in *template* with
    values derived from *post*.  Posts that have no date will use empty
    strings for date and time components.  Multiple consecutive forward
    slashes that may appear after substitution are collapsed to a single
    slash, and any leading slash is removed so that the result can safely
    be joined onto an output directory path.

    Args:
        post: The post whose metadata is used to fill the template.
        template: A format string containing ``{variable}`` placeholders.

    Returns:
        A relative path string (no leading slash) derived by substituting
        the template variables with the post's values.

    Raises:
        ValueError: If the template references an unknown variable or is
            otherwise malformed.
    """
    return resolve_path(build_post_path_vars(post), template, "post_path")


def compute_output_path(output_dir: Path, post: Post, template: str) -> Path:
    """Compute the safe, absolute output file path for a post.

    Resolves *template* using the post's metadata and joins the result onto
    *output_dir*.  The resolved path is checked to ensure it does not escape
    the output directory (preventing accidental path-traversal writes).

    Args:
        output_dir: The root output directory for the generated site.
        post: The post to compute the output path for.
        template: A post_path format string.

    Returns:
        The absolute, resolved output file path for the post.

    Raises:
        ValueError: If the resolved path escapes the output directory.
    """
    return safe_output_path(output_dir, resolve_post_path(post, template), "post_path")


### post_path.py ends here
