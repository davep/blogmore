"""Command-line interface for blogmore."""

import argparse
import sys
from pathlib import Path
from typing import Any

from blogmore.cli import create_parser
from blogmore.config import (
    DEFAULT_CONFIG_FILES,
    get_sidebar_config,
    load_config,
    merge_config_with_args,
    normalize_site_keywords,
)
from blogmore.generator import SiteGenerator
from blogmore.publisher import PublishError, publish_site
from blogmore.server import serve_site


def main() -> int:
    """Main entry point for the blogmore CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Expand user home directory in path arguments from CLI
    if hasattr(args, "content_dir") and args.content_dir is not None:
        args.content_dir = args.content_dir.expanduser()
    if hasattr(args, "templates") and args.templates is not None:
        args.templates = args.templates.expanduser()
    if hasattr(args, "output") and args.output is not None:
        args.output = args.output.expanduser()
    if hasattr(args, "config") and args.config is not None:
        args.config = args.config.expanduser()

    # Store the original CLI argument values before merging with config
    # This will be used to determine which CLI args should override config on reload
    cli_overrides = _extract_cli_overrides(args)

    # Load configuration file if specified or search for default
    config_path = None
    try:
        config_path = _determine_config_path(args)
        config = load_config(config_path)
        merge_config_with_args(config, args)
        sidebar_config = get_sidebar_config(config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: Invalid configuration file: {e}", file=sys.stderr)
        return 1

    # Normalize site_keywords: CLI provides a string, config provides a list or string
    site_keywords = normalize_site_keywords(getattr(args, "site_keywords", None))

    # Handle serve command
    if args.command in ("serve", "test"):
        return serve_site(
            output_dir=args.output,
            port=args.port,
            content_dir=args.content_dir,
            templates_dir=args.templates,
            site_title=args.site_title,
            site_subtitle=args.site_subtitle,
            site_description=args.site_description,
            site_keywords=site_keywords,
            site_url=args.site_url,
            include_drafts=args.include_drafts,
            watch=not args.no_watch,
            posts_per_feed=args.posts_per_feed,
            extra_stylesheets=args.extra_stylesheets,
            default_author=args.default_author,
            sidebar_config=sidebar_config,
            config_path=config_path,
            cli_overrides=cli_overrides,
            clean_first=args.clean_first,
            icon_source=args.icon_source,
            with_search=args.with_search,
            with_sitemap=args.with_sitemap,
        )

    # Handle build command (and its aliases: generate, gen)
    if args.command in ("build", "generate", "gen"):
        # Validate that content_dir is provided
        if args.content_dir is None:
            print(
                "Error: content_dir is required. Specify it on the command line or in the config file.",
                file=sys.stderr,
            )
            return 1

        # Validate inputs
        if not args.content_dir.exists():
            print(
                f"Error: Content directory not found: {args.content_dir}",
                file=sys.stderr,
            )
            return 1

        # Validate templates directory if provided
        if args.templates is not None and not args.templates.exists():
            print(
                f"Error: Templates directory not found: {args.templates}",
                file=sys.stderr,
            )
            return 1

        # Generate the site
        try:
            generator = SiteGenerator(
                content_dir=args.content_dir,
                templates_dir=args.templates,
                output_dir=args.output,
                site_title=args.site_title,
                site_subtitle=args.site_subtitle,
                site_description=args.site_description,
                site_keywords=site_keywords,
                site_url=args.site_url,
                posts_per_feed=args.posts_per_feed,
                extra_stylesheets=args.extra_stylesheets,
                default_author=args.default_author,
                sidebar_config=sidebar_config,
                clean_first=args.clean_first,
                icon_source=args.icon_source,
                with_search=args.with_search,
                with_sitemap=args.with_sitemap,
            )
            generator.generate(include_drafts=args.include_drafts)
            return 0
        except Exception as e:
            print(f"Error generating site: {e}", file=sys.stderr)
            return 1

    # Handle publish command
    if args.command == "publish":
        # Validate that content_dir is provided
        if args.content_dir is None:
            print(
                "Error: content_dir is required. Specify it on the command line or in the config file.",
                file=sys.stderr,
            )
            return 1

        # Validate inputs
        if not args.content_dir.exists():
            print(
                f"Error: Content directory not found: {args.content_dir}",
                file=sys.stderr,
            )
            return 1

        # Validate templates directory if provided
        if args.templates is not None and not args.templates.exists():
            print(
                f"Error: Templates directory not found: {args.templates}",
                file=sys.stderr,
            )
            return 1

        # Generate the site first
        try:
            print("Building site before publishing...")
            generator = SiteGenerator(
                content_dir=args.content_dir,
                templates_dir=args.templates,
                output_dir=args.output,
                site_title=args.site_title,
                site_subtitle=args.site_subtitle,
                site_description=args.site_description,
                site_keywords=site_keywords,
                site_url=args.site_url,
                posts_per_feed=args.posts_per_feed,
                extra_stylesheets=args.extra_stylesheets,
                default_author=args.default_author,
                sidebar_config=sidebar_config,
                clean_first=args.clean_first,
                icon_source=args.icon_source,
                with_search=args.with_search,
                with_sitemap=args.with_sitemap,
            )
            generator.generate(include_drafts=args.include_drafts)
            print("Site built successfully")
        except Exception as e:
            print(f"Error generating site: {e}", file=sys.stderr)
            return 1

        # Publish the site
        try:
            publish_site(
                output_dir=args.output,
                branch=args.branch,
                remote=args.remote,
            )
            return 0
        except PublishError as e:
            print(f"Error publishing site: {e}", file=sys.stderr)
            return 1

    return 0


def _determine_config_path(args: argparse.Namespace) -> Path | None:
    """Determine which config file is being used.

    Args:
        args: Parsed command-line arguments

    Returns:
        Path to the config file being used, or None if no config file
    """
    # If a specific config file is provided, use it
    if hasattr(args, "config") and args.config is not None:
        return Path(args.config)

    # Otherwise, search for default config files
    for config_file in DEFAULT_CONFIG_FILES:
        config_file_path = Path(config_file)
        if config_file_path.exists():
            return config_file_path

    return None


def _extract_cli_overrides(args: argparse.Namespace) -> dict[str, Any]:
    """Extract CLI arguments that were explicitly set (not defaults).

    Args:
        args: Parsed command-line arguments

    Returns:
        Dictionary of argument names to values that were explicitly set
    """
    # Define defaults for each argument
    defaults = {
        "site_title": "My Blog",
        "site_subtitle": "",
        "site_description": "",
        "site_keywords": None,
        "site_url": "",
        "output": Path("output"),
        "templates": None,
        "include_drafts": False,
        "posts_per_feed": 20,
        "extra_stylesheets": None,
        "port": 8000,
        "no_watch": False,
        "content_dir": None,
        "default_author": None,
        "clean_first": False,
        "branch": "gh-pages",
        "remote": "origin",
        "icon_source": None,
        "with_search": False,
        "with_sitemap": False,
    }

    overrides = {}

    # Check each argument to see if it differs from the default
    for arg_name, default_value in defaults.items():
        if not hasattr(args, arg_name):
            continue

        arg_value = getattr(args, arg_name)

        # If the value differs from default, it was explicitly set
        if arg_value != default_value:
            overrides[arg_name] = arg_value

    return overrides


if __name__ == "__main__":
    sys.exit(main())
