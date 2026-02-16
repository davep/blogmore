"""Integration tests for the CLI module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from blogmore.__main__ import main
from blogmore.server import ContentChangeHandler, serve_site


class TestContentChangeHandler:
    """Test the ContentChangeHandler class."""

    def test_init(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test initializing ContentChangeHandler."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        handler = ContentChangeHandler(
            generator=generator,
            include_drafts=False,
            debounce_seconds=0.5,
        )

        assert handler.generator == generator
        assert handler.include_drafts is False
        assert handler.debounce_seconds == 0.5

    def test_on_any_event_ignores_directories(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that directory events are ignored."""
        from blogmore.generator import SiteGenerator
        from watchdog.events import DirCreatedEvent

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
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
        from blogmore.generator import SiteGenerator
        from watchdog.events import FileCreatedEvent

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
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
        from blogmore.generator import SiteGenerator
        from watchdog.events import FileCreatedEvent

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        handler = ContentChangeHandler(generator=generator)

        # Create temp file events
        for filename in ["test~", "test.swp", "test.tmp", "test.pyc"]:
            event = FileCreatedEvent(str(posts_dir / filename))
            handler.on_any_event(event)


class TestServeSite:
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

        result = serve_site(output_dir=temp_output_dir, watch=False)

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
            output_dir=temp_output_dir,
            content_dir=posts_dir,
            watch=False,
        )

        assert result == 0
        # Check that site was generated
        assert (temp_output_dir / "index.html").exists()

    def test_serve_content_dir_not_found(self, temp_output_dir: Path) -> None:
        """Test serving with non-existent content directory."""
        result = serve_site(
            output_dir=temp_output_dir,
            content_dir=Path("nonexistent"),
        )

        assert result == 1

    def test_serve_output_dir_not_found_no_content(self) -> None:
        """Test serving with non-existent output and no content directory."""
        result = serve_site(
            output_dir=Path("nonexistent"),
            content_dir=None,
        )

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

        result = serve_site(output_dir=temp_output_dir, watch=False)

        assert result == 1


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

    def test_main_with_site_title(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
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

    def test_main_with_site_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
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

    def test_main_include_drafts(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
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
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
                assert call_kwargs["site_title"] == "Serve Config Blog"
                assert call_kwargs["output_dir"] == temp_output_dir
