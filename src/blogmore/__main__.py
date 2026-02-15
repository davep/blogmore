"""Command-line interface for blogmore."""

import argparse
import http.server
import socketserver
import sys
from pathlib import Path

from blogmore.generator import SiteGenerator


def serve_site(output_dir: Path, port: int = 8000) -> int:
    """
    Serve the generated site locally using a simple HTTP server.

    Args:
        output_dir: Directory containing the generated site
        port: Port to serve on (default: 8000)

    Returns:
        Exit code
    """
    if not output_dir.exists():
        print(
            f"Error: Output directory not found: {output_dir}\n"
            f"Please generate the site first using: blogmore <content_dir>",
            file=sys.stderr,
        )
        return 1

    # Change to the output directory
    import os

    os.chdir(output_dir)

    # Create a simple HTTP server
    handler = http.server.SimpleHTTPRequestHandler

    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"Serving site at http://localhost:{port}/")
            print("Press Ctrl+C to stop the server")
            httpd.serve_forever()
            return 0  # This line is never reached but needed for type checking
    except KeyboardInterrupt:
        print("\nServer stopped")
        return 0
    except OSError as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for the blogmore CLI."""
    # Check if first argument looks like a subcommand
    import sys as sys_module

    has_subcommand = len(sys_module.argv) > 1 and sys_module.argv[1] in (
        "generate",
        "gen",
        "build",
        "serve",
        "-h",
        "--help",
        "--version",
    )

    if not has_subcommand:
        # Legacy mode: assume direct path to content directory
        parser = argparse.ArgumentParser(
            description="Blogmore - A blog-oriented static site generation engine",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="For more options, use: blogmore generate --help",
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
            print(
                f"Error: Content directory not found: {args.content_dir}",
                file=sys.stderr,
            )
            return 1

        if not args.templates.exists():
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
            )
            generator.generate(include_drafts=args.include_drafts)
            return 0
        except Exception as e:
            print(f"Error generating site: {e}", file=sys.stderr)
            return 1

    # Subcommand mode
    parser = argparse.ArgumentParser(
        description="Blogmore - A blog-oriented static site generation engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Add subparsers for different commands
    subparsers = parser.add_subparsers(
        dest="command", help="Command to run", required=True
    )

    # Generate command (default)
    gen_parser = subparsers.add_parser(
        "generate", help="Generate the static site (default)", aliases=["gen", "build"]
    )

    gen_parser.add_argument(
        "content_dir",
        type=Path,
        help="Directory containing markdown blog posts",
    )

    gen_parser.add_argument(
        "-t",
        "--templates",
        type=Path,
        default=Path("templates"),
        help="Directory containing Jinja2 templates (default: templates)",
    )

    gen_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output"),
        help="Output directory for generated site (default: output)",
    )

    gen_parser.add_argument(
        "--site-title",
        default="My Blog",
        help="Title of the blog site (default: My Blog)",
    )

    gen_parser.add_argument(
        "--site-url",
        default="",
        help="Base URL of the site (optional)",
    )

    gen_parser.add_argument(
        "--include-drafts",
        action="store_true",
        help="Include posts marked as drafts",
    )

    # Serve command
    serve_parser = subparsers.add_parser(
        "serve", help="Serve the generated site locally"
    )

    serve_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output"),
        help="Output directory with generated site (default: output)",
    )

    serve_parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Port to serve on (default: 8000)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="blogmore 0.1.0",
    )

    args = parser.parse_args()

    # Handle serve command
    if args.command == "serve":
        return serve_site(args.output, args.port)

    # Handle generate command
    if args.command in ("generate", "gen", "build"):
        # Validate inputs
        if not args.content_dir.exists():
            print(
                f"Error: Content directory not found: {args.content_dir}",
                file=sys.stderr,
            )
            return 1

        if not args.templates.exists():
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
            )
            generator.generate(include_drafts=args.include_drafts)
            return 0
        except Exception as e:
            print(f"Error generating site: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
