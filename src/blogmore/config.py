"""Configuration file loading and merging for blogmore."""

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_FILES = ["blogmore.yaml", "blogmore.yml"]


def normalize_site_keywords(value: Any) -> list[str] | None:
    """Normalize site keywords from various input formats.

    Handles both comma-separated strings and lists of strings.

    Args:
        value: Keywords as a comma-separated string, a list of strings, or None

    Returns:
        List of stripped keyword strings, or None if no valid keywords
    """
    if value is None:
        return None
    if isinstance(value, list):
        keywords = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str):
        keywords = [kw.strip() for kw in value.split(",") if kw.strip()]
    else:
        return None
    return keywords if keywords else None


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from a YAML file.

    If no config_path is provided, searches for default config files
    (blogmore.yaml, blogmore.yml) in the current directory.

    Args:
        config_path: Optional path to a specific configuration file

    Returns:
        Dictionary containing configuration values, or empty dict if no config found
    """
    # If a specific config file is provided, use it
    if config_path is not None:
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        return _load_yaml_file(config_path)

    # Otherwise, search for default config files
    for config_file in DEFAULT_CONFIG_FILES:
        config_file_path = Path(config_file)
        if config_file_path.exists():
            return _load_yaml_file(config_file_path)

    # No config file found
    return {}


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load and parse a YAML file.

    Args:
        path: Path to the YAML file

    Returns:
        Dictionary containing the parsed YAML content
    """
    with open(path) as f:
        content = yaml.safe_load(f)
        # Handle empty files or files with only comments
        if content is None:
            return {}
        if not isinstance(content, dict):
            raise ValueError(
                f"Config file must contain a YAML dictionary, got {type(content).__name__}"
            )
        return content


def merge_config_with_args(config: dict[str, Any], args: Any) -> None:
    """Merge configuration file values with command-line arguments.

    Command-line arguments take precedence over configuration file values.
    Updates the args namespace in-place with values from config where
    CLI arguments have their default values.

    Args:
        config: Dictionary containing configuration file values
        args: argparse Namespace containing command-line arguments
    """
    # Define defaults for each argument to determine if CLI value was explicitly set
    defaults = {
        "site_title": "My Blog",
        "site_subtitle": "",
        "site_description": "",
        "site_keywords": None,
        "site_url": "",
        "output": Path("output"),
        "templates": None,
        "include_drafts": False,
        "posts_per_feed": 20,
        "extra_stylesheets": None,
        "port": 8000,
        "no_watch": False,
        "content_dir": None,
        "default_author": None,
        "clean_first": False,
        "branch": "gh-pages",
        "remote": "origin",
        "icon_source": None,
        "with_search": False,
        "with_sitemap": False,
        "minify_css": False,
        "minify_js": False,
    }

    # For each config key, update args if the arg value is still at its default
    for config_key, config_value in config.items():
        # Skip if this isn't a recognized config key
        if config_key not in defaults:
            continue

        # Skip if args doesn't have this attribute (e.g., port not in build command)
        if not hasattr(args, config_key):
            continue

        arg_value = getattr(args, config_key)
        default_value = defaults[config_key]

        # Check if the argument is still at its default value
        if arg_value == default_value:
            # Convert path strings to Path objects and expand user home directory
            if config_key in ("content_dir", "templates", "output"):
                setattr(args, config_key, Path(config_value).expanduser())
            # Handle extra_stylesheets specially
            elif config_key == "extra_stylesheets":
                if isinstance(config_value, list):
                    setattr(args, config_key, config_value)
                elif isinstance(config_value, str):
                    setattr(args, config_key, [config_value])
            # Handle site_keywords specially (supports list or comma-separated string)
            elif config_key == "site_keywords":
                normalized = normalize_site_keywords(config_value)
                if normalized is not None:
                    setattr(args, config_key, normalized)
            else:
                setattr(args, config_key, config_value)


def get_sidebar_config(config: dict[str, Any]) -> dict[str, Any]:
    """Extract sidebar configuration from the config dictionary.

    Returns sidebar configuration items (site_logo, links, socials) if they
    exist in the configuration file.

    Args:
        config: Dictionary containing configuration values

    Returns:
        Dictionary containing sidebar configuration values
    """
    sidebar_config: dict[str, Any] = {}

    for key in ("site_logo", "links", "socials"):
        if key in config:
            sidebar_config[key] = config[key]

    return sidebar_config
