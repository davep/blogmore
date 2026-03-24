"""Site configuration data structure for blogmore."""

##############################################################################
# Python imports.
import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from blogmore.code_styles import DEFAULT_DARK_STYLE, DEFAULT_LIGHT_STYLE
from blogmore.page_path import DEFAULT_PAGE_PATH
from blogmore.pagination_path import DEFAULT_PAGE_1_PATH, DEFAULT_PAGE_N_PATH
from blogmore.post_path import DEFAULT_POST_PATH
from blogmore.utils import normalize_site_url

##############################################################################
# Default archive page path (relative to the output directory).
DEFAULT_ARCHIVE_PATH = "archive.html"

##############################################################################
# Default search page path (relative to the output directory).
DEFAULT_SEARCH_PATH = "search.html"

##############################################################################
# Default tags page path (relative to the output directory).
DEFAULT_TAGS_PATH = "tags.html"

##############################################################################
# Default categories page path (relative to the output directory).
DEFAULT_CATEGORIES_PATH = "categories.html"

##############################################################################
# Default stats page path (relative to the output directory).
DEFAULT_STATS_PATH = "stats.html"


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

    with_stats: bool = False
    """Whether to generate a blog statistics page."""

    minify_css: bool = False
    """Whether to minify the CSS, writing it as ``styles.min.css``."""

    minify_js: bool = False
    """Whether to minify the JavaScript output files."""

    minify_html: bool = False
    """Whether to minify all generated HTML output.

    When enabled, every ``.html`` file written by the generator is passed
    through the ``minify-html`` library before being saved.  The output
    file name is not changed — only the content is minified.  Off by
    default.
    """

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

    page_path: str = DEFAULT_PAGE_PATH
    """Format string used to determine each static page's output path and URL.

    The only available variable placeholder is ``{slug}``, which is required.
    """

    search_path: str = DEFAULT_SEARCH_PATH
    """Path (relative to the output directory) where the search page is written.

    The path is joined onto the ``output`` directory, so ``search.html``
    produces ``<output>/search.html``, and ``blog/search/index.html``
    produces ``<output>/blog/search/index.html``.

    Parent directories are created automatically.  When ``clean_urls`` is
    enabled and the path ends in ``index.html``, the ``index.html`` portion
    is omitted in any URL reference to the page.

    This is a **configuration file only** option — it cannot be set on the
    command line.  Defaults to ``search.html``.
    """

    archive_path: str = DEFAULT_ARCHIVE_PATH
    """Path (relative to the output directory) where the archive page is written.

    The path is joined onto the ``output`` directory, so ``archive.html``
    produces ``<output>/archive.html``, and ``blog/archive/index.html``
    produces ``<output>/blog/archive/index.html``.

    Parent directories are created automatically.  When ``clean_urls`` is
    enabled and the path ends in ``index.html``, the ``index.html`` portion
    is omitted in any URL reference to the page.

    The path is always treated as relative to the output directory root, so
    both ``/archive/index.html`` and ``archive/index.html`` produce the same
    output location.

    This is a **configuration file only** option — it cannot be set on the
    command line.  Defaults to ``archive.html``.
    """

    tags_path: str = DEFAULT_TAGS_PATH
    """Path (relative to the output directory) where the tags overview page is written.

    The path is joined onto the ``output`` directory, so ``tags.html``
    produces ``<output>/tags.html``, and ``blog/tags/index.html``
    produces ``<output>/blog/tags/index.html``.

    Parent directories are created automatically.  When ``clean_urls`` is
    enabled and the path ends in ``index.html``, the ``index.html`` portion
    is omitted in any URL reference to the page.

    The path is always treated as relative to the output directory root, so
    both ``/tags/index.html`` and ``tags/index.html`` produce the same
    output location.

    This is a **configuration file only** option — it cannot be set on the
    command line.  Defaults to ``tags.html``.
    """

    categories_path: str = DEFAULT_CATEGORIES_PATH
    """Path (relative to the output directory) where the categories overview page is written.

    The path is joined onto the ``output`` directory, so ``categories.html``
    produces ``<output>/categories.html``, and ``blog/categories/index.html``
    produces ``<output>/blog/categories/index.html``.

    Parent directories are created automatically.  When ``clean_urls`` is
    enabled and the path ends in ``index.html``, the ``index.html`` portion
    is omitted in any URL reference to the page.

    The path is always treated as relative to the output directory root, so
    both ``/categories/index.html`` and ``categories/index.html`` produce the
    same output location.

    This is a **configuration file only** option — it cannot be set on the
    command line.  Defaults to ``categories.html``.
    """

    stats_path: str = DEFAULT_STATS_PATH
    """Path (relative to the output directory) where the statistics page is written.

    The path is joined onto the ``output`` directory, so ``stats.html``
    produces ``<output>/stats.html``, and ``blog/stats/index.html``
    produces ``<output>/blog/stats/index.html``.

    Parent directories are created automatically.  When ``clean_urls`` is
    enabled and the path ends in ``index.html``, the ``index.html`` portion
    is omitted in any URL reference to the page.

    The path is always treated as relative to the output directory root, so
    both ``/stats/index.html`` and ``stats/index.html`` produce the same
    output location.

    Only used when ``with_stats`` is ``True``.  This is a **configuration
    file only** option — it cannot be set on the command line.  Defaults to
    ``stats.html``.
    """

    page_1_path: str = DEFAULT_PAGE_1_PATH
    """Output path template for the first page of any paginated listing.

    Controls the filename generated for page 1 of the main index, date
    archives, tag pages, and category pages.  The path is always appended
    to the end of the section base path being generated — so ``/some/path``
    and ``some/path`` are treated identically.

    The only available placeholder is ``{page}`` (the 1-based page number),
    though it is not required for this template since the first page is
    typically given a fixed name such as ``index.html``.

    This is a **configuration file only** option — it cannot be set on the
    command line.  Defaults to ``index.html``.
    """

    page_n_path: str = DEFAULT_PAGE_N_PATH
    """Output path template for pages 2 and above of any paginated listing.

    Controls the filename generated for pages 2, 3, … of the main index,
    date archives, tag pages, and category pages.  The path is always
    appended to the end of the section base path being generated.

    The ``{page}`` placeholder is **required** and is replaced with the
    1-based page number.

    This is a **configuration file only** option — it cannot be set on the
    command line.  Defaults to ``page/{page}.html``.
    """

    clean_urls: bool = False
    """Whether to generate clean URLs for posts and pages whose path ends in ``index.html``.

    When enabled, any post or page whose resolved URL ends with ``/index.html`` will
    have the ``index.html`` portion removed so that the URL ends with a
    trailing slash instead.  For example, a page at
    ``pages/about/index.html`` will be referenced everywhere as
    ``pages/about/`` rather than ``pages/about/index.html``.

    This is a **configuration file only** option — it cannot be set on the
    command line.  Off by default.
    """

    with_advert: bool = True
    """Whether to show the "Generated with BlogMore" footer line."""

    sidebar_pages: list[str] | None = None
    """Optional ordered list of page slugs to display in the sidebar.

    When ``None`` or empty, all pages from the ``pages/`` directory are listed
    in the sidebar (the default behaviour).  When set to a non-empty list, only
    the pages whose slug matches an entry in the list are linked in the sidebar,
    and they appear in the order defined here.

    This is a **configuration file only** option — it cannot be set on the
    command line.
    """

    head: list[dict[str, Any]] = field(default_factory=list)
    """Extra ``<head>`` tags to inject into every generated page.

    Each entry is a single-key mapping from an HTML tag name to a dict of
    attribute name/value pairs.  For example::

        [{"link": {"rel": "author", "href": "/humans.txt"}}]

    yields::

        <link rel="author" href="/humans.txt">

    This is a **configuration file only** option — it cannot be set on the
    command line.  Empty by default.
    """

    light_mode_code_style: str = DEFAULT_LIGHT_STYLE
    """Pygments style name used for syntax highlighting in light mode.

    Accepts any style name from the Pygments style gallery
    (https://pygments.org/styles/).  The chosen style is used to generate a
    ``code.css`` file (or ``code.min.css`` when ``minify_css`` is enabled)
    that is served alongside the main stylesheet.

    This is a **configuration file only** option — it cannot be set on the
    command line.  Defaults to ``"xcode"``.
    """

    dark_mode_code_style: str = DEFAULT_DARK_STYLE
    """Pygments style name used for syntax highlighting in dark mode.

    Accepts any style name from the Pygments style gallery
    (https://pygments.org/styles/).  The chosen style is used to generate a
    ``code.css`` file (or ``code.min.css`` when ``minify_css`` is enabled)
    that is served alongside the main stylesheet.

    This is a **configuration file only** option — it cannot be set on the
    command line.  Defaults to ``"github-dark"``.
    """

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
