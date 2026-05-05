"""Asset management and static file processing for the site generator."""

from __future__ import annotations

import shutil
import urllib.error
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any

import rcssmin  # type: ignore[import-untyped]
import rjsmin  # type: ignore[import-untyped]

from blogmore.code_styles import build_code_css
from blogmore.fontawesome import (
    FONTAWESOME_CDN_CSS_URL,
    FONTAWESOME_LOCAL_CSS_MINIFIED_PATH,
    FONTAWESOME_LOCAL_CSS_PATH,
    FontAwesomeOptimizer,
)
from blogmore.generator.constants import (
    CODE_CSS_FILENAME,
    CODEBLOCKS_JS_FILENAME,
    CSS_FILENAME,
    GRAPH_JS_FILENAME,
    PAGE_SPECIFIC_CSS,
    SEARCH_JS_FILENAME,
    THEME_JS_FILENAME,
)
from blogmore.generator.utils import minified_filename
from blogmore.icons import IconGenerator, detect_source_icon

if TYPE_CHECKING:
    from blogmore.site_config import SiteConfig


class AssetManager:
    """Manages icon generation, static assets, and extras for the site generator."""

    def __init__(self, site_config: SiteConfig) -> None:
        """Initialize the asset manager.

        Args:
            site_config: The site configuration.
        """
        self.site_config = site_config
        self.fontawesome_css_url: str = FONTAWESOME_CDN_CSS_URL
        self.extras_html_paths: frozenset[str] = frozenset()

    @property
    def _content_dir(self) -> Path:
        """Return the content directory as a ``Path``, guaranteed non-``None``.

        Returns:
            The resolved content directory path.
        """
        assert self.site_config.content_dir is not None
        return self.site_config.content_dir

    def detect_favicon(self) -> str | None:
        """Detect if a favicon file exists in the icons or extras directory.

        Checks for favicon files with common extensions in priority order.
        First checks the icons directory (for generated icons), then falls back
        to the extras directory (for manually provided icons).

        Returns:
            The favicon URL (relative to site root) if found, None otherwise
        """
        # First check icons directory (generated icons)
        icons_dir = self.site_config.output_dir / "icons"
        if icons_dir.exists():
            favicon_path = icons_dir / "favicon.ico"
            if favicon_path.is_file():
                return "/icons/favicon.ico"

        # Fall back to extras directory (existing behavior)
        extras_dir = self._content_dir / "extras"
        if not extras_dir.exists():
            return None

        # Common favicon extensions in priority order
        favicon_extensions = [".ico", ".png", ".svg", ".gif", ".jpg", ".jpeg"]

        # Check for favicon files
        for ext in favicon_extensions:
            favicon_path = extras_dir / f"favicon{ext}"
            if favicon_path.is_file():
                return f"/favicon{ext}"

        return None

    def detect_generated_icons(self) -> bool:
        """Detect if generated platform icons exist in the icons directory.

        Returns:
            True if generated icons exist, False otherwise
        """
        icons_dir = self.site_config.output_dir / "icons"
        if not icons_dir.exists():
            return False

        # Check if the main Apple touch icon exists as an indicator
        apple_icon_path = icons_dir / "apple-touch-icon.png"
        return apple_icon_path.is_file()

    def generate_icons(self) -> None:
        """Generate icons from a source image if present."""
        extras_dir = self._content_dir / "extras"

        # Look for a source icon (using configured name if provided)
        source_icon = detect_source_icon(extras_dir, self.site_config.icon_source)

        if source_icon:
            print(f"Found source icon: {source_icon.name}")
            print("Generating favicon and Apple touch icons...")

            # Generate to /icons subdirectory
            icons_output_dir = self.site_config.output_dir / "icons"
            generator = IconGenerator(source_icon, icons_output_dir)
            generated = generator.generate_all()

            if generated:
                print(f"Generated {len(generated)} icon file(s):")
                for icon_name in generated:
                    print(f"  - icons/{icon_name}")

                # Copy favicon.ico to the root for backward compatibility
                if favicon_ico := generated.get("favicon.ico"):
                    shutil.copy2(
                        favicon_ico, self.site_config.output_dir / "favicon.ico"
                    )
                    print("  - favicon.ico (root copy for backward compatibility)")
            else:
                print("Warning: No icons were generated")

    def prepare_fontawesome_css(self) -> str | None:
        """Determine the FontAwesome CSS URL and optionally build optimised CSS.

        Extracts the social icon names from the sidebar configuration and
        attempts to fetch the FontAwesome metadata from GitHub to build a
        minimal CSS file.  Updates ``self.fontawesome_css_url`` with the URL
        that every rendered page will reference.

        Returns:
            The CSS content string to write to disk if optimisation succeeded,
            or ``None`` if no social icons are configured or if the metadata
            fetch failed (in the latter case the full CDN URL is used instead).
        """
        socials: list[Any] = self.site_config.sidebar_config.get("socials", [])
        if not socials:
            # No social icons — no FontAwesome CSS needed at all.
            self.fontawesome_css_url = ""
            return None

        icon_names = [
            str(social["site"])
            for social in socials
            if isinstance(social, dict) and "site" in social
        ]
        optimizer = FontAwesomeOptimizer(icon_names)

        try:
            metadata = optimizer.fetch_icon_metadata()
        except (urllib.error.URLError, ValueError, OSError) as error:
            print(f"Warning: Could not fetch FontAwesome metadata: {error}")
            print("Falling back to full FontAwesome CDN stylesheet.")
            self.fontawesome_css_url = FONTAWESOME_CDN_CSS_URL
            return None

        print("Optimizing FontAwesome CSS...")
        self.fontawesome_css_url = (
            FONTAWESOME_LOCAL_CSS_MINIFIED_PATH
            if self.site_config.minify_css
            else FONTAWESOME_LOCAL_CSS_PATH
        )
        return optimizer.build_css(metadata)

    def _get_asset_source(self, filename: str) -> str | None:
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
        self,
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

    def _write_minified_css(self, output_static: Path) -> None:
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
        for source_filename in PAGE_SPECIFIC_CSS:
            self._minify_one_css(output_static, source_filename)

    def _write_code_css(self, output_static: Path) -> None:
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

    def _write_minified_js(self, output_static: Path, js_filename: str) -> None:
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

    def copy_static_assets(self) -> None:
        """Copy static assets (CSS, JS, images) to output directory.

        When ``minify_css`` is enabled, ``style.css`` and all page-specific
        CSS files are minified; the originals are not written.

        When ``minify_js`` is enabled, the ``theme.js`` file is minified and
        written as ``theme.min.js`` (and ``search.js`` as ``search.min.js`` if
        search is enabled, ``graph.js`` as ``graph.min.js`` if graph is
        enabled); the originals are not written.
        """
        output_static = self.site_config.output_dir / "static"

        # Pre-compute set of CSS source filenames to skip when minifying.
        _css_source_filenames = {CSS_FILENAME} | set(PAGE_SPECIFIC_CSS)

        # Clear output static directory if it exists
        if output_static.exists():
            shutil.rmtree(output_static)
        output_static.mkdir(parents=True, exist_ok=True)

        # First, copy bundled static assets
        try:
            # Get bundled static directory
            bundled_static = files("blogmore").joinpath("templates", "static")
            if bundled_static.is_dir():
                for item in bundled_static.iterdir():
                    if item.is_file():
                        # Only copy search.js when search is enabled
                        if (
                            item.name == SEARCH_JS_FILENAME
                            and not self.site_config.with_search
                        ):
                            continue
                        # Only copy graph.js when graph is enabled
                        if (
                            item.name == GRAPH_JS_FILENAME
                            and not self.site_config.with_graph
                        ):
                            continue
                        # When minifying CSS, skip all source CSS files
                        if (
                            item.name in _css_source_filenames
                            and self.site_config.minify_css
                        ):
                            continue
                        # When minifying JS, skip original JS files
                        if (
                            item.name == THEME_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            item.name == SEARCH_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            item.name == CODEBLOCKS_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            item.name == GRAPH_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        # Read content and write to output
                        content = item.read_bytes()
                        output_file = output_static / item.name
                        output_file.write_bytes(content)
                print("Copied bundled static assets")
        except Exception as e:
            print(f"Warning: Could not copy bundled static assets: {e}")

        # Then, copy custom static assets (if provided), which will override bundled ones
        if self.site_config.templates_dir is not None:
            custom_static_dir = self.site_config.templates_dir / "static"
            if custom_static_dir.exists():
                for item in custom_static_dir.rglob("*"):
                    if item.is_file():
                        relative_path = item.relative_to(custom_static_dir)
                        # When minifying CSS, skip all source CSS files from custom dir
                        if (
                            relative_path.name in _css_source_filenames
                            and self.site_config.minify_css
                        ):
                            continue
                        # When minifying JS, skip original JS files from custom dir too
                        if (
                            relative_path.name == THEME_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            relative_path.name == SEARCH_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            relative_path.name == CODEBLOCKS_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            relative_path.name == GRAPH_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        output_file = output_static / relative_path
                        output_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, output_file)
                print(f"Copied custom static assets from {custom_static_dir}")

        # Minify CSS if requested
        if self.site_config.minify_css:
            self._write_minified_css(output_static)

        # Always generate code.css (or code.min.css) from configured Pygments styles.
        self._write_code_css(output_static)

        # Minify JS if requested
        if self.site_config.minify_js:
            self._write_minified_js(output_static, THEME_JS_FILENAME)
            self._write_minified_js(output_static, CODEBLOCKS_JS_FILENAME)
            if self.site_config.with_search:
                self._write_minified_js(output_static, SEARCH_JS_FILENAME)
            if self.site_config.with_graph:
                self._write_minified_js(output_static, GRAPH_JS_FILENAME)

    def write_fontawesome_css(self, css_content: str) -> None:
        """Write the optimised FontAwesome CSS file to the static directory.

        Must be called *after* [`copy_static_assets`][blogmore.generator.assets.AssetManager.copy_static_assets]
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

    def copy_extras(self) -> None:
        """Copy extra files from the extras directory to the output directory.

        Files in the extras directory are copied to the output root, preserving
        directory structure relative to the extras directory. If a file would
        override an existing file, it is allowed but a message is printed.

        After copying, ``self.extras_html_paths`` is updated with the relative
        paths (forward-slash strings) of every HTML file that was copied.  This
        is used by the sitemap generator to exclude those files from the
        sitemap, since they are not pages generated by BlogMore.
        """
        extras_dir = self._content_dir / "extras"

        if not extras_dir.exists():
            return

        # Count how many extras we copy
        extras_count = 0
        override_count = 0
        failed_count = 0

        # Track relative paths of HTML files copied from extras
        extras_html_paths: set[str] = set()

        # Recursively copy all files from the extras directory
        for file_path in extras_dir.rglob("*"):
            # Skip directories
            if file_path.is_file():
                try:
                    # Calculate relative path from extras directory to preserve structure
                    relative_path = file_path.relative_to(extras_dir)
                    # Copy to output_dir root, preserving directory structure
                    output_path = self.site_config.output_dir / relative_path

                    # Check if file already exists
                    file_exists = output_path.exists()

                    # Create parent directories if they don't exist
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file preserving metadata
                    shutil.copy2(file_path, output_path)
                    extras_count += 1

                    # Track HTML files so they can be excluded from the sitemap
                    relative_str = str(relative_path).replace("\\", "/")
                    if relative_str.endswith(".html"):
                        extras_html_paths.add(relative_str)

                    # Print message if we overrode an existing file
                    if file_exists:
                        print(f"Overriding existing file: {relative_path}")
                        override_count += 1
                except (OSError, PermissionError) as e:
                    print(f"Warning: Failed to copy extra file {file_path}: {e}")
                    failed_count += 1
                    continue

        self.extras_html_paths = frozenset(extras_html_paths)

        if extras_count > 0:
            print(f"Copied {extras_count} extra file(s) from {extras_dir}")
        if override_count > 0:
            print(f"Overrode {override_count} existing file(s)")
        if failed_count > 0:
            print(f"Warning: Failed to copy {failed_count} extra file(s)")
