"""HTML writing and minification helpers for the site generator."""

from pathlib import Path

import minify_html


def write_html(output_path: Path, html: str, minify: bool = False) -> None:
    """Write an HTML string to a file, optionally minifying it.

    When *minify* is enabled the HTML content is passed through the
    ``minify-html`` library before being written.  The output file name is
    not changed — only the content is minified.

    Args:
        output_path: Destination file path.
        html: HTML content to write.
        minify: Whether to minify the HTML content.
    """
    if minify:
        html = minify_html.minify(html, minify_js=False, minify_css=False)
    output_path.write_text(html, encoding="utf-8")
