"""CSS generation for fenced code block syntax highlighting styles."""

##############################################################################
# Python imports.
import re
from typing import Literal

##############################################################################
# Pygments imports.
from pygments.formatters import HtmlFormatter
from pygments.styles import get_all_styles, get_style_by_name

##############################################################################
# Default Pygments styles used for code syntax highlighting.
DEFAULT_LIGHT_STYLE = "xcode"
DEFAULT_DARK_STYLE = "github-dark"


def is_valid_style(style_name: str) -> bool:
    """Return whether *style_name* is a valid Pygments style name.

    Args:
        style_name: The name of the Pygments style to check.

    Returns:
        ``True`` if the style name is recognised by Pygments, ``False``
        otherwise.
    """
    return style_name in get_all_styles()


def _colour_scheme_for_style(style_name: str) -> Literal["light", "dark"]:
    """Return the CSS ``color-scheme`` value appropriate for the given Pygments style.

    Inspects the style's background colour and calculates its perceived
    luminance.  Styles with a dark background are classified as ``"dark"``
    and those with a light background as ``"light"``.

    This is used to set ``color-scheme`` on the ``.highlight`` element so
    that the browser's ``::selection`` highlight colours and any inherited
    text colours are appropriate for the Pygments style's actual background —
    regardless of the site-wide light/dark mode setting.

    Args:
        style_name: A valid Pygments style name.

    Returns:
        ``"dark"`` when the style has a dark background, ``"light"``
        otherwise.
    """
    style = get_style_by_name(style_name)
    hex_bg = style.background_color.lstrip("#")
    red = int(hex_bg[0:2], 16)
    green = int(hex_bg[2:4], 16)
    blue = int(hex_bg[4:6], 16)
    # ITU-R BT.601 perceived luminance coefficients.
    luminance = 0.299 * red + 0.587 * green + 0.114 * blue
    return "dark" if luminance < 128 else "light"


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

    Each section also sets the CSS ``color-scheme`` property directly on the
    ``.highlight`` element, derived from the background luminance of the
    chosen Pygments style.  This ensures that the browser's ``::selection``
    highlight colours and any inherited text colour are appropriate for the
    Pygments style's actual background — regardless of the site-wide
    light/dark mode setting.

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

    light_colour_scheme = _colour_scheme_for_style(light_style)
    dark_colour_scheme = _colour_scheme_for_style(dark_style)

    # Light mode — apply rules unconditionally.  Also set color-scheme so
    # that browser ::selection colours match the Pygments style background.
    light_section = (
        f".highlight {{ color-scheme: {light_colour_scheme}; }}\n"
        + "\n".join(light_rules)
    )

    # Dark mode (system preference, no explicit theme toggle).
    auto_dark_rules = _prefix_highlight_rules(dark_rules, ":root:not([data-theme])")
    auto_dark_section = (
        "@media (prefers-color-scheme: dark) {\n"
        f"    :root:not([data-theme]) .highlight {{ color-scheme: {dark_colour_scheme}; }}\n"
        + "\n".join(f"    {rule}" for rule in auto_dark_rules)
        + "\n}"
    )

    # Dark mode (explicitly selected via the theme-toggle button).
    explicit_dark_rules = _prefix_highlight_rules(
        dark_rules, ':root[data-theme="dark"]'
    )
    explicit_dark_section = (
        f':root[data-theme="dark"] .highlight {{ color-scheme: {dark_colour_scheme}; }}\n'
        + "\n".join(explicit_dark_rules)
    )

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
