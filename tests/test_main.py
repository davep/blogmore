"""Integration tests for the CLI module."""

import dataclasses
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from blogmore.__main__ import main
from blogmore.parser import CUSTOM_404_HTML
from blogmore.server import ConfigChangeHandler, ContentChangeHandler, serve_site
from blogmore.site_config import SiteConfig


class TestContentChangeHandler:
    """Test the ContentChangeHandler class."""

    def test_init(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test initializing ContentChangeHandler."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        handler = ContentChangeHandler(
            generator=generator,
            debounce_seconds=0.5,
        )

        assert handler.generator == generator
        assert handler.generator.site_config.include_drafts is False
        assert handler.debounce_seconds == 0.5

    def test_on_any_event_ignores_directories(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that directory events are ignored."""
        from watchdog.events import DirCreatedEvent

        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        handler = ContentChangeHandler(generator=generator)

        # Create a directory event
        event = DirCreatedEvent(str(posts_dir / "newdir"))

        # Should not raise any errors
        handler.on_any_event(event)

    def test_on_any_event_ignores_hidden_files(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that hidden files are ignored."""
        from watchdog.events import FileCreatedEvent

        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        handler = ContentChangeHandler(generator=generator)

        # Create a hidden file event
        event = FileCreatedEvent(str(posts_dir / ".hidden"))

        # Should not raise any errors
        handler.on_any_event(event)

    def test_on_any_event_ignores_temp_files(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that temporary files are ignored."""
        from watchdog.events import FileCreatedEvent

        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        handler = ContentChangeHandler(generator=generator)

        # Create temp file events
        for filename in ["test~", "test.swp", "test.tmp", "test.pyc"]:
            event = FileCreatedEvent(str(posts_dir / filename))
            handler.on_any_event(event)

    def test_debounce_coalesces_multiple_events(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that multiple rapid events result in only one rebuild."""
        from unittest.mock import patch

        from watchdog.events import FileCreatedEvent

        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        handler = ContentChangeHandler(generator=generator, debounce_seconds=0.05)

        with patch.object(handler, "_regenerate") as mock_regenerate:
            # Fire several events in quick succession
            for i in range(5):
                event = FileCreatedEvent(str(posts_dir / f"post{i}.md"))
                handler.on_any_event(event)

            # Wait long enough for the debounce timer to fire

            time.sleep(0.2)

        # Only one rebuild should have happened despite five events
        assert mock_regenerate.call_count == 1

    def test_debounce_timer_resets_on_new_event(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that a new event resets the debounce timer."""
        from unittest.mock import patch

        from watchdog.events import FileCreatedEvent

        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        handler = ContentChangeHandler(generator=generator, debounce_seconds=0.1)

        with patch.object(handler, "_regenerate") as mock_regenerate:
            # Fire first event
            event1 = FileCreatedEvent(str(posts_dir / "post1.md"))
            handler.on_any_event(event1)

            # Wait less than the debounce window, then fire another event
            time.sleep(0.05)
            event2 = FileCreatedEvent(str(posts_dir / "post2.md"))
            handler.on_any_event(event2)

            # At this point the timer should have been reset; no rebuild yet
            assert mock_regenerate.call_count == 0

            # Wait for the (reset) debounce timer to fire
            time.sleep(0.2)

        # Still only one rebuild
        assert mock_regenerate.call_count == 1

    def test_on_any_event_ignores_output_directory_events(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that events from the output directory are ignored."""
        from watchdog.events import FileCreatedEvent

        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        handler = ContentChangeHandler(generator=generator, debounce_seconds=0.05)

        with patch.object(handler, "_regenerate") as mock_regenerate:
            # Fire an event for a file inside the output directory
            output_file = temp_output_dir / "index.html"
            event = FileCreatedEvent(str(output_file))
            handler.on_any_event(event)

            # Wait for any debounce timer that might have been set
            time.sleep(0.15)

        # No regeneration should have been triggered
        assert mock_regenerate.call_count == 0

    def test_regeneration_lock_prevents_concurrent_regenerations(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the regeneration lock prevents simultaneous regenerations."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        handler = ContentChangeHandler(generator=generator)

        generate_call_count = 0

        def counting_generate() -> None:
            nonlocal generate_call_count
            generate_call_count += 1

        generator.generate = counting_generate  # type: ignore[method-assign]

        # Acquire the lock to simulate an in-progress regeneration
        acquired = handler._regeneration_lock.acquire(blocking=False)
        assert acquired, "Lock should be available before any regeneration"
        try:
            # A _regenerate call while the lock is held should be skipped
            handler._regenerate(posts_dir / "post.md")
        finally:
            handler._regeneration_lock.release()

        assert generate_call_count == 0, (
            "generate() should not be called when regeneration lock is held"
        )


class TestQuietHTTPRequestHandler:
    """Test the QuietHTTPRequestHandler class."""

    def test_serve_custom_404_page_when_present(self, tmp_path: Path) -> None:
        """Test that a custom 404.html is served when a file is not found."""
        import io
        from unittest.mock import patch

        from blogmore.server import QuietHTTPRequestHandler

        custom_404_content = b"<html><body>Custom 404</body></html>"
        (tmp_path / CUSTOM_404_HTML).write_bytes(custom_404_content)

        output_buffer = io.BytesIO()

        handler = QuietHTTPRequestHandler.__new__(QuietHTTPRequestHandler)
        handler.directory = str(tmp_path)
        handler.wfile = output_buffer

        with (
            patch.object(handler, "send_response") as mock_send_response,
            patch.object(handler, "send_header"),
            patch.object(handler, "end_headers"),
        ):
            handler.send_error(404)
            mock_send_response.assert_called_once_with(404)

        written = output_buffer.getvalue()
        assert b"Custom 404" in written

    def test_fallback_to_default_error_when_no_custom_404(self, tmp_path: Path) -> None:
        """Test that the default error response is used when 404.html is absent."""
        import io
        from unittest.mock import patch

        from blogmore.server import QuietHTTPRequestHandler

        output_buffer = io.BytesIO()

        handler = QuietHTTPRequestHandler.__new__(QuietHTTPRequestHandler)
        handler.directory = str(tmp_path)
        handler.wfile = output_buffer

        with patch.object(
            QuietHTTPRequestHandler.__bases__[0], "send_error"
        ) as mock_super_send_error:
            handler.send_error(404)
            mock_super_send_error.assert_called_once_with(404, None, None)

    def test_non_404_errors_use_default_handler(self, tmp_path: Path) -> None:
        """Test that non-404 errors always use the default error handler."""
        import io
        from unittest.mock import patch

        from blogmore.server import QuietHTTPRequestHandler

        (tmp_path / CUSTOM_404_HTML).write_text("<html>Custom 404</html>")

        output_buffer = io.BytesIO()

        handler = QuietHTTPRequestHandler.__new__(QuietHTTPRequestHandler)
        handler.directory = str(tmp_path)
        handler.wfile = output_buffer

        with patch.object(
            QuietHTTPRequestHandler.__bases__[0], "send_error"
        ) as mock_super_send_error:
            handler.send_error(500)
            mock_super_send_error.assert_called_once_with(500, None, None)

    """Test the serve_site function."""

    @patch("blogmore.server.ReusingTCPServer")
    @patch("blogmore.server.Observer")
    def test_serve_existing_output(
        self, mock_observer: MagicMock, mock_server: MagicMock, temp_output_dir: Path
    ) -> None:
        """Test serving an existing output directory."""
        # Create a simple file in output directory
        (temp_output_dir / "index.html").write_text("<html>Test</html>")

        # Mock the server
        mock_server_instance = MagicMock()
        mock_server.return_value.__enter__ = MagicMock(
            return_value=mock_server_instance
        )
        mock_server.return_value.__exit__ = MagicMock(return_value=False)

        # Mock serve_forever to raise KeyboardInterrupt immediately
        mock_server_instance.serve_forever.side_effect = KeyboardInterrupt()

        result = serve_site(
            site_config=SiteConfig(output_dir=temp_output_dir), watch=False
        )

        assert result == 0

    @patch("blogmore.server.ReusingTCPServer")
    @patch("blogmore.server.Observer")
    def test_serve_with_generation(
        self,
        mock_observer: MagicMock,
        mock_server: MagicMock,
        posts_dir: Path,
        temp_output_dir: Path,
    ) -> None:
        """Test serving with site generation."""
        # Mock the server
        mock_server_instance = MagicMock()
        mock_server.return_value.__enter__ = MagicMock(
            return_value=mock_server_instance
        )
        mock_server.return_value.__exit__ = MagicMock(return_value=False)

        # Mock serve_forever to raise KeyboardInterrupt immediately
        mock_server_instance.serve_forever.side_effect = KeyboardInterrupt()

        result = serve_site(
            site_config=SiteConfig(output_dir=temp_output_dir, content_dir=posts_dir),
            watch=False,
        )

        assert result == 0
        # Check that site was generated
        assert (temp_output_dir / "index.html").exists()

    def test_serve_content_dir_not_found(self, temp_output_dir: Path) -> None:
        """Test serving with non-existent content directory."""
        result = serve_site(
            site_config=SiteConfig(
                output_dir=temp_output_dir, content_dir=Path("nonexistent")
            ),
        )

        assert result == 1

    def test_serve_output_dir_not_found_no_content(self) -> None:
        """Test serving with non-existent output and no content directory."""
        result = serve_site(site_config=SiteConfig(output_dir=Path("nonexistent")))

        assert result == 1

    @patch("blogmore.server.ReusingTCPServer")
    def test_serve_port_in_use(
        self, mock_server: MagicMock, temp_output_dir: Path
    ) -> None:
        """Test serving when port is already in use."""
        # Create output directory
        (temp_output_dir / "index.html").write_text("<html>Test</html>")

        # Mock server to raise OSError
        mock_server.side_effect = OSError("Address already in use")

        result = serve_site(
            site_config=SiteConfig(output_dir=temp_output_dir), watch=False
        )

        assert result == 1

    @patch("blogmore.server.ReusingTCPServer")
    @patch("blogmore.server.Observer")
    def test_serve_uses_directory_parameter_not_chdir(
        self, mock_observer: MagicMock, mock_server: MagicMock, temp_output_dir: Path
    ) -> None:
        """Test that serve_site passes directory to handler instead of os.chdir.

        When clean_first is used, the output directory is removed and recreated
        during regeneration. The HTTP handler must use an explicit directory path
        rather than os.getcwd() so it keeps working after directory recreation.
        """
        import functools

        # Create a simple file in the output directory
        (temp_output_dir / "index.html").write_text("<html>Test</html>")

        # Capture the handler passed to ReusingTCPServer
        captured_handler: list[object] = []

        def capture_args(*args: object, **kwargs: object) -> MagicMock:
            if args:
                captured_handler.append(args[1])
            instance = MagicMock()
            instance.__enter__ = MagicMock(return_value=instance)
            instance.__exit__ = MagicMock(return_value=False)
            instance.serve_forever.side_effect = KeyboardInterrupt()
            return instance

        mock_server.side_effect = capture_args

        result = serve_site(
            site_config=SiteConfig(output_dir=temp_output_dir), watch=False
        )

        assert result == 0
        assert len(captured_handler) == 1
        handler = captured_handler[0]
        # The handler should be a functools.partial wrapping QuietHTTPRequestHandler
        # with the output directory explicitly set, not relying on os.getcwd()
        assert isinstance(handler, functools.partial)
        assert handler.keywords.get("directory") == str(temp_output_dir)


class TestMainCLI:
    """Test the main CLI entry point."""

    def test_main_help(self) -> None:
        """Test running with --help flag."""
        with patch.object(sys, "argv", ["blogmore", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Help should exit with 0
            assert exc_info.value.code == 0

    def test_main_version(self) -> None:
        """Test running with --version flag."""
        with patch.object(sys, "argv", ["blogmore", "--version"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_main_generate_command(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test generate command."""
        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "generate",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
            ],
        ):
            result = main()
            assert result == 0
            assert (temp_output_dir / "index.html").exists()

    def test_main_gen_alias(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test 'gen' alias for generate command."""
        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "gen",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
            ],
        ):
            result = main()
            assert result == 0

    def test_main_build_alias(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test 'build' alias for generate command."""
        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "build",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
            ],
        ):
            result = main()
            assert result == 0

    def test_main_test_alias(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test 'test' alias for serve command."""
        with patch("blogmore.__main__.serve_site") as mock_serve:
            mock_serve.return_value = 0

            with patch.object(
                sys,
                "argv",
                [
                    "blogmore",
                    "test",
                    str(posts_dir),
                    "-o",
                    str(temp_output_dir),
                ],
            ):
                result = main()
                assert result == 0
                assert mock_serve.called

    def test_main_content_dir_not_found(self, temp_output_dir: Path) -> None:
        """Test with non-existent content directory."""
        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "generate",
                "nonexistent",
                "-o",
                str(temp_output_dir),
            ],
        ):
            result = main()
            assert result == 1

    def test_main_with_site_title(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test with custom site title."""
        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "generate",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
                "--site-title",
                "My Custom Blog",
            ],
        ):
            result = main()
            assert result == 0

            # Check that custom title is in output
            index_content = (temp_output_dir / "index.html").read_text()
            assert "My Custom Blog" in index_content

    def test_main_with_site_url(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test with custom site URL."""
        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "generate",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
                "--site-url",
                "https://myblog.example.com",
            ],
        ):
            result = main()
            assert result == 0

    def test_main_include_drafts(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test including drafts."""
        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "generate",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
                "--include-drafts",
            ],
        ):
            result = main()
            assert result == 0

            # Check that draft post appears in index
            index_content = (temp_output_dir / "index.html").read_text()
            assert "Draft Post" in index_content

    def test_main_with_extra_stylesheet(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test with extra stylesheet."""
        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "generate",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
                "--extra-stylesheet",
                "https://example.com/custom.css",
            ],
        ):
            result = main()
            assert result == 0

            # Check that stylesheet link is in output
            index_content = (temp_output_dir / "index.html").read_text()
            assert "https://example.com/custom.css" in index_content

    def test_main_with_multiple_extra_stylesheets(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test with multiple extra stylesheets."""
        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "generate",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
                "--extra-stylesheet",
                "https://example.com/style1.css",
                "--extra-stylesheet",
                "https://example.com/style2.css",
            ],
        ):
            result = main()
            assert result == 0

            index_content = (temp_output_dir / "index.html").read_text()
            assert "https://example.com/style1.css" in index_content
            assert "https://example.com/style2.css" in index_content

    @patch("blogmore.__main__.serve_site")
    def test_main_serve_command(
        self, mock_serve: MagicMock, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test serve command."""
        mock_serve.return_value = 0

        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "serve",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
            ],
        ):
            result = main()
            assert result == 0
            assert mock_serve.called

    @patch("blogmore.__main__.serve_site")
    def test_main_serve_with_port(
        self, mock_serve: MagicMock, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test serve command with custom port."""
        mock_serve.return_value = 0

        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "serve",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
                "-p",
                "3000",
            ],
        ):
            result = main()
            assert result == 0

            # Check that port was passed correctly
            call_kwargs = mock_serve.call_args[1]
            assert call_kwargs["port"] == 3000

    @patch("blogmore.__main__.serve_site")
    def test_main_serve_no_watch(
        self, mock_serve: MagicMock, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test serve command with --no-watch."""
        mock_serve.return_value = 0

        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "serve",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
                "--no-watch",
            ],
        ):
            result = main()
            assert result == 0

            # Check that watch was disabled
            call_kwargs = mock_serve.call_args[1]
            assert call_kwargs["watch"] is False


class TestConfigFileIntegration:
    """Test CLI integration with configuration files."""

    def test_main_with_default_config_file(
        self,
        posts_dir: Path,
        temp_output_dir: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that default blogmore.yaml is automatically loaded."""
        # Change to a temporary directory
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.chdir(work_dir)

        # Create a config file
        config_file = work_dir / "blogmore.yaml"
        config = {
            "site_title": "Config Blog",
            "output": str(temp_output_dir),
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with patch.object(
            sys,
            "argv",
            ["blogmore", "build", str(posts_dir)],
        ):
            result = main()
            assert result == 0
            assert (temp_output_dir / "index.html").exists()

            # Verify that config was used by checking the output
            with open(temp_output_dir / "index.html") as f:
                content = f.read()
                assert "Config Blog" in content

    def test_main_with_explicit_config_file(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test using --config to specify a config file."""
        config_file = tmp_path / "custom.yaml"
        config = {
            "site_title": "Custom Config Blog",
            "output": str(temp_output_dir),
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "build",
                str(posts_dir),
                "--config",
                str(config_file),
            ],
        ):
            result = main()
            assert result == 0
            assert (temp_output_dir / "index.html").exists()

            # Verify that config was used
            with open(temp_output_dir / "index.html") as f:
                content = f.read()
                assert "Custom Config Blog" in content

    def test_main_cli_overrides_config(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that CLI arguments override config file values."""
        config_file = tmp_path / "config.yaml"
        config = {
            "site_title": "Config Title",
            "output": str(tmp_path / "config-output"),
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "build",
                str(posts_dir),
                "--config",
                str(config_file),
                "--site-title",
                "CLI Title",
                "-o",
                str(temp_output_dir),
            ],
        ):
            result = main()
            assert result == 0

            # Output should be in temp_output_dir, not config-output
            assert (temp_output_dir / "index.html").exists()
            assert not (tmp_path / "config-output" / "index.html").exists()

            # Title should be from CLI
            with open(temp_output_dir / "index.html") as f:
                content = f.read()
                assert "CLI Title" in content
                assert "Config Title" not in content

    def test_main_with_nonexistent_config_file(self, posts_dir: Path) -> None:
        """Test that specifying a nonexistent config file produces an error."""
        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "build",
                str(posts_dir),
                "--config",
                "nonexistent.yaml",
            ],
        ):
            result = main()
            assert result == 1  # Should return error code

    def test_main_with_invalid_yaml_config(
        self, posts_dir: Path, tmp_path: Path
    ) -> None:
        """Test that an invalid YAML config file produces an error."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("- not\n- a\n- dict\n")

        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "build",
                str(posts_dir),
                "--config",
                str(config_file),
            ],
        ):
            result = main()
            assert result == 1  # Should return error code

    def test_main_config_with_all_options(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test config file with all supported options."""
        config_file = tmp_path / "full.yaml"
        config = {
            "output": str(temp_output_dir),
            "site_title": "Full Config Blog",
            "site_url": "https://example.com",
            "include_drafts": True,
            "posts_per_feed": 30,
            "extra_stylesheets": ["https://example.com/style.css"],
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "build",
                str(posts_dir),
                "--config",
                str(config_file),
            ],
        ):
            result = main()
            assert result == 0
            assert (temp_output_dir / "index.html").exists()

            # Verify config values were used
            with open(temp_output_dir / "index.html") as f:
                content = f.read()
                assert "Full Config Blog" in content
                assert "https://example.com/style.css" in content

    def test_main_serve_with_config(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test serve command with config file."""
        config_file = tmp_path / "serve-config.yaml"
        config = {
            "output": str(temp_output_dir),
            "port": 9000,
            "site_title": "Serve Config Blog",
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with patch("blogmore.__main__.serve_site") as mock_serve:
            mock_serve.return_value = 0

            with patch.object(
                sys,
                "argv",
                [
                    "blogmore",
                    "serve",
                    str(posts_dir),
                    "--config",
                    str(config_file),
                    "--no-watch",
                ],
            ):
                result = main()
                assert result == 0

                # Verify serve was called with config values
                call_kwargs = mock_serve.call_args[1]
                assert call_kwargs["port"] == 9000
                assert call_kwargs["site_config"].site_title == "Serve Config Blog"
                assert call_kwargs["site_config"].output_dir == temp_output_dir

    def test_main_with_tilde_in_config_paths(
        self, posts_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that tilde paths in config file are properly expanded."""
        # Create a work directory with config
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.chdir(work_dir)

        # Create temp directory in home for testing
        home_temp = Path.home() / ".blogmore-test-temp"
        home_temp.mkdir(exist_ok=True)
        output_dir = home_temp / "output"

        try:
            # Create config with tilde paths
            config_file = work_dir / "blogmore.yaml"
            config = {
                "output": "~/.blogmore-test-temp/output",
            }
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            with patch.object(
                sys,
                "argv",
                ["blogmore", "build", str(posts_dir)],
            ):
                result = main()
                assert result == 0

                # Verify output was created in expanded path
                assert output_dir.exists()
                assert (output_dir / "index.html").exists()
        finally:
            # Cleanup
            import shutil

            if home_temp.exists():
                shutil.rmtree(home_temp)

    def test_main_with_tilde_in_cli_path(self, posts_dir: Path, tmp_path: Path) -> None:
        """Test that tilde paths from CLI are properly expanded."""
        home_temp = Path.home() / ".blogmore-test-temp2"
        home_temp.mkdir(exist_ok=True)
        output_dir = home_temp / "output"

        try:
            with patch.object(
                sys,
                "argv",
                [
                    "blogmore",
                    "build",
                    str(posts_dir),
                    "-o",
                    "~/.blogmore-test-temp2/output",
                ],
            ):
                result = main()
                assert result == 0

                # Verify output was created in expanded path
                assert output_dir.exists()
                assert (output_dir / "index.html").exists()
        finally:
            # Cleanup
            import shutil

            if home_temp.exists():
                shutil.rmtree(home_temp)

    def test_main_build_with_content_dir_from_config_only(
        self,
        posts_dir: Path,
        temp_output_dir: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test build command with content_dir specified only in config file."""
        # Create a work directory with config
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.chdir(work_dir)

        # Create config file with content_dir
        config_file = work_dir / "blogmore.yaml"
        config = {
            "content_dir": str(posts_dir),
            "output": str(temp_output_dir),
            "site_title": "davep.org",
            "site_url": "https://blog.davep.org",
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # Run build command WITHOUT content_dir on command line
        with patch.object(
            sys,
            "argv",
            ["blogmore", "build"],
        ):
            result = main()
            assert result == 0
            assert (temp_output_dir / "index.html").exists()

            # Verify that config was used by checking the output
            with open(temp_output_dir / "index.html") as f:
                content = f.read()
                assert "davep.org" in content

    def test_main_build_without_content_dir_fails(
        self, temp_output_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that build command fails when content_dir is not provided."""
        # Create a work directory with config
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.chdir(work_dir)

        # Create config file WITHOUT content_dir
        config_file = work_dir / "blogmore.yaml"
        config = {
            "output": str(temp_output_dir),
            "site_title": "Test Blog",
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # Run build command WITHOUT content_dir
        with patch.object(
            sys,
            "argv",
            ["blogmore", "build"],
        ):
            result = main()
            assert result == 1  # Should fail


class TestHeadConfigValidation:
    """Tests for `head` configuration file validation."""

    def test_head_config_renders_tags(
        self,
        posts_dir: Path,
        temp_output_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Valid head config entries are rendered into every generated page."""
        config_file = tmp_path / "blogmore.yaml"
        config_file.write_text(
            f"output: {temp_output_dir}\n"
            "head:\n"
            "  - link:\n"
            "      rel: author\n"
            "      href: /humans.txt\n"
            "  - meta:\n"
            "      name: theme-color\n"
            '      content: "#ffffff"\n'
        )

        with patch.object(
            sys,
            "argv",
            ["blogmore", "build", str(posts_dir), "--config", str(config_file)],
        ):
            result = main()

        assert result == 0
        content = (temp_output_dir / "index.html").read_text()
        assert '<link rel="author" href="/humans.txt">' in content
        assert '<meta name="theme-color" content="#ffffff">' in content

    def test_head_config_not_a_list_returns_error(
        self,
        posts_dir: Path,
        tmp_path: Path,
    ) -> None:
        """A non-list `head` value causes main() to return 1."""
        config_file = tmp_path / "blogmore.yaml"
        config = {
            "output": str(tmp_path / "output"),
            "head": "not-a-list",
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with patch.object(
            sys,
            "argv",
            ["blogmore", "build", str(posts_dir), "--config", str(config_file)],
        ):
            result = main()

        assert result == 1

    def test_head_config_item_not_single_key_dict_returns_error(
        self,
        posts_dir: Path,
        tmp_path: Path,
    ) -> None:
        """A head entry that is not a single-key mapping causes main() to return 1."""
        config_file = tmp_path / "blogmore.yaml"
        # Two keys in one entry is invalid
        config_file.write_text(
            "output: " + str(tmp_path / "output") + "\n"
            "head:\n"
            "  - link: {rel: author}\n"
            "    meta: {name: foo}\n"
        )

        with patch.object(
            sys,
            "argv",
            ["blogmore", "build", str(posts_dir), "--config", str(config_file)],
        ):
            result = main()

        assert result == 1

    def test_head_config_attributes_not_a_dict_returns_error(
        self,
        posts_dir: Path,
        tmp_path: Path,
    ) -> None:
        """A head entry whose attributes value is not a dict causes main() to return 1."""
        config_file = tmp_path / "blogmore.yaml"
        config_file.write_text(
            "output: " + str(tmp_path / "output") + "\nhead:\n  - link: not-a-dict\n"
        )

        with patch.object(
            sys,
            "argv",
            ["blogmore", "build", str(posts_dir), "--config", str(config_file)],
        ):
            result = main()

        assert result == 1

    def test_head_config_empty_list_is_valid(
        self,
        posts_dir: Path,
        temp_output_dir: Path,
        tmp_path: Path,
    ) -> None:
        """An empty head list is valid and produces no extra head tags."""
        config_file = tmp_path / "blogmore.yaml"
        config = {
            "output": str(temp_output_dir),
            "head": [],
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with patch.object(
            sys,
            "argv",
            ["blogmore", "build", str(posts_dir), "--config", str(config_file)],
        ):
            result = main()

        assert result == 0


class TestPagePathConfigValidation:
    """Tests for `page_path` configuration file loading and validation."""

    def test_page_path_from_config_is_applied(
        self,
        tmp_path: Path,
        temp_output_dir: Path,
    ) -> None:
        """A valid page_path in the config file is applied to the generated site."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_subdir = content_dir / "pages"
        pages_subdir.mkdir()
        (pages_subdir / "about.md").write_text(
            "---\ntitle: About Me\n---\n\nAbout content."
        )
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: A Post\ndate: 2024-01-01\n---\n\nPost content."
        )
        config_file = tmp_path / "blogmore.yaml"
        config_file.write_text(
            f"output: {temp_output_dir}\n"
            'page_path: "{slug}/index.html"\n'
        )

        with patch.object(
            sys,
            "argv",
            ["blogmore", "build", str(content_dir), "--config", str(config_file)],
        ):
            result = main()

        assert result == 0
        # The page should be generated at about/index.html, not about.html
        assert (temp_output_dir / "about" / "index.html").exists()
        assert not (temp_output_dir / "about.html").exists()

    def test_page_path_not_a_string_returns_error(
        self,
        posts_dir: Path,
        tmp_path: Path,
    ) -> None:
        """A non-string page_path causes main() to return 1."""
        config_file = tmp_path / "blogmore.yaml"
        config = {
            "output": str(tmp_path / "output"),
            "page_path": 42,
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with patch.object(
            sys,
            "argv",
            ["blogmore", "build", str(posts_dir), "--config", str(config_file)],
        ):
            result = main()

        assert result == 1

    def test_invalid_page_path_returns_error(
        self,
        posts_dir: Path,
        tmp_path: Path,
    ) -> None:
        """An invalid page_path (missing {slug}) causes main() to return 1."""
        config_file = tmp_path / "blogmore.yaml"
        config = {
            "output": str(tmp_path / "output"),
            "page_path": "pages/index.html",
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with patch.object(
            sys,
            "argv",
            ["blogmore", "build", str(posts_dir), "--config", str(config_file)],
        ):
            result = main()

        assert result == 1

    def test_404_page_always_generated_at_root(
        self,
        tmp_path: Path,
        temp_output_dir: Path,
    ) -> None:
        """The 404.md page is always generated as /404.html regardless of page_path."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_subdir = content_dir / "pages"
        pages_subdir.mkdir()
        (pages_subdir / "404.md").write_text(
            "---\ntitle: Not Found\n---\n\nPage not found."
        )
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: A Post\ndate: 2024-01-01\n---\n\nPost content."
        )
        config_file = tmp_path / "blogmore.yaml"
        config_file.write_text(
            f"output: {temp_output_dir}\n"
            'page_path: "pages/{slug}/index.html"\n'
        )

        with patch.object(
            sys,
            "argv",
            ["blogmore", "build", str(content_dir), "--config", str(config_file)],
        ):
            result = main()

        assert result == 0
        # 404.html must always be at the root, not affected by page_path
        assert (temp_output_dir / "404.html").exists()
        assert not (temp_output_dir / "pages" / "404" / "index.html").exists()


class TestConfigChangeHandler:
    """Test the ConfigChangeHandler class."""

    def test_init(self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path) -> None:
        """Test initializing ConfigChangeHandler."""
        from blogmore.generator import SiteGenerator

        config_file = tmp_path / "blogmore.yaml"
        config_file.write_text("site_title: Test Blog\n")

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        cli_overrides = {"site_title": "CLI Title"}
        handler = ConfigChangeHandler(
            config_path=config_file,
            generator=generator,
            cli_overrides=cli_overrides,
            debounce_seconds=0.5,
        )

        assert handler.config_path == config_file.resolve()
        assert handler.generator == generator
        assert handler.generator.site_config.include_drafts is False
        assert handler.cli_overrides == cli_overrides
        assert handler.debounce_seconds == 0.5

    def test_on_any_event_ignores_directories(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that directory events are ignored."""
        from watchdog.events import DirCreatedEvent

        from blogmore.generator import SiteGenerator

        config_file = tmp_path / "blogmore.yaml"
        config_file.write_text("site_title: Test Blog\n")

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        handler = ConfigChangeHandler(
            config_path=config_file,
            generator=generator,
            cli_overrides={},
        )

        # Create a directory event
        event = DirCreatedEvent(str(tmp_path / "newdir"))

        # Should not raise any errors and should not trigger regeneration
        handler.on_any_event(event)

    def test_on_any_event_ignores_unrelated_files(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that events for unrelated files are ignored."""
        from watchdog.events import FileModifiedEvent

        from blogmore.generator import SiteGenerator

        config_file = tmp_path / "blogmore.yaml"
        config_file.write_text("site_title: Test Blog\n")

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        handler = ConfigChangeHandler(
            config_path=config_file,
            generator=generator,
            cli_overrides={},
        )

        # Create an event for a different file
        other_file = tmp_path / "other.yaml"
        event = FileModifiedEvent(str(other_file))

        # Should not raise any errors
        handler.on_any_event(event)

    def test_on_any_event_reloads_config(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that config changes trigger reload and regeneration."""

        from watchdog.events import FileModifiedEvent

        from blogmore.generator import SiteGenerator

        config_file = tmp_path / "blogmore.yaml"
        config_data = {
            "site_title": "Original Title",
            "site_subtitle": "Original Subtitle",
            "posts_per_feed": 30,
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        # Mock the generate method to verify it's called
        with patch.object(generator, "generate") as mock_generate:
            handler = ConfigChangeHandler(
                config_path=config_file,
                generator=generator,
                cli_overrides={},
                debounce_seconds=0.05,
            )

            # Update the config file
            new_config_data = {
                "site_title": "Updated Title",
                "site_subtitle": "Updated Subtitle",
                "posts_per_feed": 50,
            }
            with open(config_file, "w") as f:
                yaml.dump(new_config_data, f)

            # Trigger the event and wait for the debounce timer to fire
            event = FileModifiedEvent(str(config_file))
            handler.on_any_event(event)
            time.sleep(0.2)

            # Verify generate was called
            mock_generate.assert_called_once_with()

            # Verify generator attributes were updated
            assert generator.site_config.site_title == "Updated Title"
            assert generator.site_config.site_subtitle == "Updated Subtitle"
            assert generator.site_config.posts_per_feed == 50

    def test_on_any_event_cli_overrides_preserved(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that CLI overrides are preserved when config is reloaded."""

        from watchdog.events import FileModifiedEvent

        from blogmore.generator import SiteGenerator

        config_file = tmp_path / "blogmore.yaml"
        config_data = {
            "site_title": "Config Title",
            "site_subtitle": "Config Subtitle",
            "posts_per_feed": 30,
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_title="CLI Title",
            )
        )

        cli_overrides = {"site_title": "CLI Title"}

        with patch.object(generator, "generate") as mock_generate:
            handler = ConfigChangeHandler(
                config_path=config_file,
                generator=generator,
                cli_overrides=cli_overrides,
                debounce_seconds=0.05,
            )

            # Update the config file
            new_config_data = {
                "site_title": "Updated Config Title",
                "site_subtitle": "Updated Subtitle",
                "posts_per_feed": 50,
            }
            with open(config_file, "w") as f:
                yaml.dump(new_config_data, f)

            # Trigger the event and wait for the debounce timer to fire
            event = FileModifiedEvent(str(config_file))
            handler.on_any_event(event)
            time.sleep(0.2)

            # Verify generate was called
            mock_generate.assert_called_once_with()

            # Verify CLI override was preserved but config values were updated
            assert (
                generator.site_config.site_title == "CLI Title"
            )  # CLI override preserved
            assert (
                generator.site_config.site_subtitle == "Updated Subtitle"
            )  # Config updated
            assert generator.site_config.posts_per_feed == 50  # Config updated

    def test_on_any_event_updates_extra_stylesheets(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that extra_stylesheets are updated correctly."""

        from watchdog.events import FileModifiedEvent

        from blogmore.generator import SiteGenerator

        config_file = tmp_path / "blogmore.yaml"
        config_data = {
            "extra_stylesheets": ["style1.css"],
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        with patch.object(generator, "generate"):
            handler = ConfigChangeHandler(
                config_path=config_file,
                generator=generator,
                cli_overrides={},
                debounce_seconds=0.05,
            )

            # Update config with new stylesheets
            new_config_data = {
                "extra_stylesheets": ["style1.css", "style2.css", "style3.css"],
            }
            with open(config_file, "w") as f:
                yaml.dump(new_config_data, f)

            # Trigger the event and wait for the debounce timer to fire
            event = FileModifiedEvent(str(config_file))
            handler.on_any_event(event)
            time.sleep(0.2)

            # Verify stylesheets were updated in site_config (generate() will
            # propagate them to the renderer with cache-busting applied)
            assert generator.site_config.extra_stylesheets == [
                "style1.css",
                "style2.css",
                "style3.css",
            ]

    def test_on_any_event_updates_sidebar_config(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that sidebar configuration is updated correctly."""

        from watchdog.events import FileModifiedEvent

        from blogmore.generator import SiteGenerator

        config_file = tmp_path / "blogmore.yaml"
        config_data = {
            "site_logo": "/images/logo.png",
            "links": [{"title": "Home", "url": "/"}],
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        with patch.object(generator, "generate"):
            handler = ConfigChangeHandler(
                config_path=config_file,
                generator=generator,
                cli_overrides={},
                debounce_seconds=0.05,
            )

            # Update config with new sidebar config
            new_config_data = {
                "site_logo": "/images/newlogo.png",
                "links": [
                    {"title": "Home", "url": "/"},
                    {"title": "About", "url": "/about.html"},
                ],
                "socials": [{"site": "github", "url": "https://github.com/user"}],
            }
            with open(config_file, "w") as f:
                yaml.dump(new_config_data, f)

            # Trigger the event and wait for the debounce timer to fire
            event = FileModifiedEvent(str(config_file))
            handler.on_any_event(event)
            time.sleep(0.2)

            # Verify sidebar config was updated
            assert (
                generator.site_config.sidebar_config["site_logo"]
                == "/images/newlogo.png"
            )
            assert len(generator.site_config.sidebar_config["links"]) == 2
            assert generator.site_config.sidebar_config["socials"] == [
                {"site": "github", "url": "https://github.com/user"}
            ]

    def test_on_any_event_debouncing(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that rapid config changes are debounced into a single rebuild."""

        from watchdog.events import FileModifiedEvent

        from blogmore.generator import SiteGenerator

        config_file = tmp_path / "blogmore.yaml"
        config_file.write_text("site_title: Test Blog\n")

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        with patch.object(generator, "generate") as mock_generate:
            handler = ConfigChangeHandler(
                config_path=config_file,
                generator=generator,
                cli_overrides={},
                debounce_seconds=0.1,
            )

            # Trigger multiple events rapidly - no rebuild should have fired yet
            event = FileModifiedEvent(str(config_file))
            handler.on_any_event(event)
            handler.on_any_event(event)
            handler.on_any_event(event)
            assert mock_generate.call_count == 0

            # Wait for the debounce timer to fire
            time.sleep(0.3)

            # Only one generation should have occurred despite multiple events
            assert mock_generate.call_count == 1

    @pytest.mark.parametrize(
        "config_key",
        [
            "clean_urls",
            "minify_css",
            "minify_js",
            "clean_first",
            "include_drafts",
        ],
    )
    def test_on_any_event_updates_boolean_field(
        self,
        posts_dir: Path,
        temp_output_dir: Path,
        tmp_path: Path,
        config_key: str,
    ) -> None:
        """Test that boolean config fields are updated when the config changes."""

        from watchdog.events import FileModifiedEvent

        from blogmore.generator import SiteGenerator

        config_file = tmp_path / "blogmore.yaml"
        config_data: dict[str, object] = {config_key: False}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                **{config_key: False},  # type: ignore[arg-type]
            )
        )

        with patch.object(generator, "generate"):
            handler = ConfigChangeHandler(
                config_path=config_file,
                generator=generator,
                cli_overrides={},
                debounce_seconds=0.05,
            )

            new_config_data: dict[str, object] = {config_key: True}
            with open(config_file, "w") as f:
                yaml.dump(new_config_data, f)

            event = FileModifiedEvent(str(config_file))
            handler.on_any_event(event)
            time.sleep(0.2)

            assert getattr(generator.site_config, config_key) is True

    def test_cli_minify_css_overrides_config_on_reload(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that a CLI minify_css setting overrides config on reload."""

        from watchdog.events import FileModifiedEvent

        from blogmore.generator import SiteGenerator

        config_file = tmp_path / "blogmore.yaml"
        config_data: dict[str, object] = {"minify_css": False}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                minify_css=True,
            )
        )

        # CLI set --minify-css, so it's in cli_overrides
        cli_overrides: dict[str, object] = {"minify_css": True}

        with patch.object(generator, "generate"):
            handler = ConfigChangeHandler(
                config_path=config_file,
                generator=generator,
                cli_overrides=cli_overrides,
                debounce_seconds=0.05,
            )

            # Config changes to explicitly disable minify_css
            new_config_data: dict[str, object] = {"minify_css": False}
            with open(config_file, "w") as f:
                yaml.dump(new_config_data, f)

            event = FileModifiedEvent(str(config_file))
            handler.on_any_event(event)
            time.sleep(0.2)

            # CLI override should win over config
            assert generator.site_config.minify_css is True

    def test_extra_stylesheets_updated_in_site_config(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that extra_stylesheets update is stored in site_config for generate()."""

        from watchdog.events import FileModifiedEvent

        from blogmore.generator import SiteGenerator

        config_file = tmp_path / "blogmore.yaml"
        config_data: dict[str, object] = {"extra_stylesheets": ["old.css"]}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                extra_stylesheets=["old.css"],
            )
        )

        with patch.object(generator, "generate"):
            handler = ConfigChangeHandler(
                config_path=config_file,
                generator=generator,
                cli_overrides={},
                debounce_seconds=0.05,
            )

            new_config_data: dict[str, object] = {
                "extra_stylesheets": ["new1.css", "new2.css"]
            }
            with open(config_file, "w") as f:
                yaml.dump(new_config_data, f)

            event = FileModifiedEvent(str(config_file))
            handler.on_any_event(event)
            time.sleep(0.2)

            # site_config must be updated so generate() picks up the new list
            assert generator.site_config.extra_stylesheets == ["new1.css", "new2.css"]

    def test_extra_stylesheets_cleared_when_removed_from_config(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that removing extra_stylesheets from config clears it in site_config."""

        from watchdog.events import FileModifiedEvent

        from blogmore.generator import SiteGenerator

        config_file = tmp_path / "blogmore.yaml"
        config_data: dict[str, object] = {"extra_stylesheets": ["/custom.css"]}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                extra_stylesheets=["/custom.css"],
            )
        )

        with patch.object(generator, "generate"):
            handler = ConfigChangeHandler(
                config_path=config_file,
                generator=generator,
                cli_overrides={},
                debounce_seconds=0.05,
            )

            # Remove extra_stylesheets from the config entirely
            new_config_data: dict[str, object] = {"site_title": "My Blog"}
            with open(config_file, "w") as f:
                yaml.dump(new_config_data, f)

            event = FileModifiedEvent(str(config_file))
            handler.on_any_event(event)
            time.sleep(0.2)

            # extra_stylesheets must be cleared so generate() no longer
            # includes the <link> tag for /custom.css
            assert generator.site_config.extra_stylesheets is None

    def test_extra_stylesheets_cleared_in_renderer_on_generate(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that generate() clears renderer.extra_stylesheets when config has none."""
        from blogmore.generator import SiteGenerator

        # Generator started with stylesheets
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                extra_stylesheets=["/custom.css"],
            )
        )
        # Simulate what happens after config reload removes extra_stylesheets:
        # site_config.extra_stylesheets is now None
        generator.site_config = dataclasses.replace(
            generator.site_config, extra_stylesheets=None
        )

        generator.generate()

        # Renderer must have an empty list, not the old stylesheet
        assert generator.renderer.extra_stylesheets == []
