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
    normalize_site_keywords,
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

    def test_site_subtitle_from_config(self) -> None:
        """Test loading site_subtitle from config."""
        config = {"site_subtitle": "My blog subtitle"}
        args = Mock()
        args.site_subtitle = ""  # default

        merge_config_with_args(config, args)

        assert args.site_subtitle == "My blog subtitle"

    def test_cli_site_subtitle_overrides_config(self) -> None:
        """Test that CLI site_subtitle overrides config."""
        config = {"site_subtitle": "Config subtitle"}
        args = Mock()
        args.site_subtitle = "CLI subtitle"

        merge_config_with_args(config, args)

        assert args.site_subtitle == "CLI subtitle"

    def test_site_description_from_config(self) -> None:
        """Test loading site_description from config."""
        config = {"site_description": "A great blog about stuff"}
        args = Mock()
        args.site_description = ""  # default

        merge_config_with_args(config, args)

        assert args.site_description == "A great blog about stuff"

    def test_cli_site_description_overrides_config(self) -> None:
        """Test that CLI site_description overrides config."""
        config = {"site_description": "Config description"}
        args = Mock()
        args.site_description = "CLI description"

        merge_config_with_args(config, args)

        assert args.site_description == "CLI description"

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
                {"site": "github", "url": "https://github.com/user"},
                {"site": "mastodon", "url": "https://fosstodon.org/@user"},
            ]
        }

    def test_extract_socials_already_sorted(self) -> None:
        """Test that socials already in alphabetical order remain sorted."""
        config = {
            "socials": [
                {"site": "github", "url": "https://github.com/user"},
                {"site": "mastodon", "url": "https://fosstodon.org/@user"},
            ]
        }
        result = get_sidebar_config(config)
        assert result == {
            "socials": [
                {"site": "github", "url": "https://github.com/user"},
                {"site": "mastodon", "url": "https://fosstodon.org/@user"},
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

    def test_extract_socials_title(self) -> None:
        """Test extracting socials_title from config."""
        config = {
            "socials_title": "Connect",
            "socials": [{"site": "github", "url": "https://github.com/user"}],
        }
        result = get_sidebar_config(config)
        assert result["socials_title"] == "Connect"

    def test_extract_all_sidebar_options_with_socials_title(self) -> None:
        """Test that socials_title is included when all sidebar options are present."""
        config = {
            "site_logo": "/images/logo.png",
            "links": [{"title": "Home", "url": "/"}],
            "socials": [{"site": "github", "url": "https://github.com"}],
            "socials_title": "Follow Me",
            "site_title": "My Blog",
        }
        result = get_sidebar_config(config)
        assert result == {
            "site_logo": "/images/logo.png",
            "links": [{"title": "Home", "url": "/"}],
            "socials": [{"site": "github", "url": "https://github.com"}],
            "socials_title": "Follow Me",
        }

    def test_socials_title_absent_when_not_in_config(self) -> None:
        """Test that socials_title is absent from sidebar config when not set."""
        config = {
            "socials": [{"site": "github", "url": "https://github.com/user"}],
        }
        result = get_sidebar_config(config)
        assert "socials_title" not in result

    def test_extract_links_title(self) -> None:
        """Test extracting links_title from config."""
        config = {
            "links_title": "Elsewhere",
            "links": [{"title": "Home", "url": "/"}],
        }
        result = get_sidebar_config(config)
        assert result["links_title"] == "Elsewhere"

    def test_extract_all_sidebar_options_with_links_title(self) -> None:
        """Test that links_title is included when all sidebar options are present."""
        config = {
            "site_logo": "/images/logo.png",
            "links": [{"title": "Home", "url": "/"}],
            "links_title": "Navigate",
            "socials": [{"site": "github", "url": "https://github.com"}],
            "socials_title": "Follow Me",
            "site_title": "My Blog",
        }
        result = get_sidebar_config(config)
        assert result == {
            "site_logo": "/images/logo.png",
            "links": [{"title": "Home", "url": "/"}],
            "links_title": "Navigate",
            "socials": [{"site": "github", "url": "https://github.com"}],
            "socials_title": "Follow Me",
        }

    def test_links_title_absent_when_not_in_config(self) -> None:
        """Test that links_title is absent from sidebar config when not set."""
        config = {
            "links": [{"title": "Home", "url": "/"}],
        }
        result = get_sidebar_config(config)
        assert "links_title" not in result


class TestCleanFirstConfig:
    """Test the clean_first configuration option."""

    def test_clean_first_from_config(self) -> None:
        """Test loading clean_first from config."""
        config = {"clean_first": True}
        args = Mock()
        args.clean_first = False  # default

        merge_config_with_args(config, args)

        assert args.clean_first is True

    def test_cli_clean_first_overrides_config(self) -> None:
        """Test that CLI clean_first overrides config."""
        config = {"clean_first": False}
        args = Mock()
        args.clean_first = True

        merge_config_with_args(config, args)

        assert args.clean_first is True

    def test_clean_first_defaults_to_false(self) -> None:
        """Test that clean_first defaults to False when not in config."""
        config = {}
        args = Mock()
        args.clean_first = False  # default

        merge_config_with_args(config, args)

        assert args.clean_first is False


class TestSocialsTitleConfig:
    """Test the socials_title configuration option."""

    def test_socials_title_from_config(self) -> None:
        """Test loading socials_title from config."""
        config = {"socials_title": "Connect"}
        args = Mock()
        args.socials_title = "Social"  # default

        merge_config_with_args(config, args)

        assert args.socials_title == "Connect"

    def test_cli_socials_title_overrides_config(self) -> None:
        """Test that CLI socials_title overrides config."""
        config = {"socials_title": "Connect"}
        args = Mock()
        args.socials_title = "Follow Me"  # explicitly set via CLI

        merge_config_with_args(config, args)

        assert args.socials_title == "Follow Me"

    def test_socials_title_defaults_to_social(self) -> None:
        """Test that socials_title defaults to 'Social' when not in config."""
        config = {}
        args = Mock()
        args.socials_title = "Social"  # default

        merge_config_with_args(config, args)

        assert args.socials_title == "Social"


class TestLinksTitleConfig:
    """Test the links_title configuration option."""

    def test_links_title_from_config(self) -> None:
        """Test loading links_title from config."""
        config = {"links_title": "Elsewhere"}
        args = Mock()
        args.links_title = "Links"  # default

        merge_config_with_args(config, args)

        assert args.links_title == "Elsewhere"

    def test_cli_links_title_overrides_config(self) -> None:
        """Test that CLI links_title overrides config."""
        config = {"links_title": "Elsewhere"}
        args = Mock()
        args.links_title = "Navigate"  # explicitly set via CLI

        merge_config_with_args(config, args)

        assert args.links_title == "Navigate"

    def test_links_title_defaults_to_links(self) -> None:
        """Test that links_title defaults to 'Links' when not in config."""
        config = {}
        args = Mock()
        args.links_title = "Links"  # default

        merge_config_with_args(config, args)

        assert args.links_title == "Links"


class TestNormalizeSiteKeywords:
    """Test the normalize_site_keywords function."""

    def test_none_returns_none(self) -> None:
        """Test that None input returns None."""
        assert normalize_site_keywords(None) is None

    def test_empty_string_returns_none(self) -> None:
        """Test that an empty string returns None."""
        assert normalize_site_keywords("") is None

    def test_comma_separated_string(self) -> None:
        """Test normalizing a comma-separated string."""
        result = normalize_site_keywords("python, web, programming")
        assert result == ["python", "web", "programming"]

    def test_comma_separated_string_no_spaces(self) -> None:
        """Test normalizing a comma-separated string without spaces."""
        result = normalize_site_keywords("python,web,programming")
        assert result == ["python", "web", "programming"]

    def test_list_of_strings(self) -> None:
        """Test normalizing a list of strings."""
        result = normalize_site_keywords(["python", "web", "programming"])
        assert result == ["python", "web", "programming"]

    def test_list_strips_whitespace(self) -> None:
        """Test that list items have whitespace stripped."""
        result = normalize_site_keywords(["  python  ", "  web  "])
        assert result == ["python", "web"]

    def test_string_strips_whitespace(self) -> None:
        """Test that string items have whitespace stripped."""
        result = normalize_site_keywords("  python  ,  web  ")
        assert result == ["python", "web"]

    def test_empty_list_returns_none(self) -> None:
        """Test that an empty list returns None."""
        assert normalize_site_keywords([]) is None

    def test_list_with_empty_strings_filters_them(self) -> None:
        """Test that empty strings in lists are filtered out."""
        result = normalize_site_keywords(["python", "", "web"])
        assert result == ["python", "web"]

    def test_string_with_trailing_comma(self) -> None:
        """Test handling a string with a trailing comma."""
        result = normalize_site_keywords("python, web,")
        assert result == ["python", "web"]

    def test_invalid_type_returns_none(self) -> None:
        """Test that an invalid type returns None."""
        assert normalize_site_keywords(42) is None  # type: ignore[arg-type]


class TestSiteKeywordsConfig:
    """Test site_keywords handling in merge_config_with_args."""

    def test_site_keywords_list_from_config(self) -> None:
        """Test loading site_keywords as a YAML list from config."""
        config = {"site_keywords": ["python", "web", "programming"]}
        args = Mock()
        args.site_keywords = None  # default

        merge_config_with_args(config, args)

        assert args.site_keywords == ["python", "web", "programming"]

    def test_site_keywords_string_from_config(self) -> None:
        """Test loading site_keywords as a comma-separated string from config."""
        config = {"site_keywords": "python, web, programming"}
        args = Mock()
        args.site_keywords = None  # default

        merge_config_with_args(config, args)

        assert args.site_keywords == ["python", "web", "programming"]

    def test_cli_site_keywords_overrides_config(self) -> None:
        """Test that a CLI-set site_keywords is not overridden by config."""
        config = {"site_keywords": ["config-kw"]}
        args = Mock()
        args.site_keywords = "cli-keyword"  # explicitly set by CLI (non-default)

        merge_config_with_args(config, args)

        # CLI value should not be overridden since it differs from default (None)
        assert args.site_keywords == "cli-keyword"

    def test_site_keywords_not_set_remains_none(self) -> None:
        """Test that site_keywords remains None when not in config."""
        config = {}
        args = Mock()
        args.site_keywords = None  # default

        merge_config_with_args(config, args)

        assert args.site_keywords is None

    def test_minify_css_from_config(self) -> None:
        """Test loading minify_css from config."""
        config = {"minify_css": True}
        args = Mock()
        args.minify_css = False  # default

        merge_config_with_args(config, args)

        assert args.minify_css is True

    def test_cli_minify_css_overrides_config(self) -> None:
        """Test that CLI minify_css overrides config."""
        config = {"minify_css": False}
        args = Mock()
        args.minify_css = True  # set via CLI

        merge_config_with_args(config, args)

        assert args.minify_css is True

    def test_minify_js_from_config(self) -> None:
        """Test loading minify_js from config."""
        config = {"minify_js": True}
        args = Mock()
        args.minify_js = False  # default

        merge_config_with_args(config, args)

        assert args.minify_js is True

    def test_cli_minify_js_overrides_config(self) -> None:
        """Test that CLI minify_js overrides config."""
        config = {"minify_js": False}
        args = Mock()
        args.minify_js = True  # set via CLI

        merge_config_with_args(config, args)

        assert args.minify_js is True

    def test_with_read_time_from_config(self) -> None:
        """Test loading with_read_time from config."""
        config = {"with_read_time": True}
        args = Mock()
        args.with_read_time = False  # default

        merge_config_with_args(config, args)

        assert args.with_read_time is True

    def test_cli_with_read_time_overrides_config(self) -> None:
        """Test that CLI with_read_time overrides config."""
        config = {"with_read_time": False}
        args = Mock()
        args.with_read_time = True  # set via CLI

        merge_config_with_args(config, args)

        assert args.with_read_time is True

    def test_minify_html_from_config(self) -> None:
        """Test loading minify_html from config."""
        config = {"minify_html": True}
        args = Mock()
        args.minify_html = False  # default

        merge_config_with_args(config, args)

        assert args.minify_html is True

    def test_cli_minify_html_overrides_config(self) -> None:
        """Test that CLI minify_html overrides config."""
        config = {"minify_html": False}
        args = Mock()
        args.minify_html = True  # set via CLI

        merge_config_with_args(config, args)

        assert args.minify_html is True


class TestParseSiteConfigFromDict:
    """Tests for the parse_site_config_from_dict function."""

    def test_empty_config_returns_defaults_for_explicit_fields(
        self, tmp_path: Path
    ) -> None:
        """An empty config dict returns path-template and html-path defaults."""
        from blogmore.config import parse_site_config_from_dict
        from blogmore.page_path import DEFAULT_PAGE_PATH
        from blogmore.pagination_path import DEFAULT_PAGE_1_PATH, DEFAULT_PAGE_N_PATH
        from blogmore.post_path import DEFAULT_POST_PATH
        from blogmore.site_config import (
            DEFAULT_ARCHIVE_PATH,
            DEFAULT_CATEGORIES_PATH,
            DEFAULT_SEARCH_PATH,
            DEFAULT_TAGS_PATH,
        )

        kwargs, errors = parse_site_config_from_dict({}, tmp_path)

        assert errors == []
        assert kwargs["post_path"] == DEFAULT_POST_PATH
        assert kwargs["page_path"] == DEFAULT_PAGE_PATH
        assert kwargs["page_1_path"] == DEFAULT_PAGE_1_PATH
        assert kwargs["page_n_path"] == DEFAULT_PAGE_N_PATH
        assert kwargs["search_path"] == DEFAULT_SEARCH_PATH
        assert kwargs["archive_path"] == DEFAULT_ARCHIVE_PATH
        assert kwargs["tags_path"] == DEFAULT_TAGS_PATH
        assert kwargs["categories_path"] == DEFAULT_CATEGORIES_PATH
        assert kwargs["sidebar_pages"] is None
        assert kwargs["head"] == []
        assert kwargs["extra_stylesheets"] is None

    def test_simple_scalar_fields_copied_when_present(self, tmp_path: Path) -> None:
        """Simple scalar fields present in the config are included in kwargs."""
        from blogmore.config import parse_site_config_from_dict

        config = {
            "site_title": "Test Blog",
            "site_subtitle": "A subtitle",
            "posts_per_feed": 10,
            "with_search": True,
            "minify_css": True,
            "with_advert": False,
            "clean_urls": True,
        }
        kwargs, errors = parse_site_config_from_dict(config, tmp_path)

        assert errors == []
        assert kwargs["site_title"] == "Test Blog"
        assert kwargs["site_subtitle"] == "A subtitle"
        assert kwargs["posts_per_feed"] == 10
        assert kwargs["with_search"] is True
        assert kwargs["minify_css"] is True
        assert kwargs["with_advert"] is False
        assert kwargs["clean_urls"] is True

    def test_simple_scalar_absent_resets_to_default(self, tmp_path: Path) -> None:
        """Simple scalar fields absent from config are reset to their SiteConfig defaults."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({}, tmp_path)

        assert errors == []
        assert kwargs["site_title"] == "My Blog"
        assert kwargs["site_subtitle"] == ""
        assert kwargs["with_search"] is False

    def test_simple_scalar_wrong_type_produces_error(self, tmp_path: Path) -> None:
        """A simple scalar field with the wrong type produces an error."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"site_title": 42, "posts_per_feed": "not-a-number"}, tmp_path
        )

        assert len(errors) == 2
        assert "site_title" not in kwargs
        assert "posts_per_feed" not in kwargs

    def test_bool_field_rejects_int(self, tmp_path: Path) -> None:
        """A bool field with an int value produces an error."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({"with_search": 1}, tmp_path)

        assert len(errors) == 1
        assert "with_search" not in kwargs

    def test_optional_str_field_accepts_none(self, tmp_path: Path) -> None:
        """An Optional[str] field accepts None."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({"default_author": None}, tmp_path)

        assert errors == []
        assert kwargs["default_author"] is None

    def test_optional_str_field_accepts_string(self, tmp_path: Path) -> None:
        """An Optional[str] field accepts a string value."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"default_author": "Alice"}, tmp_path
        )

        assert errors == []
        assert kwargs["default_author"] == "Alice"

    def test_site_keywords_normalised_from_string(self, tmp_path: Path) -> None:
        """site_keywords as a comma-separated string is normalised to a list."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"site_keywords": "python, blog, tech"}, tmp_path
        )

        assert errors == []
        assert kwargs["site_keywords"] == ["python", "blog", "tech"]

    def test_site_keywords_normalised_from_list(self, tmp_path: Path) -> None:
        """site_keywords as a list is passed through."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"site_keywords": ["python", "blog"]}, tmp_path
        )

        assert errors == []
        assert kwargs["site_keywords"] == ["python", "blog"]

    def test_site_keywords_absent_resets_to_none(self, tmp_path: Path) -> None:
        """site_keywords absent from config resets to None (the SiteConfig default)."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({}, tmp_path)

        assert errors == []
        assert kwargs["site_keywords"] is None

    def test_extra_stylesheets_string_normalised_to_list(self, tmp_path: Path) -> None:
        """extra_stylesheets as a string is wrapped in a list."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"extra_stylesheets": "custom.css"}, tmp_path
        )

        assert errors == []
        assert kwargs["extra_stylesheets"] == ["custom.css"]

    def test_extra_stylesheets_list_passed_through(self, tmp_path: Path) -> None:
        """extra_stylesheets as a list is passed through unchanged."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"extra_stylesheets": ["a.css", "b.css"]}, tmp_path
        )

        assert errors == []
        assert kwargs["extra_stylesheets"] == ["a.css", "b.css"]

    def test_extra_stylesheets_absent_uses_cli_override(self, tmp_path: Path) -> None:
        """When extra_stylesheets is absent from config, cli_overrides is used."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {}, tmp_path, cli_overrides={"extra_stylesheets": ["cli.css"]}
        )

        assert errors == []
        assert kwargs["extra_stylesheets"] == ["cli.css"]

    def test_extra_stylesheets_absent_no_override_returns_none(
        self, tmp_path: Path
    ) -> None:
        """When extra_stylesheets is absent and no cli_overrides, returns None."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({}, tmp_path)

        assert errors == []
        assert kwargs["extra_stylesheets"] is None

    def test_valid_post_path(self, tmp_path: Path) -> None:
        """A valid post_path template is accepted."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"post_path": "{year}/{month}/{slug}.html"}, tmp_path
        )

        assert errors == []
        assert kwargs["post_path"] == "{year}/{month}/{slug}.html"

    def test_invalid_post_path_produces_error(self, tmp_path: Path) -> None:
        """An invalid post_path (missing {slug}) produces an error."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"post_path": "{year}/{month}/noslug.html"}, tmp_path
        )

        assert len(errors) == 1
        assert "post_path" not in kwargs

    def test_non_string_post_path_produces_error(self, tmp_path: Path) -> None:
        """A non-string post_path produces an error."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({"post_path": 42}, tmp_path)

        assert len(errors) == 1
        assert "post_path" not in kwargs

    def test_valid_search_path(self, tmp_path: Path) -> None:
        """A valid search_path ending in .html is accepted."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"search_path": "find/index.html"}, tmp_path
        )

        assert errors == []
        assert kwargs["search_path"] == "find/index.html"

    def test_search_path_must_end_with_html(self, tmp_path: Path) -> None:
        """A search_path not ending in .html produces an error."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"search_path": "search.htm"}, tmp_path
        )

        assert len(errors) == 1
        assert "search_path" not in kwargs

    def test_search_path_must_not_be_empty(self, tmp_path: Path) -> None:
        """An empty search_path produces an error."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({"search_path": ""}, tmp_path)

        assert len(errors) == 1
        assert "search_path" not in kwargs

    def test_html_path_must_not_escape_output_dir(self, tmp_path: Path) -> None:
        """A search_path that escapes the output directory produces an error."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"search_path": "../outside.html"}, tmp_path
        )

        assert len(errors) == 1
        assert "search_path" not in kwargs

    def test_all_html_path_fields_validated(self, tmp_path: Path) -> None:
        """All four html path fields (search, archive, tags, categories) are validated."""
        from blogmore.config import parse_site_config_from_dict

        config = {
            "search_path": "bad",
            "archive_path": "also-bad",
            "tags_path": "no-html",
            "categories_path": "",
        }
        kwargs, errors = parse_site_config_from_dict(config, tmp_path)

        assert len(errors) == 4
        assert "search_path" not in kwargs
        assert "archive_path" not in kwargs
        assert "tags_path" not in kwargs
        assert "categories_path" not in kwargs

    def test_sidebar_pages_via_pages_key(self, tmp_path: Path) -> None:
        """sidebar_pages is read from the YAML 'pages' key."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"pages": ["about", "contact"]}, tmp_path
        )

        assert errors == []
        assert kwargs["sidebar_pages"] == ["about", "contact"]

    def test_sidebar_pages_absent_resets_to_none(self, tmp_path: Path) -> None:
        """When 'pages' is absent, sidebar_pages is reset to None (show all)."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({}, tmp_path)

        assert errors == []
        assert kwargs["sidebar_pages"] is None

    def test_sidebar_pages_empty_list_becomes_none(self, tmp_path: Path) -> None:
        """An empty 'pages' list is normalised to None."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({"pages": []}, tmp_path)

        assert errors == []
        assert kwargs["sidebar_pages"] is None

    def test_sidebar_pages_invalid_produces_error(self, tmp_path: Path) -> None:
        """A non-list 'pages' value produces an error."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({"pages": "about"}, tmp_path)

        assert len(errors) == 1
        assert "sidebar_pages" not in kwargs

    def test_head_valid_tags(self, tmp_path: Path) -> None:
        """A valid head list is accepted."""
        from blogmore.config import parse_site_config_from_dict

        head = [{"link": {"rel": "author", "href": "/humans.txt"}}]
        kwargs, errors = parse_site_config_from_dict({"head": head}, tmp_path)

        assert errors == []
        assert kwargs["head"] == head

    def test_head_absent_resets_to_empty_list(self, tmp_path: Path) -> None:
        """When 'head' is absent, head is reset to an empty list."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({}, tmp_path)

        assert errors == []
        assert kwargs["head"] == []

    def test_head_invalid_structure_produces_error(self, tmp_path: Path) -> None:
        """A malformed head list produces an error."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"head": [{"a": 1, "b": 2}]}, tmp_path
        )

        assert len(errors) == 1
        assert "head" not in kwargs

    def test_multiple_errors_collected(self, tmp_path: Path) -> None:
        """Multiple invalid fields produce multiple errors; valid fields still returned."""
        from blogmore.config import parse_site_config_from_dict

        config = {
            "post_path": "no-slug.html",
            "search_path": "bad-extension.htm",
            "site_title": "Good Title",
        }
        kwargs, errors = parse_site_config_from_dict(config, tmp_path)

        assert len(errors) == 2
        assert "post_path" not in kwargs
        assert "search_path" not in kwargs
        assert kwargs["site_title"] == "Good Title"

    def test_no_structural_fields_returned(self, tmp_path: Path) -> None:
        """Structural fields (output_dir, content_dir, etc.) are never in kwargs."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, _ = parse_site_config_from_dict(
            {
                "output_dir": "/some/path",
                "content_dir": "/content",
                "templates_dir": "/tmpl",
                "sidebar_config": {"key": "value"},
            },
            tmp_path,
        )

        assert "output_dir" not in kwargs
        assert "content_dir" not in kwargs
        assert "templates_dir" not in kwargs
        assert "sidebar_config" not in kwargs

    def test_config_only_scalar_absent_resets_to_default(self, tmp_path: Path) -> None:
        """Config-file-only scalars reset to the SiteConfig default when absent.

        Removing clean_urls or with_advert from the config file during a serve
        reload must reset those fields to their SiteConfig defaults rather than
        preserving the stale previous value via dataclasses.replace.
        """
        from blogmore.config import parse_site_config_from_dict

        # Neither field present → defaults returned
        kwargs, errors = parse_site_config_from_dict({}, tmp_path)

        assert errors == []
        # SiteConfig defaults
        assert kwargs["clean_urls"] is False
        assert kwargs["with_advert"] is True

    def test_config_only_scalar_value_overrides_default(self, tmp_path: Path) -> None:
        """Config-file-only scalars use the config value when present."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"clean_urls": True, "with_advert": False}, tmp_path
        )

        assert errors == []
        assert kwargs["clean_urls"] is True
        assert kwargs["with_advert"] is False

    def test_overlapping_scalar_absent_resets_to_default(self, tmp_path: Path) -> None:
        """Overlapping CLI+config scalars absent from config reset to SiteConfig defaults.

        When a key is removed from the config file during a serve-mode reload
        and no CLI override was supplied, the field must revert to its SiteConfig
        class default rather than preserving a stale previous value.
        """
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({}, tmp_path)

        assert errors == []
        # All overlapping fields absent from config with no CLI override reset to defaults.
        assert kwargs["site_title"] == "My Blog"
        assert kwargs["with_search"] is False
        assert kwargs["include_drafts"] is False

    def test_overlapping_scalar_absent_uses_cli_override(self, tmp_path: Path) -> None:
        """When a key is absent from config but a CLI override was set, the override is used.

        This simulates a serve-mode reload where the user removes a key from the
        config file, but the value had originally been provided via a CLI flag.
        The CLI value must always win.
        """
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {},
            tmp_path,
            cli_overrides={"site_title": "CLI Title", "with_search": True},
        )

        assert errors == []
        assert kwargs["site_title"] == "CLI Title"
        assert kwargs["with_search"] is True

    def test_cli_override_wins_over_config_value(self, tmp_path: Path) -> None:
        """A CLI override takes precedence over the corresponding config-file value."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"site_title": "Config Title", "posts_per_feed": 5},
            tmp_path,
            cli_overrides={"site_title": "CLI Title"},
        )

        assert errors == []
        assert kwargs["site_title"] == "CLI Title"
        # Fields without a CLI override still use the config-file value.
        assert kwargs["posts_per_feed"] == 5

    def test_site_keywords_absent_uses_cli_override(self, tmp_path: Path) -> None:
        """When site_keywords is absent from config, the CLI override is used."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {},
            tmp_path,
            cli_overrides={"site_keywords": "python, blog"},
        )

        assert errors == []
        assert kwargs["site_keywords"] == ["python", "blog"]

    def test_site_keywords_cli_override_wins_over_config(self, tmp_path: Path) -> None:
        """A site_keywords CLI override wins even when the config file also has the key."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"site_keywords": ["config", "keywords"]},
            tmp_path,
            cli_overrides={"site_keywords": "cli, keywords"},
        )

        assert errors == []
        assert kwargs["site_keywords"] == ["cli", "keywords"]

    def test_extra_stylesheets_cli_override_wins_over_config(
        self, tmp_path: Path
    ) -> None:
        """A CLI extra_stylesheets override wins even when the config file also has the key."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"extra_stylesheets": "config.css"},
            tmp_path,
            cli_overrides={"extra_stylesheets": ["cli.css"]},
        )

        assert errors == []
        assert kwargs["extra_stylesheets"] == ["cli.css"]

    def test_read_time_wpm_valid_value(self, tmp_path: Path) -> None:
        """A valid positive integer read_time_wpm is accepted."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({"read_time_wpm": 250}, tmp_path)

        assert errors == []
        assert kwargs["read_time_wpm"] == 250

    def test_read_time_wpm_absent_resets_to_default(self, tmp_path: Path) -> None:
        """When read_time_wpm is absent from config, it resets to the default (200)."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({}, tmp_path)

        assert errors == []
        assert kwargs["read_time_wpm"] == 200

    def test_read_time_wpm_zero_produces_error(self, tmp_path: Path) -> None:
        """A read_time_wpm of zero produces an error and uses the default."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({"read_time_wpm": 0}, tmp_path)

        assert len(errors) == 1
        assert "read_time_wpm" in errors[0]
        assert kwargs["read_time_wpm"] == 200

    def test_read_time_wpm_negative_produces_error(self, tmp_path: Path) -> None:
        """A negative read_time_wpm produces an error and uses the default."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict({"read_time_wpm": -50}, tmp_path)

        assert len(errors) == 1
        assert "read_time_wpm" in errors[0]
        assert kwargs["read_time_wpm"] == 200

    def test_read_time_wpm_non_integer_produces_error(self, tmp_path: Path) -> None:
        """A non-integer read_time_wpm produces an error and uses the default."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"read_time_wpm": "fast"}, tmp_path
        )

        assert len(errors) == 1
        assert "read_time_wpm" in errors[0]
        assert kwargs["read_time_wpm"] == 200

    def test_read_time_wpm_bool_produces_error(self, tmp_path: Path) -> None:
        """A boolean read_time_wpm produces an error (booleans are subclasses of int)."""
        from blogmore.config import parse_site_config_from_dict

        kwargs, errors = parse_site_config_from_dict(
            {"read_time_wpm": True}, tmp_path
        )

        assert len(errors) == 1
        assert "read_time_wpm" in errors[0]
        assert kwargs["read_time_wpm"] == 200
