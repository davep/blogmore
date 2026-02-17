"""Local server and file watching functionality for blogmore."""

import http.server
import os
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


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that gracefully handles client disconnections.

    This handler catches BrokenPipeError and ConnectionResetError exceptions
    that occur when clients disconnect before the server finishes sending data.
    This is common behavior in web servers and should not produce error traces.

    Uses HTTP/1.1 to enable keep-alive connections, which significantly improves
    performance in browsers like Safari that make many parallel requests.
    """

    # Enable HTTP/1.1 for persistent connections (keep-alive)
    # This prevents Safari from having to establish new TCP connections
    # for every resource request, which was causing severe slowdowns.
    protocol_version = "HTTP/1.1"

    def handle(self) -> None:
        """Handle a single HTTP request, catching connection errors."""
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected before we finished sending data.
            # This is normal behavior and not an error condition.
            pass


class ContentChangeHandler(FileSystemEventHandler):
    """Handle file system events for content changes."""

    def __init__(
        self,
        generator: SiteGenerator,
        include_drafts: bool = False,
        debounce_seconds: float = 0.5,
    ) -> None:
        """Initialize the content change handler.

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
        """Handle any file system event.

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
    extra_stylesheets: list[str] | None = None,
    default_author: str | None = None,
) -> int:
    """Serve the generated site locally using a simple HTTP server.

    Args:
        output_dir: Directory containing the generated site
        port: Port to serve on (default: 8000)
        content_dir: Directory containing markdown posts (optional, for generation)
        templates_dir: Optional directory containing custom templates.
                      If not provided, uses bundled templates.
        site_title: Title of the blog site
        site_url: Base URL of the site
        include_drafts: Whether to include drafts
        watch: Whether to watch for changes and regenerate (default: True)
        posts_per_feed: Maximum number of posts to include in feeds (default: 20)
        extra_stylesheets: Optional list of URLs for additional stylesheets
        default_author: Default author name for posts without author in frontmatter

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

        # Validate templates directory if provided
        if templates_dir is not None and not templates_dir.exists():
            print(
                f"Error: Templates directory not found: {templates_dir}",
                file=sys.stderr,
            )
            return 1

        # Convert to absolute paths before changing directory
        content_dir = content_dir.resolve()
        if templates_dir is not None:
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
                extra_stylesheets=extra_stylesheets,
                default_author=default_author,
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

            # Watch templates directory if custom templates are provided
            if templates_dir is not None:
                observer.schedule(handler, str(templates_dir), recursive=True)
                print(f"Watching for changes in {content_dir} and {templates_dir}...")
            else:
                print(f"Watching for changes in {content_dir}...")

            observer.start()
    elif not output_dir.exists():
        print(
            f"Error: Output directory not found: {output_dir}\n"
            f"Please provide a content directory to generate the site:\n"
            f"  blogmore serve <content_dir> [options]",
            file=sys.stderr,
        )
        return 1

    # Change to the output directory
    os.chdir(output_dir)

    # Create a simple HTTP server with our custom handler
    http_handler = QuietHTTPRequestHandler

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
