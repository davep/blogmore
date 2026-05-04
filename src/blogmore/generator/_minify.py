"""Mixin providing HTML writing and CSS/JS minification helpers for
[`SiteGenerator`][blogmore.generator.site.SiteGenerator].
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

import minify_html
import rcssmin  # type: ignore[import-untyped]
import rjsmin  # type: ignore[import-untyped]

from blogmore.code_styles import build_code_css
from blogmore.generator.constants import (
    _PAGE_SPECIFIC_CSS,
    CODE_CSS_FILENAME,
    CSS_FILENAME,
)
from blogmore.generator.utils import minified_filename

if TYPE_CHECKING:
    from blogmore.generator._protocol import GeneratorProtocol


class MinifyMixin:
    """Mixin that writes HTML pages and minifies CSS/JS assets.

    This mixin is intended to be composed into
    [`SiteGenerator`][blogmore.generator.site.SiteGenerator] (via
    [`AssetsMixin`][blogmore.generator._assets.AssetsMixin]).
    """

    def _write_html(self: GeneratorProtocol, output_path: Path, html: str) -> None:
        """Write an HTML string to a file, minifying it when configured to do so.

        When ``minify_html`` is enabled the HTML content is passed through the
        ``minify-html`` library before being written.  The output file name is
        not changed — only the content is minified.

        Args:
            output_path: Destination file path.
            html: HTML content to write.
        """
        if self.site_config.minify_html:
            html = minify_html.minify(html, minify_js=False, minify_css=False)
        output_path.write_text(html, encoding="utf-8")

    def _get_asset_source(self: GeneratorProtocol, filename: str) -> str | None:
        """Read the text content of a static asset, preferring custom over bundled.

        Looks first in the custom templates directory (``templates_dir/static/``)
        when one is configured, then falls back to the package's bundled templates.
        Returns ``None`` and emits a warning if the asset cannot be found.

        Args:
            filename: The asset filename to look up (e.g. ``"style.css"``).

        Returns:
            The text content of the asset, or ``None`` if it could not be read.
        """
        if self.site_config.templates_dir is not None:
            custom_path = self.site_config.templates_dir / "static" / filename
            if custom_path.is_file():
                return custom_path.read_text(encoding="utf-8")

        try:
            bundled = files("blogmore").joinpath("templates", "static", filename)
            return bundled.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Warning: Could not read bundled {filename} for minification: {e}")
            return None

    def _minify_one_css(
        self: GeneratorProtocol,
        output_static: Path,
        source_filename: str,
    ) -> None:
        """Read one source CSS file, minify it, and write the minified output.

        The source CSS is read from the custom templates directory (if
        available) or from the bundled templates.  The minified output filename
        is derived from *source_filename* via
        [`minified_filename`][blogmore.generator.utils.minified_filename] and written
        to ``output_static/<minified_name>``.

        Args:
            output_static: Path to the output static directory.
            source_filename: Source CSS filename (e.g. ``style.css``).
        """
        css_source = self._get_asset_source(source_filename)
        if css_source is None:
            return

        minified_name = minified_filename(source_filename)
        minified = rcssmin.cssmin(css_source)
        output_path = output_static / minified_name
        output_path.write_text(minified, encoding="utf-8")
        print(f"Generated minified CSS as {minified_name}")

    def _write_minified_css(self: GeneratorProtocol, output_static: Path) -> None:
        """Minify all CSS files and write them to the output static directory.

        Minifies the main stylesheet (``style.css`` → ``style.min.css``) and
        each of the page-specific stylesheets (``search.css``, ``stats.css``,
        ``archive.css``, ``tag-cloud.css``).  The source CSS for each file is
        read from the custom templates directory (if configured) or from the
        bundled templates.

        Args:
            output_static: Path to the output static directory.
        """
        self._minify_one_css(output_static, CSS_FILENAME)
        for source_filename in _PAGE_SPECIFIC_CSS:
            self._minify_one_css(output_static, source_filename)

    def _write_code_css(self: GeneratorProtocol, output_static: Path) -> None:
        """Generate and write the code syntax highlighting CSS file.

        Builds a ``code.css`` (or ``code.min.css`` when ``minify_css`` is
        enabled) from the Pygments styles configured in ``light_mode_code_style``
        and ``dark_mode_code_style``.  The file is always regenerated from the
        configured styles, even when the default styles are in use, so that the
        output is self-contained and does not depend on any hardcoded CSS rules
        in the main stylesheet.

        Args:
            output_static: Path to the output static directory.
        """
        css_content = build_code_css(
            self.site_config.light_mode_code_style,
            self.site_config.dark_mode_code_style,
        )
        if self.site_config.minify_css:
            minified = rcssmin.cssmin(css_content)
            code_css_min = minified_filename(CODE_CSS_FILENAME)
            output_path = output_static / code_css_min
            output_path.write_text(minified, encoding="utf-8")
            print(f"Generated minified code CSS as {code_css_min}")
        else:
            output_path = output_static / CODE_CSS_FILENAME
            output_path.write_text(css_content, encoding="utf-8")
            print(f"Generated code CSS as {CODE_CSS_FILENAME}")

    def _write_minified_js(
        self: GeneratorProtocol, output_static: Path, js_filename: str
    ) -> None:
        """Read a source JavaScript file, minify it, and write it with the minified name.

        The source JS is read from the custom templates directory (if
        available) or from the bundled templates.  The minified output filename
        is derived from *js_filename* via
        [`minified_filename`][blogmore.generator.utils.minified_filename] and written
        to ``output_static/<minified_name>``.

        Args:
            output_static: Path to the output static directory.
            js_filename: The original JavaScript filename (e.g. ``theme.js``).
        """
        js_source = self._get_asset_source(js_filename)
        if js_source is None:
            return

        js_min = minified_filename(js_filename)
        minified = rjsmin.jsmin(js_source)
        output_path = output_static / js_min
        output_path.write_text(minified, encoding="utf-8")
        print(f"Generated minified JS as {js_min}")

    def _write_fontawesome_css(self: GeneratorProtocol, css_content: str) -> None:
        """Write the optimised FontAwesome CSS file to the static directory.

        Must be called *after*
        [`_copy_static_assets`][blogmore.generator._assets.AssetsMixin._copy_static_assets]
        so the file is not overwritten.  When ``minify_css`` is enabled the
        content is minified and written as ``fontawesome.min.css``; otherwise
        it is written as ``fontawesome.css``.

        Args:
            css_content: CSS text to write.
        """
        static_dir = self.site_config.output_dir / "static"
        static_dir.mkdir(parents=True, exist_ok=True)
        if self.site_config.minify_css:
            minified = rcssmin.cssmin(css_content)
            fa_min = minified_filename("fontawesome.css")
            css_path = static_dir / fa_min
            css_path.write_text(minified, encoding="utf-8")
            print(f"Generated minified FontAwesome CSS as {fa_min}")
        else:
            css_path = static_dir / "fontawesome.css"
            css_path.write_text(css_content, encoding="utf-8")
            print("Generated optimized FontAwesome CSS")


### _minify.py ends here
