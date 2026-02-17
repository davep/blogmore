"""Command-line interface for blogmore."""

import sys

from blogmore.cli import create_parser
from blogmore.config import load_config, merge_config_with_args
from blogmore.generator import SiteGenerator
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

    # Load configuration file if specified or search for default
    try:
        config = load_config(args.config if hasattr(args, "config") else None)
        merge_config_with_args(config, args)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: Invalid configuration file: {e}", file=sys.stderr)
        return 1

    # Handle serve command
    if args.command in ("serve", "test"):
        return serve_site(
            output_dir=args.output,
            port=args.port,
            content_dir=args.content_dir,
            templates_dir=args.templates,
            site_title=args.site_title,
            site_url=args.site_url,
            include_drafts=args.include_drafts,
            watch=not args.no_watch,
            posts_per_feed=args.posts_per_feed,
            extra_stylesheets=args.extra_stylesheets,
            default_author=args.default_author,
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
                site_url=args.site_url,
                posts_per_feed=args.posts_per_feed,
                extra_stylesheets=args.extra_stylesheets,
                default_author=args.default_author,
            )
            generator.generate(include_drafts=args.include_drafts)
            return 0
        except Exception as e:
            print(f"Error generating site: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
