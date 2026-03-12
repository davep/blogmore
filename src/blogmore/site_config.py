"""Site configuration data structure for blogmore."""

##############################################################################
# Python imports.
import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from blogmore.post_path import DEFAULT_POST_PATH
from blogmore.utils import normalize_site_url


@dataclass
class SiteConfig:
    """Configuration describing a static blog site.

    Holds all parameters required to describe the content, presentation and
    build options for a site.
    """

    output_dir: Path
    """Directory where the generated site will be written."""

    content_dir: Path | None = None
    """Directory containing Markdown posts.

    May be ``None`` when serving an already-generated site without rebuilding.
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

    include_drafts: bool = False
    """Whether to include draft posts in generation."""

    post_path: str = DEFAULT_POST_PATH
    """Format string used to determine each post's output path and URL.

    Variable placeholders available: ``{year}``, ``{month}``, ``{day}``,
    ``{hour}``, ``{minute}``, ``{second}``, ``{category}``, ``{author}``,
    ``{slug}``.  The ``{slug}`` placeholder is required.
    """

    with_advert: bool = True
    """Whether to show the "Generated with BlogMore" footer line."""

    def __post_init__(self) -> None:
        """Normalise fields after initialisation."""
        self.site_url = normalize_site_url(self.site_url)
        # Resolve output_dir to an absolute path so that Path.relative_to()
        # calls in the generator always work, even when the user supplies a
        # relative path such as "site" or "./output".
        self.output_dir = self.output_dir.resolve()


def site_config_defaults() -> dict[str, Any]:
    """Return the default values for all SiteConfig fields that have scalar defaults.

    Fields that use ``default_factory`` (such as ``sidebar_config``) and
    required fields with no default (such as ``output_dir``) are excluded.

    Returns:
        Mapping from field name to its default value.
    """
    return {
        f.name: f.default
        for f in dataclasses.fields(SiteConfig)
        if f.default is not dataclasses.MISSING
    }


### site_config.py ends here
