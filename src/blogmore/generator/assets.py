"""Asset handling for the site generator (icons, CSS, JS, etc.)."""

import shutil
import urllib.error
from importlib.resources import files
from pathlib import Path
from typing import Any

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
from blogmore.site_config import SiteConfig


def detect_favicon(site_config: SiteConfig, content_dir: Path) -> str | None:
    """Detect if a favicon file exists in the icons or extras directory."""
    # First check icons directory (generated icons)
    icons_dir = site_config.output_dir / "icons"
    if icons_dir.exists():
        favicon_path = icons_dir / "favicon.ico"
        if favicon_path.is_file():
            return "/icons/favicon.ico"

    # Fall back to extras directory
    extras_dir = content_dir / "extras"
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


def detect_generated_icons(site_config: SiteConfig) -> bool:
    """Detect if generated platform icons exist in the icons directory."""
    icons_dir = site_config.output_dir / "icons"
    if not icons_dir.exists():
        return False

    # Check if the main Apple touch icon exists as an indicator
    apple_icon_path = icons_dir / "apple-touch-icon.png"
    return apple_icon_path.is_file()


def generate_icons(site_config: SiteConfig, content_dir: Path) -> None:
    """Generate icons from a source image if present."""
    extras_dir = content_dir / "extras"

    # Look for a source icon (using configured name if provided)
    source_icon = detect_source_icon(extras_dir, site_config.icon_source)

    if source_icon:
        print(f"Found source icon: {source_icon.name}")
        print("Generating favicon and Apple touch icons...")

        # Generate to /icons subdirectory
        icons_output_dir = site_config.output_dir / "icons"
        generator = IconGenerator(source_icon, icons_output_dir)
        generated = generator.generate_all()

        if generated:
            print(f"Generated {len(generated)} icon file(s):")
            for icon_name in generated:
                print(f"  - icons/{icon_name}")

            # Copy favicon.ico to the root for backward compatibility
            if favicon_ico := generated.get("favicon.ico"):
                shutil.copy2(favicon_ico, site_config.output_dir / "favicon.ico")
                print("  - favicon.ico (root copy for backward compatibility)")
        else:
            print("Warning: No icons were generated")


def prepare_fontawesome_css(
    site_config: SiteConfig,
) -> tuple[str | None, str]:
    """Determine the FontAwesome CSS URL and optionally build optimised CSS.

    Returns:
        A tuple of (css_content, css_url).  css_content is None if optimization
        failed or is not needed.
    """
    socials: list[Any] = site_config.sidebar_config.get("socials", [])
    if not socials:
        return None, ""

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
        return None, FONTAWESOME_CDN_CSS_URL

    print("Optimizing FontAwesome CSS...")
    css_url = (
        FONTAWESOME_LOCAL_CSS_MINIFIED_PATH
        if site_config.minify_css
        else FONTAWESOME_LOCAL_CSS_PATH
    )
    return optimizer.build_css(metadata), css_url


def write_fontawesome_css(site_config: SiteConfig, css_content: str) -> None:
    """Write the optimised FontAwesome CSS file to the static directory."""
    static_dir = site_config.output_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    if site_config.minify_css:
        minified = rcssmin.cssmin(css_content)
        fa_min = minified_filename("fontawesome.css")
        css_path = static_dir / fa_min
        css_path.write_text(minified, encoding="utf-8")
        print(f"Generated minified FontAwesome CSS as {fa_min}")
    else:
        css_path = static_dir / "fontawesome.css"
        css_path.write_text(css_content, encoding="utf-8")
        print("Generated optimized FontAwesome CSS")


def get_asset_source(site_config: SiteConfig, filename: str) -> str | None:
    """Read the text content of a static asset, preferring custom over bundled."""
    if site_config.templates_dir is not None:
        custom_path = site_config.templates_dir / "static" / filename
        if custom_path.is_file():
            return custom_path.read_text(encoding="utf-8")

    try:
        bundled = files("blogmore").joinpath("templates", "static", filename)
        return bundled.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: Could not read bundled {filename} for minification: {e}")
        return None


def minify_one_css(
    site_config: SiteConfig,
    output_static: Path,
    source_filename: str,
) -> None:
    """Read one source CSS file, minify it, and write the minified output."""
    css_source = get_asset_source(site_config, source_filename)
    if css_source is None:
        return

    minified_name = minified_filename(source_filename)
    minified = rcssmin.cssmin(css_source)
    output_path = output_static / minified_name
    output_path.write_text(minified, encoding="utf-8")
    print(f"Generated minified CSS as {minified_name}")


def write_minified_css(site_config: SiteConfig, output_static: Path) -> None:
    """Minify all CSS files and write them to the output static directory."""
    minify_one_css(site_config, output_static, CSS_FILENAME)
    for source_filename in PAGE_SPECIFIC_CSS:
        minify_one_css(site_config, output_static, source_filename)


