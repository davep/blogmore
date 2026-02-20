"""Local server and file watching functionality for blogmore."""

import functools
import http.server
import socketserver
import sys
import threading
import time
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from blogmore.config import get_sidebar_config, load_config
from blogmore.generator import SiteGenerator


class ReusingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Multi-threaded TCP server that allows address reuse.

    This prevents "Address already in use" errors when restarting the server
    quickly after it has been stopped.

    ThreadingMixIn enables the server to handle multiple connections concurrently,
    which is essential for HTTP/1.1 keep-alive connections. Without threading,
    the server would block on each connection, severely degrading performance.
    """

    allow_reuse_address = True
    daemon_threads = True  # Allow daemon threads for clean shutdown


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


class ConfigChangeHandler(FileSystemEventHandler):
    """Handle file system events for configuration file changes."""

    def __init__(
        self,
        config_path: Path,
        generator: SiteGenerator,
        include_drafts: bool,
        cli_overrides: dict[str, Any],
        debounce_seconds: float = 0.5,
    ) -> None:
        """Initialize the config change handler.

        Args:
            config_path: Path to the configuration file being watched
            generator: The site generator to use for regeneration
            include_drafts: Whether to include drafts in generation
            cli_overrides: Dictionary of CLI arguments that should override config
            debounce_seconds: Time to wait before regenerating after a change
        """
        super().__init__()
        self.config_path = config_path.resolve()
        self.generator = generator
        self.include_drafts = include_drafts
        self.cli_overrides = cli_overrides
        self.debounce_seconds = debounce_seconds
        self._last_regenerate_time = 0.0
        self._regenerate_lock = threading.Lock()

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handle any file system event.

        Args:
            event: The file system event
        """
        # Ignore directory events
        if event.is_directory:
            return

        # Only react to changes to the config file we're watching
        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode("utf-8")
        event_path = Path(src_path).resolve()

        if event_path != self.config_path:
            return

        # Debounce: only regenerate if enough time has passed
        current_time = time.time()
        with self._regenerate_lock:
            if current_time - self._last_regenerate_time < self.debounce_seconds:
                return
            self._last_regenerate_time = current_time

        print(
            f"\nDetected change in config file {self.config_path.name}, reloading and regenerating site..."
        )
        try:
            # Reload the configuration
            config = load_config(self.config_path)

            # Apply CLI overrides to the loaded config
            for key, value in self.cli_overrides.items():
                if key in config:
                    config[key] = value

            # Extract sidebar config
            sidebar_config = get_sidebar_config(config)

            # Update the generator with new config values
            self._update_generator(config, sidebar_config)

            # Regenerate the site
            self.generator.generate(include_drafts=self.include_drafts)
            print("Configuration reloaded and regeneration complete!")
        except Exception as e:
            print(f"Error reloading config or regenerating: {e}", file=sys.stderr)

    def _update_generator(
        self, config: dict[str, Any], sidebar_config: dict[str, Any]
    ) -> None:
        """Update generator attributes with new configuration values.

        Args:
            config: The loaded configuration dictionary
            sidebar_config: The sidebar configuration
        """
        # Update generator attributes with new config values
        if "site_title" in config:
            self.generator.site_title = config["site_title"]
        if "site_subtitle" in config:
            self.generator.site_subtitle = config["site_subtitle"]
        if "site_url" in config:
            self.generator.site_url = config["site_url"]
        if "posts_per_feed" in config:
            self.generator.posts_per_feed = config["posts_per_feed"]
        if "extra_stylesheets" in config:
            stylesheets = config["extra_stylesheets"]
            if isinstance(stylesheets, str):
                self.generator.renderer.extra_stylesheets = [stylesheets]
            elif isinstance(stylesheets, list):
                self.generator.renderer.extra_stylesheets = stylesheets
        if "default_author" in config:
            self.generator.default_author = config["default_author"]
        if "icon_source" in config:
            self.generator.icon_source = config["icon_source"]
        if "with_search" in config:
            self.generator.with_search = config["with_search"]
        if "with_sitemap" in config:
            self.generator.with_sitemap = config["with_sitemap"]

        # Update sidebar config
        self.generator.sidebar_config = sidebar_config


def serve_site(
    output_dir: Path,
    port: int = 8000,
    content_dir: Path | None = None,
    templates_dir: Path | None = None,
    site_title: str = "My Blog",
    site_subtitle: str = "",
    site_url: str = "",
    include_drafts: bool = False,
    watch: bool = True,
    posts_per_feed: int = 20,
    extra_stylesheets: list[str] | None = None,
    default_author: str | None = None,
    sidebar_config: dict[str, Any] | None = None,
    config_path: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
    clean_first: bool = False,
    icon_source: str | None = None,
    with_search: bool = False,
    with_sitemap: bool = False,
) -> int:
    """Serve the generated site locally using a simple HTTP server.

    Args:
        output_dir: Directory containing the generated site
        port: Port to serve on (default: 8000)
        content_dir: Directory containing markdown posts (optional, for generation)
        templates_dir: Optional directory containing custom templates.
                      If not provided, uses bundled templates.
        site_title: Title of the blog site
        site_subtitle: Subtitle of the blog site
        site_url: Base URL of the site
        include_drafts: Whether to include drafts
        watch: Whether to watch for changes and regenerate (default: True)
        posts_per_feed: Maximum number of posts to include in feeds (default: 20)
        extra_stylesheets: Optional list of URLs for additional stylesheets
        default_author: Default author name for posts without author in frontmatter
        sidebar_config: Optional sidebar configuration (site_logo, links, socials)
        config_path: Path to the configuration file being used (if any)
        cli_overrides: Dictionary of CLI arguments that override config values
        clean_first: Whether to remove the output directory before generating
        icon_source: Optional source icon filename in extras/ directory
        with_search: Whether to generate a search index and search page
        with_sitemap: Whether to generate an XML sitemap

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
                site_subtitle=site_subtitle,
                site_url=site_url,
                posts_per_feed=posts_per_feed,
                extra_stylesheets=extra_stylesheets,
                default_author=default_author,
                sidebar_config=sidebar_config,
                clean_first=clean_first,
                icon_source=icon_source,
                with_search=with_search,
                with_sitemap=with_sitemap,
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

            # Watch configuration file if one is being used
            if config_path is not None and config_path.exists():
                config_handler = ConfigChangeHandler(
                    config_path=config_path,
                    generator=generator,
                    include_drafts=include_drafts,
                    cli_overrides=cli_overrides or {},
                )
                # Watch the directory containing the config file
                observer.schedule(
                    config_handler, str(config_path.parent), recursive=False
                )
                print(f"Watching for changes in config file: {config_path}")

            observer.start()
    elif not output_dir.exists():
        print(
            f"Error: Output directory not found: {output_dir}\n"
            f"Please provide a content directory to generate the site:\n"
            f"  blogmore serve <content_dir> [options]",
            file=sys.stderr,
        )
        return 1

    # Create a simple HTTP server with our custom handler, passing the output
    # directory explicitly so that the handler continues to work even if
    # clean_first removes and recreates the directory during regeneration.
    http_handler = functools.partial(QuietHTTPRequestHandler, directory=str(output_dir))

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
