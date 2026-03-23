"""CSS generation for fenced code block syntax highlighting styles."""

##############################################################################
# Python imports.
import re

##############################################################################
# Pygments imports.
from pygments.formatters import HtmlFormatter
from pygments.styles import get_all_styles

##############################################################################
# Default Pygments styles used for code syntax highlighting.
DEFAULT_LIGHT_STYLE = "default"
DEFAULT_DARK_STYLE = "monokai"


def is_valid_style(style_name: str) -> bool:
    """Return whether *style_name* is a valid Pygments style name.

    Args:
        style_name: The name of the Pygments style to check.

    Returns:
        ``True`` if the style name is recognised by Pygments, ``False``
        otherwise.
    """
    return style_name in get_all_styles()


def _highlight_rules(style_name: str) -> list[str]:
    """Extract ``.highlight`` CSS rules for the given Pygments style.

    Uses the Pygments ``HtmlFormatter`` to produce CSS and filters the output
    to only the lines that begin with ``.highlight``, discarding all preamble
    rules (``pre``, ``td.linenos``, etc.) which are not relevant to inline
    code colouring.

    Args:
        style_name: A valid Pygments style name.

    Returns:
        A list of CSS rule strings, each starting with ``.highlight``.

    Raises:
        ClassNotFound: If *style_name* is not a valid Pygments style.
    """
    formatter = HtmlFormatter(style=style_name)
    css: str = formatter.get_style_defs(".highlight")  # type: ignore[no-untyped-call]
    return [line for line in css.splitlines() if line.startswith(".highlight")]


def _prefix_highlight_rules(rules: list[str], prefix: str) -> list[str]:
    """Re-write a list of ``.highlight`` CSS rules, inserting a selector prefix.

    Each ``.highlight`` occurrence at the start of a selector is replaced by
    ``<prefix> .highlight``.  This transforms a plain light-mode rule such as::

        .highlight .k { color: #008000; font-weight: bold } /* Keyword */

    into::

        :root[data-theme="dark"] .highlight .k { color: #008000; font-weight: bold } /* Keyword */

    Args:
        rules: A list of CSS rule strings as returned by :func:`_highlight_rules`.
        prefix: The selector prefix to insert before ``.highlight``.

    Returns:
        A new list of CSS rule strings with the prefix applied.
    """
    return [re.sub(r"^\.highlight", f"{prefix} .highlight", rule) for rule in rules]


def build_code_css(light_style: str, dark_style: str) -> str:
    """Build a complete ``code.css`` stylesheet for the given Pygments styles.

    Generates CSS that:

    * Applies the *light_style* colour scheme unconditionally (base rules that
      remain in effect in light mode).
    * Overrides the colour scheme with *dark_style* when the operating system
      reports a preference for dark mode (``@media (prefers-color-scheme:
      dark)``) and the user has not explicitly chosen a theme via the
      theme-toggle button (``[data-theme]`` is absent from ``<html>``).
    * Overrides the colour scheme with *dark_style* when the theme-toggle
      button has explicitly selected dark mode
      (``[data-theme="dark"]`` on ``<html>``).

    Args:
        light_style: Name of the Pygments style to use in light mode.
        dark_style: Name of the Pygments style to use in dark mode.

    Returns:
        A CSS string suitable for writing to ``code.css``.

    Raises:
        ClassNotFound: If either *light_style* or *dark_style* is not a
            recognised Pygments style name.
    """
    light_rules = _highlight_rules(light_style)
    dark_rules = _highlight_rules(dark_style)

    # Light mode — apply rules unconditionally.
    light_section = "\n".join(light_rules)

    # Dark mode (system preference, no explicit theme toggle).
    auto_dark_rules = _prefix_highlight_rules(dark_rules, ":root:not([data-theme])")
    auto_dark_section = (
        "@media (prefers-color-scheme: dark) {\n"
        + "\n".join(f"    {rule}" for rule in auto_dark_rules)
        + "\n}"
    )

    # Dark mode (explicitly selected via the theme-toggle button).
    explicit_dark_rules = _prefix_highlight_rules(
        dark_rules, ':root[data-theme="dark"]'
    )
    explicit_dark_section = "\n".join(explicit_dark_rules)

    parts = [
        "/* Light mode syntax highlighting */",
        light_section,
        "",
        "/* Dark mode syntax highlighting (system preference) */",
        auto_dark_section,
        "",
        "/* Dark mode syntax highlighting (explicit theme toggle) */",
        explicit_dark_section,
    ]
    return "\n".join(parts) + "\n"


### code_styles.py ends here
