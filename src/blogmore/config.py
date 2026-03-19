"""Configuration file loading and merging for blogmore."""

import dataclasses
import typing
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from blogmore.page_path import DEFAULT_PAGE_PATH, validate_page_path_template
from blogmore.pagination_path import (
    DEFAULT_PAGE_1_PATH,
    DEFAULT_PAGE_N_PATH,
    validate_page_1_path_template,
    validate_page_n_path_template,
)
from blogmore.post_path import DEFAULT_POST_PATH, validate_post_path_template
from blogmore.site_config import (
    DEFAULT_ARCHIVE_PATH,
    DEFAULT_CATEGORIES_PATH,
    DEFAULT_SEARCH_PATH,
    DEFAULT_TAGS_PATH,
    SiteConfig,
    site_config_defaults,
)

##############################################################################
# Fields set from program structure or CLI arguments, not from the YAML file.
# These are excluded from config-dict parsing entirely.
_STRUCTURAL_FIELDS: frozenset[str] = frozenset(
    {
        "output_dir",
        "content_dir",
        "templates_dir",
        "sidebar_config",
    }
)

##############################################################################
# Fields that require explicit parsing (validation, normalisation, or YAML key
# aliasing). These are excluded from the automatic simple-scalar handler and
# processed individually in parse_site_config_from_dict.
_EXPLICIT_HANDLED_FIELDS: frozenset[str] = frozenset(
    {
        "site_keywords",
        "extra_stylesheets",
        "post_path",
        "page_path",
        "page_1_path",
        "page_n_path",
        "search_path",
        "archive_path",
        "tags_path",
        "categories_path",
        "sidebar_pages",
        "head",
    }
)

