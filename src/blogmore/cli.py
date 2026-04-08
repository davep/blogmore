"""Command-line interface argument parsing for blogmore."""

import argparse
from pathlib import Path
from typing import Any

from . import __version__
from .site_config import site_config_defaults

# Default values for CLI arguments that also appear in SiteConfig.
# Derived via the central site_config_defaults() function so there is a
# single source of truth.
_SITE_CONFIG_DEFAULTS: dict[str, Any] = site_config_defaults()


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to a parser.

    Args:
        parser: The argument parser to add arguments to
    """
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help="Path to configuration file (default: searches for blogmore.yaml or blogmore.yml)",
    )

    parser.add_argument(
        "-t",
        "--templates",
        type=Path,
        default=None,
        help="Optional directory containing custom Jinja2 templates (uses bundled templates by default)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output"),
        help="Output directory for generated site (default: output)",
    )

    parser.add_argument(
        "--site-title",
        default=_SITE_CONFIG_DEFAULTS["site_title"],
        help="Title of the blog site (default: My Blog)",
    )

    parser.add_argument(
        "--site-subtitle",
        default=_SITE_CONFIG_DEFAULTS["site_subtitle"],
        help="Subtitle of the blog site (optional)",
    )

    parser.add_argument(
        "--site-description",
        default=_SITE_CONFIG_DEFAULTS["site_description"],
        help="Default description for pages that have no description of their own (optional)",
    )

    parser.add_argument(
        "--site-keywords",
        default=_SITE_CONFIG_DEFAULTS["site_keywords"],
        help="Default keywords for pages as a comma-separated list (optional)",
    )

    parser.add_argument(
        "--site-url",
        default=_SITE_CONFIG_DEFAULTS["site_url"],
        help="Base URL of the site (optional)",
    )

    parser.add_argument(
        "--include-drafts",
        action="store_true",
        help="Include posts marked as drafts",
    )

    parser.add_argument(
        "--posts-per-feed",
        type=int,
        default=_SITE_CONFIG_DEFAULTS["posts_per_feed"],
        help="Maximum number of posts to include in feeds (default: 20)",
    )

    parser.add_argument(
        "--extra-stylesheet",
        action="append",
        dest="extra_stylesheets",
        help="URL of an additional stylesheet to include (can be used multiple times)",
    )

    parser.add_argument(
        "--default-author",
        default=_SITE_CONFIG_DEFAULTS["default_author"],
        help="Default author name for posts that don't specify an author",
    )

    parser.add_argument(
        "--clean-first",
        action="store_true",
        help="Remove the output directory before generating the site",
    )

    parser.add_argument(
        "--icon-source",
        type=str,
        default=_SITE_CONFIG_DEFAULTS["icon_source"],
        help="Source icon filename in extras/ directory (e.g., 'my-logo.png')",
    )

    parser.add_argument(
        "--with-search",
        action="store_true",
        default=_SITE_CONFIG_DEFAULTS["with_search"],
        help="Generate a client-side search index and search page (default: disabled)",
    )

    parser.add_argument(
        "--with-sitemap",
        action="store_true",
        default=_SITE_CONFIG_DEFAULTS["with_sitemap"],
        help="Generate an XML sitemap (sitemap.xml) in the output directory (default: disabled)",
    )

    parser.add_argument(
        "--with-stats",
        action="store_true",
        default=_SITE_CONFIG_DEFAULTS["with_stats"],
        help="Generate a blog statistics page (default: disabled)",
    )

    parser.add_argument(
        "--with-calendar",
        action="store_true",
        default=_SITE_CONFIG_DEFAULTS["with_calendar"],
        help="Generate a calendar view of all posts (default: disabled)",
    )

    parser.add_argument(
        "--minify-css",
        action="store_true",
        default=_SITE_CONFIG_DEFAULTS["minify_css"],
        help="Minify the generated CSS, writing it as styles.min.css (default: disabled)",
    )

    parser.add_argument(
        "--minify-js",
        action="store_true",
        default=_SITE_CONFIG_DEFAULTS["minify_js"],
        help="Minify the generated JavaScript, writing as theme.min.js (and search.min.js if search enabled)",
    )

    parser.add_argument(
        "--minify-html",
        action="store_true",
        default=_SITE_CONFIG_DEFAULTS["minify_html"],
        help="Minify all generated HTML output in place (default: disabled)",
    )

    parser.add_argument(
        "--with-read-time",
        action="store_true",
        default=_SITE_CONFIG_DEFAULTS["with_read_time"],
        help="Show estimated reading time on posts (default: disabled)",
    )

    parser.add_argument(
        "--socials-title",
        default="Social",
        help="Title for the social media icons section in the sidebar (default: Social)",
    )

    parser.add_argument(
        "--links-title",
        default="Links",
        help="Title for the links section in the sidebar (default: Links)",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for blogmore.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Blogmore - A blog-oriented static site generation engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Add subparsers for different commands
    subparsers = parser.add_subparsers(
        dest="command", help="Command to run", required=True
    )

    # Build command (primary) with generate and gen as aliases
    build_parser = subparsers.add_parser(
        "build",
        help="Generate the static site",
        aliases=["generate", "gen"],
    )

    build_parser.add_argument(
        "content_dir",
        type=Path,
        nargs="?",
        help="Directory containing markdown blog posts",
    )

    add_common_arguments(build_parser)

    # Serve command with test as alias
    serve_parser = subparsers.add_parser(
        "serve",
        help="Generate (if needed) and serve the site locally, watching for changes",
        aliases=["test"],
    )

    serve_parser.add_argument(
        "content_dir",
        type=Path,
        nargs="?",
        help="Directory containing markdown blog posts (optional, triggers generation)",
    )

    serve_parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Port to serve on (default: 8000)",
    )

    serve_parser.add_argument(
        "--no-watch",
        action="store_true",
        help="Disable watching for changes (default: watch enabled)",
    )

    add_common_arguments(serve_parser)

    # Publish command
    publish_parser = subparsers.add_parser(
        "publish",
        help="Build the site and publish it to a git branch (e.g., gh-pages)",
    )

    publish_parser.add_argument(
        "content_dir",
        type=Path,
        nargs="?",
        help="Directory containing markdown blog posts",
    )

    publish_parser.add_argument(
        "--branch",
        default="gh-pages",
        help="Git branch to publish to (default: gh-pages)",
    )

    publish_parser.add_argument(
        "--remote",
        default="origin",
        help="Git remote to push to (default: origin)",
    )

    add_common_arguments(publish_parser)

    parser.add_argument(
        "--version",
        action="version",
        version=f"blogmore {__version__}",
    )

    return parser
