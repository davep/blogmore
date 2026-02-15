"""Command-line interface for blogmore."""

import argparse
import sys
from pathlib import Path

from blogmore.generator import SiteGenerator


def main() -> int:
    """Main entry point for the blogmore CLI."""
    parser = argparse.ArgumentParser(
        description="Blogmore - A blog-oriented static site generation engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "content_dir",
        type=Path,
        help="Directory containing markdown blog posts",
    )

    parser.add_argument(
        "-t",
        "--templates",
        type=Path,
        default=Path("templates"),
        help="Directory containing Jinja2 templates (default: templates)",
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
        default="My Blog",
        help="Title of the blog site (default: My Blog)",
    )

    parser.add_argument(
        "--site-url",
        default="",
        help="Base URL of the site (optional)",
    )

    parser.add_argument(
        "--include-drafts",
        action="store_true",
        help="Include posts marked as drafts",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="blogmore 0.1.0",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.content_dir.exists():
        print(f"Error: Content directory not found: {args.content_dir}", file=sys.stderr)
        return 1

    if not args.templates.exists():
        print(f"Error: Templates directory not found: {args.templates}", file=sys.stderr)
        return 1

    # Generate the site
    try:
        generator = SiteGenerator(
            content_dir=args.content_dir,
            templates_dir=args.templates,
            output_dir=args.output,
            site_title=args.site_title,
            site_url=args.site_url,
        )
        generator.generate(include_drafts=args.include_drafts)
        return 0
    except Exception as e:
        print(f"Error generating site: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
