"""Post path resolution for configurable output file paths."""

##############################################################################
# Python imports.
import re
from pathlib import Path
from string import Formatter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blogmore.parser import Post

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
    if not template:
        raise ValueError("post_path must not be empty")

    # Extract field names using the standard Formatter parser.
    try:
        field_names = [
            field_name
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name is not None
        ]
    except (ValueError, KeyError) as error:
        raise ValueError(
            f"post_path '{template}' contains an invalid placeholder: {error}"
        ) from error

    unknown = set(field_names) - ALLOWED_PATH_VARIABLES
    if unknown:
        raise ValueError(
            f"post_path '{template}' contains unknown variable(s): "
            + ", ".join(sorted(unknown))
            + f". Allowed variables are: {', '.join(sorted(ALLOWED_PATH_VARIABLES))}"
        )

    if "slug" not in field_names:
        raise ValueError(
            f"post_path '{template}' must contain the {{slug}} variable so that "
            "each post can be uniquely identified"
        )


def resolve_post_path(post: "Post", template: str) -> str:
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
    # Import here to avoid circular imports at module load time.
    from blogmore.parser import remove_date_prefix, sanitize_for_url

    slug = remove_date_prefix(post.slug)

    # Author – read from metadata, slugify for safe use in URLs/paths.
    author = ""
    if post.metadata:
        raw_author = post.metadata.get("author")
        if raw_author:
            author = sanitize_for_url(str(raw_author))

    # Category – already available as a sanitised property on Post.
    category = post.safe_category or ""

    # Date / time components – empty strings for undated posts.
    if post.date:
        year = str(post.date.year)
        month = f"{post.date.month:02d}"
        day = f"{post.date.day:02d}"
        hour = f"{post.date.hour:02d}"
        minute = f"{post.date.minute:02d}"
        second = f"{post.date.second:02d}"
    else:
        year = month = day = hour = minute = second = ""

    variables = {
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "minute": minute,
        "second": second,
        "category": category,
        "author": author,
        "slug": slug,
    }

    try:
        result = template.format_map(variables)
    except (KeyError, ValueError) as error:
        raise ValueError(
            f"Failed to resolve post_path template '{template}': {error}"
        ) from error

    # Collapse multiple consecutive forward slashes that may result from
    # empty variable substitutions (e.g. an undated post using {year}/{month}).
    result = re.sub(r"/+", "/", result)

    # Remove any leading slash so the result can be safely joined onto a
    # Path with the / operator.
    return result.lstrip("/")


def compute_output_path(output_dir: Path, post: "Post", template: str) -> Path:
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
    relative = resolve_post_path(post, template)
    candidate = (output_dir / relative).resolve()
    output_resolved = output_dir.resolve()

    if not candidate.is_relative_to(output_resolved):
        raise ValueError(
            f"The resolved post path '{relative}' escapes the output directory. "
            "Ensure the post_path template does not contain '..' segments."
        )

    return candidate


### post_path.py ends here
