"""Local server and file watching functionality for blogmore."""

import dataclasses
import functools
import http.server
import io
import queue
import socketserver
import sys
import threading
import time
from pathlib import Path
from typing import Any

from watchdog.events import (
    FileClosedNoWriteEvent,
    FileOpenedEvent,
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from blogmore.config import (
    get_sidebar_config,
    load_config,
    parse_site_config_from_dict,
)
from blogmore.generator import SiteGenerator
from blogmore.parser import CUSTOM_404_HTML
from blogmore.site_config import SiteConfig

# Registry of active SSE connections for browser reloading
_reload_queues: list[queue.Queue[str]] = []
_reload_lock = threading.Lock()


def _trigger_reload() -> None:
    """Signal all connected browsers to reload."""
    with _reload_lock:
        for reload_queue in _reload_queues:
            reload_queue.put("reload")


RELOAD_SCRIPT = """
<script>
(function() {
    const eventSource = new EventSource('/_blogmore/reload');
    eventSource.onmessage = (event) => {
        if (event.data === 'reload') {
            console.log('BlogMore: Change detected, reloading...');
            location.reload();
        }
    };
    eventSource.onerror = () => {
        console.warn('BlogMore: Reload connection lost. Retrying...');
    };
})();
</script>
"""


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

    When a `404.html` file exists in the served directory it is returned as
    the response body for any 404 error, mirroring the behaviour of services
    such as GitHub Pages.

    Also handles the `/_blogmore/reload` SSE endpoint and injects an auto-reload
    script into all served HTML files when they are requested.
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

    def do_GET(self) -> None:
        """Handle a GET request, routing SSE or serving files."""
        if self.path == "/_blogmore/reload":
            self._handle_reload_sse()
            return

        super().do_GET()

    def _handle_reload_sse(self) -> None:
        """Handle the Server-Sent Events (SSE) connection for auto-reload."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        reload_queue: queue.Queue[str] = queue.Queue()
        with _reload_lock:
            _reload_queues.append(reload_queue)

        try:
            while True:
                try:
                    # Wait for a reload signal or timeout for keep-alive ping
                    reload_message = reload_queue.get(timeout=30)
                    self.wfile.write(f"data: {reload_message}\n\n".encode())
                    self.wfile.flush()
                except queue.Empty:
                    # Keep-alive ping to prevent connection timeout
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with _reload_lock:
                _reload_queues.remove(reload_queue)

    def send_head(self) -> io.BytesIO | Any:
        """Send headers and return a file-like object for HTML injection.

        Overrides SimpleHTTPRequestHandler.send_head to inject the auto-reload
        script into HTML responses.
        """
        file_path = Path(self.translate_path(self.path))
        response_body: Any = None

        # If the path is a directory, look for index.html
        if file_path.is_dir():
            index_file = file_path / "index.html"
            if index_file.exists():
                file_path = index_file
            else:
                return super().send_head()

        content_type = self.guess_type(str(file_path))
        if content_type != "text/html":
            return super().send_head()

        # It's an HTML file. Read, inject, and serve.
        try:
            with open(file_path, "rb") as source_file:
                content = source_file.read()

            try:
                html_content = content.decode("utf-8")
                if "</body>" in html_content:
                    # Replace only the last occurrence
                    parts = html_content.rpartition("</body>")
                    injected = parts[0] + RELOAD_SCRIPT + "</body>" + parts[2]
                elif "</html>" in html_content:
                    # Replace only the last occurrence
                    parts = html_content.rpartition("</html>")
                    injected = parts[0] + RELOAD_SCRIPT + "</html>" + parts[2]
                else:
                    # Likely minified or partial HTML, append to the end.
                    injected = html_content + RELOAD_SCRIPT

                response_content = injected.encode()

                response_body = io.BytesIO(response_content)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(response_content)))
                self.send_header("Last-Modified", self.date_time_string(time.time()))
                self.end_headers()
                return response_body
            except UnicodeDecodeError:
                pass
        except OSError:
            pass

        return super().send_head()

    def send_error(
        self,
        code: int,
        message: str | None = None,
        explain: str | None = None,
    ) -> None:
        """Send an error response, serving the custom 404 page when available.

        Args:
            code: HTTP status code
            message: Optional short error message
            explain: Optional longer error explanation
        """
        if code == 404:
            custom_404 = Path(self.directory) / CUSTOM_404_HTML
            if custom_404.exists():
                content = custom_404.read_bytes()
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
        super().send_error(code, message, explain)


class ContentChangeHandler(FileSystemEventHandler):
    """Handle file system events for content changes."""

    def __init__(
        self,
        generator: SiteGenerator,
        debounce_seconds: float = 0.5,
    ) -> None:
        """Initialize the content change handler.

        Args:
            generator: The site generator to use for regeneration
            debounce_seconds: Time to wait after the last change before regenerating
        """
        super().__init__()
        self.generator = generator
        self.debounce_seconds = debounce_seconds
        self._pending_timer: threading.Timer | None = None
        self._timer_lock = threading.Lock()
        self._regeneration_lock = threading.Lock()

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

        # Ignore read-only file access events.  On Linux, watchdog (via
        # inotify) emits FileOpenedEvent and FileClosedNoWriteEvent whenever a
        # file is opened for reading — including when the site generator reads
        # extras files during a copy.  Treating these as content changes would
        # cause an endless regeneration loop, so they are explicitly discarded.
        if isinstance(event, (FileOpenedEvent, FileClosedNoWriteEvent)):
            return

        # Ignore events originating from the output directory to avoid
        # spurious regenerations triggered by the site being written on Linux
        # (inotify generates events for output files that watchdog may pick up
        # even when the output directory is not explicitly watched).
        try:
            path.relative_to(self.generator.site_config.output_dir)
            return
        except ValueError:
            pass

        # Debounce: cancel any pending regeneration and schedule a new one so
        # that a burst of events (e.g. multiple files dropped at once) results
        # in only a single rebuild after the burst settles.
        with self._timer_lock:
            if self._pending_timer is not None:
                self._pending_timer.cancel()
            self._pending_timer = threading.Timer(
                self.debounce_seconds, self._regenerate, args=(path,)
            )
            self._pending_timer.start()

    def _regenerate(self, path: Path) -> None:
        """Regenerate the site after a debounced change event.

        A non-blocking lock prevents multiple simultaneous regenerations when
        two change events fire in quick succession (e.g. on Linux where inotify
        can produce many events for a single logical edit).

        Args:
            path: Path to the file that triggered the regeneration
        """
        if not self._regeneration_lock.acquire(blocking=False):
            print("Regeneration already in progress, skipping...")
            return
        try:
            print(f"\nDetected change in {path}, regenerating site...")
            self.generator.generate()
            print("Regeneration complete!")
            _trigger_reload()
        except Exception as e:
            print(f"Error during regeneration: {e}", file=sys.stderr)
        finally:
            self._regeneration_lock.release()


class ConfigChangeHandler(FileSystemEventHandler):
    """Handle file system events for configuration file changes."""

    def __init__(
        self,
        config_path: Path,
        generator: SiteGenerator,
        cli_overrides: dict[str, Any],
        debounce_seconds: float = 0.5,
    ) -> None:
        """Initialize the config change handler.

        Args:
            config_path: Path to the configuration file being watched
            generator: The site generator to use for regeneration
            cli_overrides: Dictionary of CLI arguments that should override config
            debounce_seconds: Time to wait before regenerating after a change
        """
        super().__init__()
        self.config_path = config_path.resolve()
        self.generator = generator
        self.cli_overrides = cli_overrides
        self.debounce_seconds = debounce_seconds
        self._pending_timer: threading.Timer | None = None
        self._timer_lock = threading.Lock()

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

        # Debounce: cancel any pending regeneration and schedule a new one so
        # that a burst of save events results in only a single config reload.
        with self._timer_lock:
            if self._pending_timer is not None:
                self._pending_timer.cancel()
            self._pending_timer = threading.Timer(
                self.debounce_seconds, self._reload_and_regenerate
            )
            self._pending_timer.start()

    def _reload_and_regenerate(self) -> None:
        """Reload configuration and regenerate the site after a debounced change."""
        print(
            f"\nDetected change in config file {self.config_path.name}, reloading and regenerating site..."
        )
        try:
            # Reload the configuration
            config = load_config(self.config_path)

            # Extract sidebar config from the reloaded YAML.
            sidebar_config = get_sidebar_config(config)

            # Update the generator with new config values
            self._update_generator(config, sidebar_config)

            # Regenerate the site
            self.generator.generate()
            print("Configuration reloaded and regeneration complete!")
            _trigger_reload()
        except Exception as e:
            print(f"Error reloading config or regenerating: {e}", file=sys.stderr)

    def _update_generator(
        self, config: dict[str, Any], sidebar_config: dict[str, Any]
    ) -> None:
        """Update the generator's site configuration with new values.

        Args:
            config: The loaded configuration dictionary
            sidebar_config: The sidebar configuration
        """
        kwargs, warnings = parse_site_config_from_dict(
            config,
            self.generator.site_config.output_dir,
            self.cli_overrides,
        )
        for warning in warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        self.generator.site_config = dataclasses.replace(
            self.generator.site_config,
            sidebar_config=sidebar_config,
            **kwargs,
        )


def serve_site(
    site_config: SiteConfig,
    port: int = 8000,
    watch: bool = True,
    config_path: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> int:
    """Serve the generated site locally using a simple HTTP server.

    Args:
        site_config: Site configuration holding all generation parameters.
            When `site_config.content_dir` is not `None` the site will be
            (re-)generated before serving.  `site_config.include_drafts`
            controls whether draft posts are included.
        port: Port to serve on (default: 8000)
        watch: Whether to watch for changes and regenerate (default: True)
        config_path: Path to the configuration file being used (if any)
        cli_overrides: Dictionary of CLI arguments that override config values

    Returns:
        Exit code
    """
    # Generate the site if content_dir is provided or output doesn't exist
    generator = None
    observer = None

    output_dir = site_config.output_dir

    if site_config.content_dir is not None:
        content_dir = site_config.content_dir
        templates_dir = site_config.templates_dir

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
        site_config = dataclasses.replace(
            site_config,
            content_dir=content_dir.resolve(),
            templates_dir=templates_dir.resolve()
            if templates_dir is not None
            else None,
            output_dir=output_dir.resolve(),
        )
        output_dir = site_config.output_dir

        # Generate the site
        print(f"Generating site from {site_config.content_dir}...")
        try:
            generator = SiteGenerator(site_config=site_config)
            generator.generate()
        except Exception as e:
            print(f"Error generating site: {e}", file=sys.stderr)
            return 1

        # Set up file watching if requested
        if watch:
            observer = Observer()
            handler = ContentChangeHandler(generator)

            # Watch content directory
            observer.schedule(handler, str(site_config.content_dir), recursive=True)

            # Watch templates directory if custom templates are provided
            if site_config.templates_dir is not None:
                observer.schedule(
                    handler, str(site_config.templates_dir), recursive=True
                )
                print(
                    f"Watching for changes in {site_config.content_dir} and {site_config.templates_dir}..."
                )
            else:
                print(f"Watching for changes in {site_config.content_dir}...")

            # Watch configuration file if one is being used
            if config_path is not None and config_path.exists():
                config_handler = ConfigChangeHandler(
                    config_path=config_path,
                    generator=generator,
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
