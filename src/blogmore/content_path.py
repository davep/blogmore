"""Shared path-resolution utilities for content output paths.

This module provides the generic building blocks used by ``page_path`` and
``post_path``.  Each content type supplies its own allowed-variable set and
variable dict; this module handles the common validation, substitution, and
safety checks.
"""

##############################################################################
# Standard-library imports.
import re
from pathlib import Path
from string import Formatter


def validate_path_template(
    template: str,
    config_key: str,
    allowed_variables: frozenset[str],
    item_name: str,
) -> None:
    """Validate a path format string for a content type.

    Checks that *template* is non-empty, well-formed, references only
    variables from *allowed_variables*, and includes the mandatory
    ``{slug}`` placeholder.

    Args:
        template: The path format string to validate.
        config_key: The configuration key name used in error messages
            (e.g. ``"page_path"`` or ``"post_path"``).
        allowed_variables: The set of variable names permitted in the
            template.
        item_name: The human-readable name of the content type used in
            the uniqueness error message (e.g. ``"page"`` or ``"post"``).

    Raises:
        ValueError: If the template is empty, malformed, references an
            unknown variable, or omits the ``{slug}`` placeholder.
    """
    if not template:
        raise ValueError(f"{config_key} must not be empty")

    # Extract field names using the standard Formatter parser.
    try:
        field_names = [
            field_name
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name is not None
        ]
    except (ValueError, KeyError) as error:
        raise ValueError(
            f"{config_key} '{template}' contains an invalid placeholder: {error}"
        ) from error

    unknown = set(field_names) - allowed_variables
    if unknown:
        raise ValueError(
            f"{config_key} '{template}' contains unknown variable(s): "
            + ", ".join(sorted(unknown))
            + f". Allowed variables are: {', '.join(sorted(allowed_variables))}"
        )

    if "slug" not in field_names:
        raise ValueError(
            f"{config_key} '{template}' must contain the {{slug}} variable so that "
            f"each {item_name} can be uniquely identified"
        )


def resolve_path(variables: dict[str, str], template: str, config_key: str) -> str:
    """Resolve a path template using a pre-built variables mapping.

    Substitutes *variables* into *template* via :meth:`str.format_map`,
    collapses consecutive forward slashes that may result from empty
    variable substitutions, and strips any leading slash so the result
    can safely be joined onto an output directory path.

    Args:
        variables: A mapping of variable names to their resolved string
            values.
        template: A format string containing ``{variable}`` placeholders.
        config_key: The configuration key name used in error messages
            (e.g. ``"page_path"`` or ``"post_path"``).

    Returns:
        A relative path string (no leading slash).

    Raises:
        ValueError: If the template references an unknown variable or is
            otherwise malformed.
    """
    try:
        result = template.format_map(variables)
    except (KeyError, ValueError) as error:
        raise ValueError(
            f"Failed to resolve {config_key} template '{template}': {error}"
        ) from error

    # Collapse consecutive slashes that can arise from empty variable
    # substitutions (e.g. an undated post using {year}/{month}).
    result = re.sub(r"/+", "/", result)

    # Strip the leading slash so the result joins safely with Path('/').
    return result.lstrip("/")


def safe_output_path(output_dir: Path, relative: str, config_key: str) -> Path:
    """Join *relative* onto *output_dir* and verify the result stays inside it.

    Prevents accidental path-traversal writes that could occur if a
    user-supplied template contains ``..`` segments.

    Args:
        output_dir: The root output directory for the generated site.
        relative: The relative path string produced by resolving a
            content-path template.
        config_key: The configuration key name used in error messages
            (e.g. ``"page_path"`` or ``"post_path"``).

    Returns:
        The absolute, resolved output file path.

    Raises:
        ValueError: If the resolved path escapes the output directory.
    """
    candidate = (output_dir / relative).resolve()
    output_resolved = output_dir.resolve()

    if not candidate.is_relative_to(output_resolved):
        # Derive a human-readable label: "page_path" → "page path".
        label = config_key.replace("_", " ")
        raise ValueError(
            f"The resolved {label} '{relative}' escapes the output directory. "
            f"Ensure the {config_key} template does not contain '..' segments."
        )

    return candidate


### content_path.py ends here
