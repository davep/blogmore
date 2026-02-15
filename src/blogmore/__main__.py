"""Command-line interface for blogmore."""

import argparse
import http.server
import socketserver
import sys
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from blogmore.generator import SiteGenerator


class ReusingTCPServer(socketserver.TCPServer):
    """TCP server that allows address reuse.

    This prevents "Address already in use" errors when restarting the server
    quickly after it has been stopped.
    """

    allow_reuse_address = True


class ContentChangeHandler(FileSystemEventHandler):
    """Handle file system events for content changes."""

    def __init__(
        self,
        generator: SiteGenerator,
        include_drafts: bool = False,
        debounce_seconds: float = 0.5,
    ) -> None:
        """
        Initialize the content change handler.

        Args:
            generator: The site generator to use for regeneration
            include_drafts: Whether to include drafts in generation
            debounce_seconds: Time to wait before regenerating after a change
        """
        super().__init__()
        self.generator = generator
        self.include_drafts = include_drafts
        self.debounce_seconds = debounce_seconds
        self._last_regenerate_time = 0.0
        self._regenerate_lock = threading.Lock()

    def on_any_event(self, event: FileSystemEvent) -> None:
        """
        Handle any file system event.

        Args:
            event: The file system event
        """
        # Ignore directory events and temporary files
        if event.is_directory:
            return

        # Ignore hidden files and common temporary files
        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode("utf-8")
        path = Path(src_path)
        if path.name.startswith(".") or path.name.endswith(
            ("~", ".swp", ".tmp", ".pyc")
        ):
            return

        # Debounce: only regenerate if enough time has passed
        current_time = time.time()
        with self._regenerate_lock:
            if current_time - self._last_regenerate_time < self.debounce_seconds:
                return
            self._last_regenerate_time = current_time

        print(f"\nDetected change in {path}, regenerating site...")
        try:
            self.generator.generate(include_drafts=self.include_drafts)
            print("Regeneration complete!")
        except Exception as e:
            print(f"Error during regeneration: {e}", file=sys.stderr)


def serve_site(
    output_dir: Path,
    port: int = 8000,
    content_dir: Path | None = None,
    templates_dir: Path | None = None,
    site_title: str = "My Blog",
    site_url: str = "",
    include_drafts: bool = False,
    watch: bool = True,
    posts_per_feed: int = 20,
) -> int:
    """
    Serve the generated site locally using a simple HTTP server.

    Args:
        output_dir: Directory containing the generated site
        port: Port to serve on (default: 8000)
        content_dir: Directory containing markdown posts (optional, for generation)
        templates_dir: Directory containing templates (optional, for generation)
        site_title: Title of the blog site
        site_url: Base URL of the site
        include_drafts: Whether to include drafts
        watch: Whether to watch for changes and regenerate (default: True)
        posts_per_feed: Maximum number of posts to include in feeds (default: 20)

    Returns:
        Exit code
    """
    # Generate the site if content_dir is provided or output doesn't exist
    generator = None
    observer = None

    if content_dir is not None:
        # Validate content directory
        if not content_dir.exists():
            print(
                f"Error: Content directory not found: {content_dir}",
                file=sys.stderr,
            )
            return 1

        # Set templates directory default if not provided
        if templates_dir is None:
            templates_dir = Path("templates")

        # Validate templates directory
        if not templates_dir.exists():
            print(
                f"Error: Templates directory not found: {templates_dir}",
                file=sys.stderr,
            )
            return 1

        # Convert to absolute paths before changing directory
        content_dir = content_dir.resolve()
        templates_dir = templates_dir.resolve()
        output_dir = output_dir.resolve()

        # Generate the site
        print(f"Generating site from {content_dir}...")
        try:
            generator = SiteGenerator(
                content_dir=content_dir,
                templates_dir=templates_dir,
                output_dir=output_dir,
                site_title=site_title,
                site_url=site_url,
                posts_per_feed=posts_per_feed,
            )
            generator.generate(include_drafts=include_drafts)
        except Exception as e:
            print(f"Error generating site: {e}", file=sys.stderr)
            return 1

        # Set up file watching if requested
        if watch:
            observer = Observer()
            handler = ContentChangeHandler(generator, include_drafts=include_drafts)

            # Watch content directory
            observer.schedule(handler, str(content_dir), recursive=True)

            # Watch templates directory
            observer.schedule(handler, str(templates_dir), recursive=True)

            observer.start()
            print(f"Watching for changes in {content_dir} and {templates_dir}...")
    elif not output_dir.exists():
        print(
            f"Error: Output directory not found: {output_dir}\n"
            f"Please provide a content directory to generate the site:\n"
            f"  blogmore serve <content_dir> [options]",
            file=sys.stderr,
        )
        return 1

    # Change to the output directory
    import os

    os.chdir(output_dir)

    # Create a simple HTTP server
    http_handler = http.server.SimpleHTTPRequestHandler

    try:
        with ReusingTCPServer(("", port), http_handler) as httpd:
            print(f"Serving site at http://localhost:{port}/")
            print("Press Ctrl+C to stop the server")
            try:
                httpd.serve_forever()
            finally:
                # Ensure cleanup happens regardless of how we exit
                if observer is not None:
                    observer.stop()
                    observer.join()
    except KeyboardInterrupt:
        print("\nServer stopped")
    except OSError as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        return 1

    return 0


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
            "--posts-per-feed",
            type=int,
            default=20,
            help="Maximum number of posts to include in feeds (default: 20)",
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
                posts_per_feed=args.posts_per_feed,
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

    gen_parser.add_argument(
        "--posts-per-feed",
        type=int,
        default=20,
        help="Maximum number of posts to include in feeds (default: 20)",
    )

    # Serve command
    serve_parser = subparsers.add_parser(
        "serve",
        help="Generate (if needed) and serve the site locally, watching for changes",
    )

    serve_parser.add_argument(
        "content_dir",
        type=Path,
        nargs="?",
        help="Directory containing markdown blog posts (optional, triggers generation)",
    )

    serve_parser.add_argument(
        "-t",
        "--templates",
        type=Path,
        default=Path("templates"),
        help="Directory containing Jinja2 templates (default: templates)",
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

    serve_parser.add_argument(
        "--site-title",
        default="My Blog",
        help="Title of the blog site (default: My Blog)",
    )

    serve_parser.add_argument(
        "--site-url",
        default="",
        help="Base URL of the site (optional)",
    )

    serve_parser.add_argument(
        "--include-drafts",
        action="store_true",
        help="Include posts marked as drafts",
    )

    serve_parser.add_argument(
        "--posts-per-feed",
        type=int,
        default=20,
        help="Maximum number of posts to include in feeds (default: 20)",
    )

    serve_parser.add_argument(
        "--no-watch",
        action="store_true",
        help="Disable watching for changes (default: watch enabled)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="blogmore 0.1.0",
    )

    args = parser.parse_args()

    # Handle serve command
    if args.command == "serve":
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
        )

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
                posts_per_feed=args.posts_per_feed,
            )
            generator.generate(include_drafts=args.include_drafts)
            return 0
        except Exception as e:
            print(f"Error generating site: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
