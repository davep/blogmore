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

##############################################################################
# Internal regex for parsing a single Pygments .highlight CSS rule.
_RULE_PATTERN = re.compile(r"^(\.highlight(?:\s+\.[a-z0-9]+)?)\s*\{([^}]*)\}")


def is_valid_style(style_name: str) -> bool:
    """Return whether *style_name* is a valid Pygments style name.

    Args:
        style_name: The name of the Pygments style to check.

    Returns:
        [`True`][builtins.True] if the style name is recognised by Pygments, [`False`][builtins.False]
        otherwise.
    """
    return style_name in get_all_styles()


def _colour_scheme_for_style(style_name: str) -> Literal["light", "dark"]:
    """Return the CSS `color-scheme` value appropriate for the given Pygments style.

    Inspects the style's background colour and calculates its perceived
    luminance.  Styles with a dark background are classified as `"dark"`
    and those with a light background as `"light"`.

    This is used to set [`color-scheme`][mdn.color-scheme] on the [`.highlight`][pygments.highlight] element so
    that the browser's [`::selection`][mdn.selection] highlight colours and any inherited
    text colours are appropriate for the Pygments style's actual background —
    regardless of the site-wide light/dark mode setting.

    Args:
        style_name: A valid Pygments style name.

    Returns:
        `"dark"` when the style has a dark background, `"light"`
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
    """Extract [`.highlight`][pygments.highlight] CSS rules for the given Pygments style.

    Uses the Pygments [`HtmlFormatter`][pygments.HtmlFormatter] to produce CSS and filters the output
    to only the lines that begin with [`.highlight`][pygments.highlight], discarding all preamble
    rules ([`pre`][pygments.pre], [`td.linenos`][pygments.td.linenos], etc.) which are not relevant to inline
    code colouring.

    Args:
        style_name: A valid Pygments style name.

    Returns:
        A list of CSS rule strings, each starting with [`.highlight`][pygments.highlight].

    Raises:
        ClassNotFound: If *style_name* is not a valid Pygments style.
    """
    formatter = HtmlFormatter(style=style_name)
    css: str = formatter.get_style_defs(".highlight")  # type: ignore[no-untyped-call]
    return [line for line in css.splitlines() if line.startswith(".highlight")]


def _parse_token_rules(rules: list[str]) -> dict[str, dict[str, str]]:
    """Parse a list of raw [`.highlight`][pygments.highlight] CSS rules into a structured mapping.

    Args:
        rules: CSS rule strings as returned by
            [blogmore.code_styles._highlight_rules][blogmore.code_styles._highlight_rules].

    Returns:
        A dictionary mapping each CSS selector (e.g. [`.highlight .k`][pygments.highlight.k]) to a
        dictionary of CSS property names to their raw values.
    """
    parsed: dict[str, dict[str, str]] = {}
    for rule in rules:
        match = _RULE_PATTERN.match(rule)
        if not match:
            continue
        selector = match.group(1).strip()
        props: dict[str, str] = {}
        for declaration in match.group(2).split(";"):
            declaration = declaration.strip()
            if ":" in declaration:
                prop, _, value = declaration.partition(":")
                props[prop.strip()] = value.strip()
        if props:
            parsed[selector] = props
    return parsed


def _css_var_name(selector: str, prop: str) -> str:
    """Generate a CSS custom property name for a [`.highlight`][pygments.highlight] selector and property.

    Args:
        selector: A CSS selector such as [`.highlight .k`][pygments.highlight.k] or [`.highlight`][pygments.highlight].
        prop: A CSS property name such as [`color`][mdn.color] or [`font-weight`][mdn.font-weight].

    Returns:
        A CSS custom property name such as [`--hl-k-color`][css.hl-k-color] or
        [`--hl-background`][css.hl-background].
    """
    parts = selector.strip().split()
    if len(parts) > 1:
        token = parts[-1].lstrip(".")
        return f"--hl-{token}-{prop}"
    return f"--hl-{prop}"


def build_code_css(light_style: str, dark_style: str) -> str:
    """Build a complete [`code.css`][blogmore.code_css] stylesheet for the given Pygments styles.

    Uses CSS custom properties so that each [`.highlight`][pygments.highlight] selector rule is
    declared only once.  Theme switching is achieved by overriding the custom
    properties in two dark-mode contexts:

    * `@media (prefers-color-scheme: dark)` with `:root:not([data-theme])`
      — active when the operating system reports a dark preference and the
      user has not activated the theme-toggle button.
    * `:root[data-theme="dark"]` — active when the theme-toggle button has
      explicitly selected dark mode.

    The [`color-scheme`][mdn.color-scheme] property on [`.highlight`][pygments.highlight] is also driven by a custom
    property ([`--hl-color-scheme`][css.hl-color-scheme]), derived from the perceived background
    luminance of the chosen Pygments style.  This ensures that the browser's
    [`::selection`][mdn.selection] colours and any inherited text colour remain appropriate
    regardless of the site-wide light/dark mode setting.

    Args:
        light_style: Name of the Pygments style to use in light mode.
        dark_style: Name of the Pygments style to use in dark mode.

    Returns:
        A CSS string suitable for writing to [`code.css`][blogmore.code_css].

    Raises:
        ClassNotFound: If either *light_style* or *dark_style* is not a
            recognised Pygments style name.
    """
    light_parsed = _parse_token_rules(_highlight_rules(light_style))
    dark_parsed = _parse_token_rules(_highlight_rules(dark_style))

    light_colour_scheme = _colour_scheme_for_style(light_style)
    dark_colour_scheme = _colour_scheme_for_style(dark_style)

    # Collect all unique selectors, preserving order (light first, then any
    # dark-only selectors appended at the end).
    all_selectors: list[str] = []
    seen_selectors: set[str] = set()
    for selector in list(light_parsed.keys()) + list(dark_parsed.keys()):
        if selector not in seen_selectors:
            all_selectors.append(selector)
            seen_selectors.add(selector)

    # For each selector, collect all unique CSS properties across both styles,
    # preserving order (light properties first, then any dark-only ones).
    all_props_by_selector: dict[str, list[str]] = {}
    for selector in all_selectors:
        seen_props: set[str] = set()
        all_props: list[str] = []
        for prop in list(light_parsed.get(selector, {}).keys()) + list(
            dark_parsed.get(selector, {}).keys()
        ):
            if prop not in seen_props:
                all_props.append(prop)
                seen_props.add(prop)
        all_props_by_selector[selector] = all_props

    def _var_declarations(
        parsed: dict[str, dict[str, str]], colour_scheme: str
    ) -> list[str]:
        """Return a flat list of CSS custom property declarations for one mode."""
        lines: list[str] = [f"--hl-color-scheme: {colour_scheme};"]
        for selector in all_selectors:
            props = parsed.get(selector, {})
            for prop in all_props_by_selector[selector]:
                # Use "unset" for any property absent in this style so that
                # the property resets cleanly (inherited props → inherit,
                # non-inherited props → initial/transparent).
                value = props.get(prop, "unset")
                lines.append(f"{_css_var_name(selector, prop)}: {value};")
        return lines

    light_vars = _var_declarations(light_parsed, light_colour_scheme)
    dark_vars = _var_declarations(dark_parsed, dark_colour_scheme)

    # Build the actual .highlight selector rules — declared only once, each
    # property value resolved through a CSS custom property.
    rule_lines: list[str] = []
    base_handled = False
    for selector in all_selectors:
        all_props = all_props_by_selector[selector]
        if not all_props:
            continue
        prop_decls = "; ".join(
            f"{prop}: var({_css_var_name(selector, prop)})" for prop in all_props
        )
        if selector == ".highlight":
            rule_lines.append(
                f"{selector} {{ color-scheme: var(--hl-color-scheme); {prop_decls} }}"
            )
            base_handled = True
        else:
            rule_lines.append(f"{selector} {{ {prop_decls} }}")

    if not base_handled:
        rule_lines.insert(0, ".highlight { color-scheme: var(--hl-color-scheme); }")

    parts = [
        "/* Light mode syntax highlighting */",
        ":root {",
        *[f"    {line}" for line in light_vars],
        "}",
        "",
        "/* Dark mode syntax highlighting (system preference) */",
        "@media (prefers-color-scheme: dark) {",
        "    :root:not([data-theme]) {",
        *[f"        {line}" for line in dark_vars],
        "    }",
        "}",
        "",
        "/* Dark mode syntax highlighting (explicit theme toggle) */",
        ':root[data-theme="dark"] {',
        *[f"    {line}" for line in dark_vars],
        "}",
        "",
        "/* Syntax highlighting rules */",
        *rule_lines,
    ]
    return "\n".join(parts) + "\n"


### code_styles.py ends here
