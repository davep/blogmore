"""Tests for the config module."""

from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from blogmore.config import (
    DEFAULT_CONFIG_FILES,
    get_sidebar_config,
    load_config,
    merge_config_with_args,
)


class TestLoadConfig:
    """Test the load_config function."""

    def test_load_specific_config_file(self, tmp_path: Path) -> None:
        """Test loading a specific configuration file."""
        config_file = tmp_path / "custom.yaml"
        config_data = {
            "site_title": "My Custom Blog",
            "output": "custom-output",
            "posts_per_feed": 30,
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = load_config(config_file)

        assert result == config_data

    def test_load_nonexistent_config_file(self, tmp_path: Path) -> None:
        """Test that loading a nonexistent file raises FileNotFoundError."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config(config_file)

    def test_load_default_blogmore_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading default blogmore.yaml file."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "blogmore.yaml"
        config_data = {"site_title": "Default Config Blog"}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = load_config()

        assert result == config_data

    def test_load_default_blogmore_yml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading default blogmore.yml file when .yaml doesn't exist."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "blogmore.yml"
        config_data = {"site_title": "YML Config Blog"}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = load_config()

        assert result == config_data

    def test_yaml_takes_precedence_over_yml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that blogmore.yaml takes precedence over blogmore.yml."""
        monkeypatch.chdir(tmp_path)

        yaml_file = tmp_path / "blogmore.yaml"
        yaml_data = {"site_title": "YAML Config"}
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_data, f)

        yml_file = tmp_path / "blogmore.yml"
        yml_data = {"site_title": "YML Config"}
        with open(yml_file, "w") as f:
            yaml.dump(yml_data, f)

        result = load_config()

        assert result == yaml_data

    def test_no_default_config_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that an empty dict is returned when no config file is found."""
        monkeypatch.chdir(tmp_path)

        result = load_config()

        assert result == {}

    def test_empty_config_file(self, tmp_path: Path) -> None:
        """Test loading an empty configuration file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        result = load_config(config_file)

        assert result == {}

    def test_config_file_with_only_comments(self, tmp_path: Path) -> None:
        """Test loading a config file with only comments."""
        config_file = tmp_path / "comments.yaml"
        config_file.write_text("# This is just a comment\n# Another comment\n")

        result = load_config(config_file)

        assert result == {}

    def test_invalid_yaml_format(self, tmp_path: Path) -> None:
        """Test that loading a non-dict YAML raises ValueError."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("- item1\n- item2\n")

        with pytest.raises(ValueError, match="must contain a YAML dictionary"):
            load_config(config_file)


class TestMergeConfigWithArgs:
    """Test the merge_config_with_args function."""

    def test_cli_overrides_config(self) -> None:
        """Test that CLI arguments override config file values."""
        config = {
            "site_title": "Config Title",
            "output": "config-output",
        }
        args = Mock()
        args.site_title = "CLI Title"
        args.output = Path("cli-output")

        merge_config_with_args(config, args)

        assert args.site_title == "CLI Title"
        assert args.output == Path("cli-output")

    def test_config_used_when_cli_is_default(self) -> None:
        """Test that config values are used when CLI has default values."""
        config = {
            "site_title": "Config Title",
            "output": "config-output",
            "posts_per_feed": 50,
            "port": 3000,
        }
        args = Mock()
        args.site_title = "My Blog"  # default
        args.output = Path("output")  # default
        args.posts_per_feed = 20  # default
        args.port = 8000  # default

        merge_config_with_args(config, args)

        assert args.site_title == "Config Title"
        assert args.output == Path("config-output")
        assert args.posts_per_feed == 50
        assert args.port == 3000

    def test_templates_from_config(self) -> None:
        """Test loading templates directory from config."""
        config = {"templates": "my-templates"}
        args = Mock()
        args.templates = None  # default

        merge_config_with_args(config, args)

        assert args.templates == Path("my-templates")

    def test_cli_templates_overrides_config(self) -> None:
        """Test that CLI templates override config."""
        config = {"templates": "config-templates"}
        args = Mock()
        args.templates = Path("cli-templates")

        merge_config_with_args(config, args)

        assert args.templates == Path("cli-templates")

    def test_include_drafts_from_config(self) -> None:
        """Test loading include_drafts from config."""
        config = {"include_drafts": True}
        args = Mock()
        args.include_drafts = False

        merge_config_with_args(config, args)

        assert args.include_drafts is True

    def test_cli_include_drafts_overrides_config(self) -> None:
        """Test that CLI include_drafts overrides config."""
        config = {"include_drafts": False}
        args = Mock()
        args.include_drafts = True

        merge_config_with_args(config, args)

        assert args.include_drafts is True

    def test_extra_stylesheets_from_config_list(self) -> None:
        """Test loading extra stylesheets from config as a list."""
        config = {"extra_stylesheets": ["style1.css", "style2.css"]}
        args = Mock()
        args.extra_stylesheets = None

        merge_config_with_args(config, args)

        assert args.extra_stylesheets == ["style1.css", "style2.css"]

    def test_extra_stylesheets_from_config_string(self) -> None:
        """Test loading a single stylesheet from config as a string."""
        config = {"extra_stylesheets": "style.css"}
        args = Mock()
        args.extra_stylesheets = None

        merge_config_with_args(config, args)

        assert args.extra_stylesheets == ["style.css"]

    def test_cli_extra_stylesheets_overrides_config(self) -> None:
        """Test that CLI stylesheets override config."""
        config = {"extra_stylesheets": ["config.css"]}
        args = Mock()
        args.extra_stylesheets = ["cli.css"]

        merge_config_with_args(config, args)

        assert args.extra_stylesheets == ["cli.css"]

    def test_site_url_from_config(self) -> None:
        """Test loading site_url from config."""
        config = {"site_url": "https://example.com"}
        args = Mock()
        args.site_url = ""  # default

        merge_config_with_args(config, args)

        assert args.site_url == "https://example.com"

    def test_content_dir_from_config(self) -> None:
        """Test loading content_dir from config."""
        config = {"content_dir": "my-posts"}
        args = Mock()
        args.content_dir = None

        merge_config_with_args(config, args)

        assert args.content_dir == Path("my-posts")

    def test_cli_content_dir_overrides_config(self) -> None:
        """Test that CLI content_dir overrides config."""
        config = {"content_dir": "config-posts"}
        args = Mock()
        args.content_dir = Path("cli-posts")

        merge_config_with_args(config, args)

        assert args.content_dir == Path("cli-posts")

    def test_no_watch_from_config(self) -> None:
        """Test loading no_watch from config."""
        config = {"no_watch": True}
        args = Mock()
        args.no_watch = False

        merge_config_with_args(config, args)

        assert args.no_watch is True

    def test_missing_attributes_in_args(self) -> None:
        """Test that merge handles missing attributes gracefully."""
        config = {
            "port": 3000,
            "no_watch": True,
        }
        args = Mock(spec=["site_title", "output"])
        args.site_title = "My Blog"
        args.output = Path("output")

        # Should not raise an error
        merge_config_with_args(config, args)

        assert args.site_title == "My Blog"
        assert args.output == Path("output")

    def test_empty_config(self) -> None:
        """Test merging with an empty config."""
        config = {}
        args = Mock()
        args.site_title = "My Blog"
        args.output = Path("output")

        merge_config_with_args(config, args)

        assert args.site_title == "My Blog"
        assert args.output == Path("output")

    def test_complete_config(self) -> None:
        """Test merging a complete configuration."""
        config = {
            "content_dir": "posts",
            "templates": "templates",
            "output": "site",
            "site_title": "Awesome Blog",
            "site_url": "https://blog.example.com",
            "include_drafts": True,
            "posts_per_feed": 25,
            "extra_stylesheets": ["custom.css"],
            "port": 9000,
            "no_watch": False,
        }
        args = Mock()
        args.content_dir = None
        args.templates = None
        args.output = Path("output")
        args.site_title = "My Blog"
        args.site_url = ""
        args.include_drafts = False
        args.posts_per_feed = 20
        args.extra_stylesheets = None
        args.port = 8000
        args.no_watch = False

        merge_config_with_args(config, args)

        assert args.content_dir == Path("posts")
        assert args.templates == Path("templates")
        assert args.output == Path("site")
        assert args.site_title == "Awesome Blog"
        assert args.site_url == "https://blog.example.com"
        assert args.include_drafts is True
        assert args.posts_per_feed == 25
        assert args.extra_stylesheets == ["custom.css"]
        assert args.port == 9000
        assert args.no_watch is False


class TestDefaultConfigFiles:
    """Test the DEFAULT_CONFIG_FILES constant."""

    def test_default_config_files_list(self) -> None:
        """Test that default config files are defined correctly."""
        assert DEFAULT_CONFIG_FILES == ["blogmore.yaml", "blogmore.yml"]
        assert len(DEFAULT_CONFIG_FILES) == 2


class TestPathExpansion:
    """Test path expansion with tilde (~) for user home directory."""

    def test_config_expands_tilde_in_content_dir(self, tmp_path: Path) -> None:
        """Test that tilde in content_dir from config is expanded."""
        from unittest.mock import Mock

        config = {"content_dir": "~/test-content"}
        args = Mock()
        args.content_dir = None

        merge_config_with_args(config, args)

        # Should expand to absolute path
        assert args.content_dir.is_absolute()
        assert str(args.content_dir).startswith("/")
        assert "~" not in str(args.content_dir)

    def test_config_expands_tilde_in_output(self, tmp_path: Path) -> None:
        """Test that tilde in output from config is expanded."""
        from unittest.mock import Mock

        config = {"output": "~/test-output"}
        args = Mock()
        args.output = Path("output")

        merge_config_with_args(config, args)

        # Should expand to absolute path
        assert args.output.is_absolute()
        assert str(args.output).startswith("/")
        assert "~" not in str(args.output)

    def test_config_expands_tilde_in_templates(self, tmp_path: Path) -> None:
        """Test that tilde in templates from config is expanded."""
        from unittest.mock import Mock

        config = {"templates": "~/test-templates"}
        args = Mock()
        args.templates = None

        merge_config_with_args(config, args)

        # Should expand to absolute path
        assert args.templates.is_absolute()
        assert str(args.templates).startswith("/")
        assert "~" not in str(args.templates)

    def test_config_without_tilde_works(self, tmp_path: Path) -> None:
        """Test that paths without tilde still work correctly."""
        from unittest.mock import Mock

        config = {"content_dir": "posts", "output": "site"}
        args = Mock()
        args.content_dir = None
        args.output = Path("output")

        merge_config_with_args(config, args)

        assert args.content_dir == Path("posts")
        assert args.output == Path("site")

    def test_merge_default_author_from_config(self) -> None:
        """Test merging default_author from config file."""
        from unittest.mock import Mock

        config = {"default_author": "Jane Smith"}
        args = Mock()
        args.default_author = None

        merge_config_with_args(config, args)

        assert args.default_author == "Jane Smith"

    def test_cli_default_author_overrides_config(self) -> None:
        """Test that CLI default_author takes precedence over config."""
        from unittest.mock import Mock

        config = {"default_author": "Config Author"}
        args = Mock()
        args.default_author = "CLI Author"

        merge_config_with_args(config, args)

        assert args.default_author == "CLI Author"



class TestGetSidebarConfig:
    """Test the get_sidebar_config function."""

    def test_extract_site_logo(self) -> None:
        """Test extracting site_logo from config."""
        config = {"site_logo": "/images/logo.png", "site_title": "My Blog"}
        result = get_sidebar_config(config)
        assert result == {"site_logo": "/images/logo.png"}

    def test_extract_links(self) -> None:
        """Test extracting links from config."""
        config = {
            "links": [
                {"title": "GitHub", "url": "https://github.com"},
                {"title": "Twitter", "url": "https://twitter.com"},
            ]
        }
        result = get_sidebar_config(config)
        assert result == {
            "links": [
                {"title": "GitHub", "url": "https://github.com"},
                {"title": "Twitter", "url": "https://twitter.com"},
            ]
        }

    def test_extract_socials(self) -> None:
        """Test extracting socials from config."""
        config = {
            "socials": [
                {"site": "mastodon", "url": "https://fosstodon.org/@user"},
                {"site": "github", "url": "https://github.com/user"},
            ]
        }
        result = get_sidebar_config(config)
        assert result == {
            "socials": [
                {"site": "mastodon", "url": "https://fosstodon.org/@user"},
                {"site": "github", "url": "https://github.com/user"},
            ]
        }

    def test_extract_all_sidebar_options(self) -> None:
        """Test extracting all sidebar options from config."""
        config = {
            "site_logo": "/images/logo.png",
            "links": [{"title": "Home", "url": "/"}],
            "socials": [{"site": "github", "url": "https://github.com"}],
            "site_title": "My Blog",
        }
        result = get_sidebar_config(config)
        assert result == {
            "site_logo": "/images/logo.png",
            "links": [{"title": "Home", "url": "/"}],
            "socials": [{"site": "github", "url": "https://github.com"}],
        }

    def test_extract_from_empty_config(self) -> None:
        """Test extracting from empty config returns empty dict."""
        config = {}
        result = get_sidebar_config(config)
        assert result == {}

    def test_extract_ignores_non_sidebar_options(self) -> None:
        """Test that non-sidebar options are not included."""
        config = {
            "site_title": "My Blog",
            "site_url": "https://example.com",
            "site_logo": "/logo.png",
        }
        result = get_sidebar_config(config)
        assert result == {"site_logo": "/logo.png"}
        assert "site_title" not in result
        assert "site_url" not in result
