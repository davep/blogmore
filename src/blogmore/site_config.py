"""Site configuration data structure for blogmore."""

##############################################################################
# Python imports.
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SiteConfig:
    """Configuration for static site generation.

    This dataclass holds all parameters required to describe and generate a
    static blog site.  It is passed to ``SiteGenerator`` and ``serve_site``
    so that callers do not need to manage large lists of individual keyword
    arguments.
    """

    output_dir: Path
    """Directory where the generated site will be written."""

    content_dir: Path | None = None
    """Directory containing Markdown posts.

    Required for site generation; may be ``None`` when serving an
    already-generated site without rebuilding.
    """

    templates_dir: Path | None = None
    """Optional directory containing custom Jinja2 templates.

    When ``None`` the bundled templates are used.
    """

    site_title: str = "My Blog"
    """Title of the blog site."""

    site_subtitle: str = ""
    """Subtitle displayed below the site title."""

    site_description: str = ""
    """Default description used in metadata for pages without their own description."""

    site_keywords: list[str] | None = None
    """Default keywords used in metadata for pages without their own keywords."""

    site_url: str = ""
    """Base URL of the site (e.g. ``https://example.com``)."""

    posts_per_feed: int = 20
    """Maximum number of posts to include in RSS/Atom feeds."""

    extra_stylesheets: list[str] | None = None
    """Optional list of URLs for additional stylesheets to include on every page."""

    default_author: str | None = None
    """Default author name for posts that lack an author in their frontmatter."""

    sidebar_config: dict[str, Any] = field(default_factory=dict)
    """Sidebar configuration (``site_logo``, ``links``, ``socials``, etc.)."""

    clean_first: bool = False
    """Whether to remove the output directory before generating."""

    icon_source: str | None = None
    """Optional source icon filename in the ``extras/`` directory."""

    with_search: bool = False
    """Whether to generate a search index and search page."""

    with_sitemap: bool = False
    """Whether to generate an XML sitemap."""

    minify_css: bool = False
    """Whether to minify the CSS, writing it as ``styles.min.css``."""

    minify_js: bool = False
    """Whether to minify the JavaScript output files."""

    with_read_time: bool = False
    """Whether to show estimated reading time on posts."""


### site_config.py ends here