def write_code_css(site_config: SiteConfig, output_static: Path) -> None:
    """Generate and write the code syntax highlighting CSS file."""
    css_content = build_code_css(
        site_config.light_mode_code_style,
        site_config.dark_mode_code_style,
    )
    if site_config.minify_css:
        minified = rcssmin.cssmin(css_content)
        code_css_min = minified_filename(CODE_CSS_FILENAME)
        output_path = output_static / code_css_min
        output_path.write_text(minified, encoding="utf-8")
        print(f"Generated minified code CSS as {code_css_min}")
    else:
        output_path = output_static / CODE_CSS_FILENAME
        output_path.write_text(css_content, encoding="utf-8")
        print(f"Generated code CSS as {CODE_CSS_FILENAME}")


def write_minified_js(
    site_config: SiteConfig, output_static: Path, js_filename: str
) -> None:
    """Read a source JavaScript file, minify it, and write it with the minified name."""
    js_source = get_asset_source(site_config, js_filename)
    if js_source is None:
        return

    js_min = minified_filename(js_filename)
    minified = rjsmin.jsmin(js_source)
    output_path = output_static / js_min
    output_path.write_text(minified, encoding="utf-8")
    print(f"Generated minified JS as {js_min}")


def copy_static_assets(site_config: SiteConfig) -> None:
    """Copy static assets (CSS, JS, images) to output directory."""
    output_static = site_config.output_dir / "static"

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
                    if item.name == SEARCH_JS_FILENAME and not site_config.with_search:
                        continue
                    # Only copy graph.js when graph is enabled
                    if item.name == GRAPH_JS_FILENAME and not site_config.with_graph:
                        continue
                    # When minifying CSS, skip all source CSS files
                    if item.name in _css_source_filenames and site_config.minify_css:
                        continue
                    # When minifying JS, skip original JS files
                    if item.name == THEME_JS_FILENAME and site_config.minify_js:
                        continue
                    if item.name == SEARCH_JS_FILENAME and site_config.minify_js:
                        continue
                    if item.name == CODEBLOCKS_JS_FILENAME and site_config.minify_js:
                        continue
                    if item.name == GRAPH_JS_FILENAME and site_config.minify_js:
                        continue
                    # Read content and write to output
                    content = item.read_bytes()
                    output_file = output_static / item.name
                    output_file.write_bytes(content)
            print("Copied bundled static assets")
    except Exception as e:
        print(f"Warning: Could not copy bundled static assets: {e}")

    # Then, copy custom static assets (if provided), which will override bundled ones
    if site_config.templates_dir is not None:
        custom_static_dir = site_config.templates_dir / "static"
        if custom_static_dir.exists():
            for item in custom_static_dir.rglob("*"):
                if item.is_file():
                    relative_path = item.relative_to(custom_static_dir)
                    # When minifying CSS, skip all source CSS files from custom dir
                    if (
                        relative_path.name in _css_source_filenames
                        and site_config.minify_css
                    ):
                        continue
                    # When minifying JS, skip original JS files from custom dir too
                    if (
                        relative_path.name == THEME_JS_FILENAME
                        and site_config.minify_js
                    ):
                        continue
                    if (
                        relative_path.name == SEARCH_JS_FILENAME
                        and site_config.minify_js
                    ):
                        continue
                    if (
                        relative_path.name == CODEBLOCKS_JS_FILENAME
                        and site_config.minify_js
                    ):
                        continue
                    if (
                        relative_path.name == GRAPH_JS_FILENAME
                        and site_config.minify_js
                    ):
                        continue
                    output_file = output_static / relative_path
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, output_file)
            print(f"Copied custom static assets from {custom_static_dir}")

    # Minify CSS if requested
    if site_config.minify_css:
        write_minified_css(site_config, output_static)

    # Always generate code.css (or code.min.css) from configured Pygments styles.
    write_code_css(site_config, output_static)

    # Minify JS if requested
    if site_config.minify_js:
        write_minified_js(site_config, output_static, THEME_JS_FILENAME)
        write_minified_js(site_config, output_static, CODEBLOCKS_JS_FILENAME)
        if site_config.with_search:
            write_minified_js(site_config, output_static, SEARCH_JS_FILENAME)
        if site_config.with_graph:
            write_minified_js(site_config, output_static, GRAPH_JS_FILENAME)


def copy_extras(site_config: SiteConfig, content_dir: Path) -> frozenset[str]:
    """Copy extra files from the extras directory to the output directory.

    Returns:
        A frozenset of relative paths of HTML files copied.
    """
    extras_dir = content_dir / "extras"

    if not extras_dir.exists():
        return frozenset()

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
                output_path = site_config.output_dir / relative_path

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

    if extras_count > 0:
        print(f"Copied {extras_count} extra file(s) from {extras_dir}")
    if override_count > 0:
        print(f"Overrode {override_count} existing file(s)")
    if failed_count > 0:
        print(f"Warning: Failed to copy {failed_count} extra file(s)")

    return frozenset(extras_html_paths)