##############################################################################
# Simple scalar fields that exist only in the config file and have no CLI
# equivalent.  When one of these is absent from the config dict during a
# serve-mode reload, parse_site_config_from_dict must include it in the
# returned kwargs using the SiteConfig class default so that removing the key
# resets the value rather than preserving the previous (stale) one.
#
# Overlapping CLI+config scalar fields (site_title, with_search, etc.) are
# intentionally NOT listed here: those must preserve the existing value when
# absent so that an explicit CLI override is not silently dropped on reload.
_CONFIG_ONLY_SCALAR_FIELDS: frozenset[str] = frozenset(
    {
        "with_advert",
        "clean_urls",
    }
)

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
    # Build defaults from SiteConfig (single source of truth for site config fields).
    defaults: dict[str, Any] = site_config_defaults()
    # SiteConfig uses templates_dir but the CLI arg is named templates.
    defaults["templates"] = defaults.pop("templates_dir")
    # SiteConfig.output_dir is a required field with no default; the CLI arg
    # output defaults to Path("output").
    defaults["output"] = Path("output")
    # Defaults for CLI-only arguments that have no SiteConfig equivalent.
    defaults.update(
        {
            "port": 8000,
            "no_watch": False,
            "branch": "gh-pages",
            "remote": "origin",
            "socials_title": "Social",
            "links_title": "Links",
        }
    )

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

    Returns sidebar configuration items (site_logo, links, socials,
    socials_title, links_title) if they exist in the configuration file.
    The ``socials`` list is sorted alphabetically by site name.

    Args:
        config: Dictionary containing configuration values

    Returns:
        Dictionary containing sidebar configuration values
    """
    sidebar_config: dict[str, Any] = {}

    for key in ("site_logo", "links", "socials", "socials_title", "links_title"):
        if key in config:
            sidebar_config[key] = config[key]

    if "socials" in sidebar_config and isinstance(sidebar_config["socials"], list):
        sidebar_config["socials"] = sorted(
            sidebar_config["socials"],
            key=lambda s: (
                str(s.get("site", "")).casefold() if isinstance(s, dict) else ""
            ),
        )

    return sidebar_config


def _is_simple_scalar_hint(hint: Any) -> bool:
    """Return True if the type hint is a simple scalar we can safely copy from config.

    Recognises str, int, bool, and their Optional (``X | None``) variants.

    Args:
        hint: A resolved type hint (as returned by typing.get_type_hints).

    Returns:
        True if the hint is a simple scalar, False otherwise.
    """
    if hint in (str, int, bool):
        return True
    # Handles both ``str | None`` (types.UnionType) and ``Optional[str]``
    # (typing.Union), since typing.get_args works for both.
    args = typing.get_args(hint)
    if args:
        non_none = [a for a in args if a is not type(None)]
        return len(non_none) == 1 and non_none[0] in (str, int, bool)
    return False


def _check_simple_scalar_value(value: Any, hint: Any) -> bool:
    """Return True if value is a valid instance of the given simple scalar hint.

    Ensures bool values are not accepted for int fields and vice versa, to
    guard against accidental YAML type coercions.

    Args:
        value: The value to check.
        hint: A resolved simple-scalar type hint.

    Returns:
        True if the value is type-compatible with the hint.
    """
    if hint is bool:
        return isinstance(value, bool)
    if hint is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if hint is str:
        return isinstance(value, str)
    # Optional (X | None)
    args = typing.get_args(hint)
    if args:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            if value is None:
                return True
            base = non_none[0]
            if base is bool:
                return isinstance(value, bool)
            if base is int:
                return isinstance(value, int) and not isinstance(value, bool)
            if base is str:
                return isinstance(value, str)
    return False


def parse_site_config_from_dict(
    config: dict[str, Any],
    output_dir: Path,
    cli_overrides: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Parse all config-file-controlled SiteConfig fields from a raw dict.

    Validates and normalises every field that can appear in the YAML
    configuration file.  Simple scalar fields (str, int, bool, and their
    Optional variants) are discovered automatically from SiteConfig using
    dataclasses introspection so that newly-added simple scalar fields are
    handled without any code changes here.  Fields that require validation or
    normalisation are handled explicitly.

    Fields that fail validation are omitted from the returned kwargs dict so
    that a caller using ``dataclasses.replace()`` will preserve the existing
    SiteConfig value for those fields.

    Absent-field semantics differ by field category:

    * **Config-file-only scalars** (``_CONFIG_ONLY_SCALAR_FIELDS``): when the
      key is absent the SiteConfig class default is included in kwargs so that
      removing the key resets the value rather than preserving a stale one.
    * **Overlapping CLI+config scalars** (e.g. ``site_title``): when the key
      is absent the field is omitted from kwargs so that an explicit CLI
      override supplied at startup is not silently dropped on reload.
    * **Explicit fields** (path templates, html paths, ``sidebar_pages``,
      ``head``): always included in kwargs, using their SiteConfig defaults
      when absent.

    Args:
        config: Raw configuration dictionary loaded from the YAML file.
        output_dir: The site output directory, used to verify that path fields
            do not escape it.
        cli_overrides: Optional dict of values explicitly set via the CLI.
            Currently used to restore the CLI-provided ``extra_stylesheets``
            when that key is absent from the config file.

    Returns:
        A tuple ``(kwargs, errors)`` where ``kwargs`` is a dict suitable for
        passing to ``SiteConfig()`` or ``dataclasses.replace()``, and
        ``errors`` is a list of human-readable validation messages (empty when
        all fields are valid).
    """
    overrides: dict[str, Any] = cli_overrides or {}
    kwargs: dict[str, Any] = {}
    errors: list[str] = []
    resolved_output = output_dir.resolve()

    # --- Auto-discover simple scalar fields via SiteConfig introspection -----
    hints: dict[str, Any] = typing.get_type_hints(SiteConfig)
    for field in dataclasses.fields(SiteConfig):
        name = field.name
        if name in _STRUCTURAL_FIELDS or name in _EXPLICIT_HANDLED_FIELDS:
            continue
        hint = hints.get(name)
        if hint is None or not _is_simple_scalar_hint(hint):
            continue
        if name in config:
            value = config[name]
            if _check_simple_scalar_value(value, hint):
                kwargs[name] = value
            else:
                errors.append(
                    f"{name} in the configuration file has an unexpected type; "
                    "ignoring value"
                )
        elif name in _CONFIG_ONLY_SCALAR_FIELDS:
            # Config-file-only fields have no CLI equivalent to fall back on,
            # so removing the key from the config file must reset the value to
            # the SiteConfig class default rather than preserving the stale one.
            if field.default is not dataclasses.MISSING:
                kwargs[name] = field.default

    # --- site_keywords -------------------------------------------------------
    if "site_keywords" in config:
        kwargs["site_keywords"] = normalize_site_keywords(config["site_keywords"])

    # --- extra_stylesheets ---------------------------------------------------
    if "extra_stylesheets" in config:
        raw_stylesheets = config["extra_stylesheets"]
        if isinstance(raw_stylesheets, str):
            kwargs["extra_stylesheets"] = [raw_stylesheets]
        elif isinstance(raw_stylesheets, list):
            kwargs["extra_stylesheets"] = raw_stylesheets
        else:
            errors.append(
                "extra_stylesheets in the configuration file must be a string "
                "or a list; ignoring value"
            )
    else:
        kwargs["extra_stylesheets"] = overrides.get("extra_stylesheets")

    # --- Path template fields ------------------------------------------------
    _path_template_validators: list[tuple[str, str, Callable[[str], None]]] = [
        ("post_path", DEFAULT_POST_PATH, validate_post_path_template),
        ("page_path", DEFAULT_PAGE_PATH, validate_page_path_template),
        ("page_1_path", DEFAULT_PAGE_1_PATH, validate_page_1_path_template),
        ("page_n_path", DEFAULT_PAGE_N_PATH, validate_page_n_path_template),
    ]
    for field_name, default, validator in _path_template_validators:
        raw = config.get(field_name, default)
        if not isinstance(raw, str):
            errors.append(
                f"{field_name} in the configuration file must be a string; "
                "using the default"
            )
        else:
            try:
                validator(raw)
                kwargs[field_name] = raw
            except ValueError as exc:
                errors.append(
                    f"Invalid {field_name} in the configuration file: {exc}; "
                    "using the default"
                )

    # --- HTML path fields ----------------------------------------------------
    _html_path_defaults: list[tuple[str, str]] = [
        ("search_path", DEFAULT_SEARCH_PATH),
        ("archive_path", DEFAULT_ARCHIVE_PATH),
        ("tags_path", DEFAULT_TAGS_PATH),
        ("categories_path", DEFAULT_CATEGORIES_PATH),
    ]
    for field_name, default in _html_path_defaults:
        raw = config.get(field_name, default)
        if not isinstance(raw, str):
            errors.append(
                f"{field_name} in the configuration file must be a string; "
                "using the default"
            )
            continue
        if not raw:
            errors.append(
                f"{field_name} in the configuration file must not be empty; "
                "using the default"
            )
            continue
        if not raw.endswith(".html"):
            errors.append(
                f"{field_name} in the configuration file must end with '.html'; "
                "using the default"
            )
            continue
        resolved_path = (resolved_output / raw.lstrip("/")).resolve()
        if not resolved_path.is_relative_to(resolved_output):
            errors.append(
                f"{field_name} in the configuration file must not escape the "
                "output directory; using the default"
            )
            continue
        kwargs[field_name] = raw

    # --- sidebar_pages (YAML key: "pages") -----------------------------------
    raw_sidebar_pages = config.get("pages")
    if raw_sidebar_pages is None:
        kwargs["sidebar_pages"] = None
    elif isinstance(raw_sidebar_pages, list) and all(
        isinstance(item, str) for item in raw_sidebar_pages
    ):
        kwargs["sidebar_pages"] = raw_sidebar_pages if raw_sidebar_pages else None
    else:
        errors.append(
            "pages in the configuration file must be a list of page slugs; "
            "ignoring value"
        )

    # --- head ----------------------------------------------------------------
    raw_head = config.get("head")
    if raw_head is None:
        kwargs["head"] = []
    elif isinstance(raw_head, list) and all(
        isinstance(item, dict) and len(item) == 1 for item in raw_head
    ):
        kwargs["head"] = raw_head
    else:
        errors.append(
            "head in the configuration file must be a list of single-key tag "
            "mappings; ignoring value"
        )

    return kwargs, errors
