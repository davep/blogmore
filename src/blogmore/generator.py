"""Static site generator for blog content."""

import datetime as dt
import shutil
import time
import urllib.error
from collections import defaultdict
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path
from typing import Any

import minify_html
import rcssmin  # type: ignore[import-untyped]
import rjsmin  # type: ignore[import-untyped]

from blogmore import __version__
from blogmore.backlinks import Backlink, build_backlink_map
from blogmore.calendar import CalendarYear, build_calendar
from blogmore.clean_url import make_url_clean
from blogmore.code_styles import build_code_css
from blogmore.comment_invite import build_mailto_url, get_invite_email_for_post
from blogmore.feeds import BlogFeedGenerator
from blogmore.fontawesome import (
    FONTAWESOME_CDN_BRANDS_WOFF2_URL,
    FONTAWESOME_CDN_CSS_URL,
    FONTAWESOME_LOCAL_CSS_MINIFIED_PATH,
    FONTAWESOME_LOCAL_CSS_PATH,
    FontAwesomeOptimizer,
)
from blogmore.graph import GraphData, build_graph_data
from blogmore.icons import IconGenerator, detect_source_icon
from blogmore.page_path import compute_page_output_path
from blogmore.pagination_path import resolve_pagination_page_path
from blogmore.parser import (
    CUSTOM_404_HTML,
    Page,
    Post,
    PostParser,
    post_sort_key,
    sanitize_for_url,
)
from blogmore.post_path import compute_output_path
from blogmore.renderer import TemplateRenderer
from blogmore.search import write_search_index
from blogmore.site_config import SiteConfig
from blogmore.sitemap import write_sitemap
from blogmore.stats import BlogStats, compute_blog_stats

CSS_FILENAME = "style.css"
SEARCH_CSS_FILENAME = "search.css"
STATS_CSS_FILENAME = "stats.css"
ARCHIVE_CSS_FILENAME = "archive.css"
CALENDAR_CSS_FILENAME = "calendar.css"
GRAPH_CSS_FILENAME = "graph.css"
TAG_CLOUD_CSS_FILENAME = "tag-cloud.css"
GRAPH_JS_FILENAME = "graph.js"
CODE_CSS_FILENAME = "code.css"
THEME_JS_FILENAME = "theme.js"
SEARCH_JS_FILENAME = "search.js"
CODEBLOCKS_JS_FILENAME = "codeblocks.js"

# All page-specific CSS files (source filenames only).
_PAGE_SPECIFIC_CSS: list[str] = [
    SEARCH_CSS_FILENAME,
    STATS_CSS_FILENAME,
    ARCHIVE_CSS_FILENAME,
    TAG_CLOUD_CSS_FILENAME,
    CALENDAR_CSS_FILENAME,
    GRAPH_CSS_FILENAME,
]


def minified_filename(source: str) -> str:
    """Compute the minified output filename for a given source filename.

    Transforms the file extension: ``.css`` becomes ``.min.css`` and
    ``.js`` becomes ``.min.js``.  For example, ``theme.js`` becomes
    ``theme.min.js`` and ``style.css`` becomes ``style.min.css``.

    Args:
        source: Source filename ending in ``.css`` or ``.js``.

    Returns:
        The corresponding minified filename.

    Raises:
        ValueError: If *source* does not end with ``.css`` or ``.js``.
    """
    if source.endswith(".css"):
        return source[: -len(".css")] + ".min.css"
    if source.endswith(".js"):
        return source[: -len(".js")] + ".min.js"
    raise ValueError(f"Unsupported file extension for minification: {source!r}")


def paginate_posts(posts: list[Post], posts_per_page: int) -> list[list[Post]]:
    """Split a list of posts into pages.

    Args:
        posts: List of posts to paginate
        posts_per_page: Number of posts per page

    Returns:
        List of pages, where each page is a list of posts
    """
    if not posts:
        return []
    if posts_per_page <= 0:
        return [posts]

    pages = []
    for i in range(0, len(posts), posts_per_page):
        pages.append(posts[i : i + posts_per_page])
    return pages


class SiteGenerator:
    """Generate a static blog site from markdown posts."""

    # Directory names for organizing content
    TAG_DIR = "tag"
    CATEGORY_DIR = "category"

    # Pagination constants - posts per page for each index type
    POSTS_PER_PAGE_INDEX = 10
    POSTS_PER_PAGE_TAG = 10
    POSTS_PER_PAGE_CATEGORY = 10
    POSTS_PER_PAGE_ARCHIVE = 10

    # Feed constants - posts per feed
    POSTS_PER_FEED = 20

    def __init__(self, site_config: SiteConfig) -> None:
        """Initialize the site generator.

        Args:
            site_config: Configuration for the site to be generated.  The
                [`content_dir`][blogmore.site_config.SiteConfig.content_dir] field must not be `None`.
        """
        if site_config.content_dir is None:
            raise ValueError(
                "site_config.content_dir must be provided for site generation"
            )
        self.site_config = site_config

        # Default to CDN URL; updated during generate() once socials are known
        self._fontawesome_css_url: str = FONTAWESOME_CDN_CSS_URL

        # Cache-busting token; set at the start of each generate() call so all
        # pages in one generation share the same token but successive generations
        # get a fresh one, forcing browsers to re-fetch updated stylesheets.
        self._cache_bust_token: str = ""

        self.parser = PostParser(site_url=site_config.site_url)
        self.renderer = TemplateRenderer(
            site_config.templates_dir,
            site_config.extra_stylesheets,
            site_config.site_url,
        )

        # Relative paths (forward-slash strings) of HTML files that were copied
        # verbatim from the extras directory.  Populated by _copy_extras() and
        # consumed by _generate_sitemap() to exclude those files from the sitemap.
        self._extras_html_paths: frozenset[str] = frozenset()

    @property
    def _content_dir(self) -> Path:
        """Return the content directory as a ``Path``, guaranteed non-``None``.

        ``__init__`` validates that ``site_config.content_dir`` is not ``None``,
        so this property is always safe to call on a constructed instance.

        Returns:
            The resolved content directory path.
        """
        assert self.site_config.content_dir is not None
        return self.site_config.content_dir

    def _detect_favicon(self) -> str | None:
        """Detect if a favicon file exists in the icons or extras directory.

        Checks for favicon files with common extensions in priority order.
        First checks the icons directory (for generated icons), then falls back
        to the extras directory (for manually provided icons).

        Returns:
            The favicon URL (relative to site root) if found, None otherwise
        """
        # First check icons directory (generated icons)
        icons_dir = self.site_config.output_dir / "icons"
        if icons_dir.exists():
            favicon_path = icons_dir / "favicon.ico"
            if favicon_path.is_file():
                return "/icons/favicon.ico"

        # Fall back to extras directory (existing behavior)
        extras_dir = self._content_dir / "extras"
        if not extras_dir.exists():
            return None

        # Common favicon extensions in priority order
        favicon_extensions = [".ico", ".png", ".svg", ".gif", ".jpg", ".jpeg"]

        # Check for favicon files
        for ext in favicon_extensions:
            favicon_path = extras_dir / f"favicon{ext}"
            if favicon_path.is_file():
                return f"/favicon{ext}"

        return None

    def _detect_generated_icons(self) -> bool:
        """Detect if generated platform icons exist in the icons directory.

        Returns:
            True if generated icons exist, False otherwise
        """
        icons_dir = self.site_config.output_dir / "icons"
        if not icons_dir.exists():
            return False

        # Check if the main Apple touch icon exists as an indicator
        apple_icon_path = icons_dir / "apple-touch-icon.png"
        return apple_icon_path.is_file()

    def _generate_icons(self) -> None:
        """Generate icons from a source image if present."""
        extras_dir = self._content_dir / "extras"

        # Look for a source icon (using configured name if provided)
        source_icon = detect_source_icon(extras_dir, self.site_config.icon_source)

        if source_icon:
            print(f"Found source icon: {source_icon.name}")
            print("Generating favicon and Apple touch icons...")

            # Generate to /icons subdirectory
            icons_output_dir = self.site_config.output_dir / "icons"
            generator = IconGenerator(source_icon, icons_output_dir)
            generated = generator.generate_all()

            if generated:
                print(f"Generated {len(generated)} icon file(s):")
                for icon_name in generated:
                    print(f"  - icons/{icon_name}")

                # Copy favicon.ico to the root for backward compatibility
                if favicon_ico := generated.get("favicon.ico"):
                    shutil.copy2(
                        favicon_ico, self.site_config.output_dir / "favicon.ico"
                    )
                    print("  - favicon.ico (root copy for backward compatibility)")
            else:
                print("Warning: No icons were generated")

    def _with_cache_bust(self, url: str) -> str:
        """Return a URL with a cache-busting query parameter appended.

        External URLs (i.e. those that start with ``http://`` or ``https://``)
        are returned unchanged.  Local URLs (starting with ``/``) have
        ``?v=<token>`` appended so that browsers re-fetch them when the site is
        regenerated.  If no cache-busting token has been set (e.g. before
        :meth:`generate` is called) the URL is returned as-is.

        Args:
            url: The URL to process.

        Returns:
            The URL with a cache-busting query parameter appended, or the
            original URL if it is external or the token has not been set.
        """
        if (
            not self._cache_bust_token
            or not url
            or url.startswith(("http://", "https://"))
        ):
            return url
        return f"{url}?v={self._cache_bust_token}"

    def _get_configured_url(self, path_field_name: str) -> str:
        """Return the URL path for a configured page, derived from a config field.

        Strips any leading slash from the config value, prepends a fresh
        ``/``, and optionally applies [`make_url_clean`][blogmore.clean_url.make_url_clean]
        when ``clean_urls`` is enabled.

        Args:
            path_field_name: The name of the [`SiteConfig`][blogmore.site_config.SiteConfig]
                attribute that holds the page path (e.g. ``"search_path"``).

        Returns:
            The URL path for the configured page, always starting with ``/``.
        """
        path: str = getattr(self.site_config, path_field_name)
        url = "/" + path.lstrip("/")
        if self.site_config.clean_urls:
            url = make_url_clean(url)
        return url

    def _get_search_url(self) -> str:
        """Return the URL path for the configured search page.

        Returns:
            The URL path for the search page, always starting with ``/``.
        """
        return self._get_configured_url("search_path")

    def _get_archive_url(self) -> str:
        """Return the URL path for the configured archive page.

        Returns:
            The URL path for the archive page, always starting with ``/``.
        """
        return self._get_configured_url("archive_path")

    def _get_tags_url(self) -> str:
        """Return the URL path for the configured tags overview page.

        Returns:
            The URL path for the tags page, always starting with ``/``.
        """
        return self._get_configured_url("tags_path")

    def _get_categories_url(self) -> str:
        """Return the URL path for the configured categories overview page.

        Returns:
            The URL path for the categories page, always starting with ``/``.
        """
        return self._get_configured_url("categories_path")

    def _get_stats_url(self) -> str:
        """Return the URL path for the configured statistics page.

        Returns:
            The URL path for the statistics page, always starting with ``/``.
        """
        return self._get_configured_url("stats_path")

    def _get_calendar_url(self) -> str:
        """Return the URL path for the configured calendar page.

        Returns:
            The URL path for the calendar page, always starting with ``/``.
        """
        return self._get_configured_url("calendar_path")

    def _get_graph_url(self) -> str:
        """Return the URL path for the configured graph page.

        Returns:
            The URL path for the graph page, always starting with ``/``.
        """
        return self._get_configured_url("graph_path")

    def _get_asset_url(
        self,
        regular: str,
        minify: bool,
        *,
        cache_bust: bool = True,
    ) -> str:
        """Build the ``/static/`` URL for one asset, choosing the minified variant when requested.

        When *minify* is ``True`` the minified filename is derived from
        *regular* via [`minified_filename`][blogmore.generator.minified_filename].

        Args:
            regular: Filename for the non-minified asset (e.g. ``"style.css"``).
            minify: When ``True``, the minified filename is used.
            cache_bust: When ``True`` (the default), the URL is passed through
                [`_with_cache_bust`][blogmore.generator.SiteGenerator._with_cache_bust]
                so that browsers re-fetch the file after each build.

        Returns:
            The ``/static/<filename>`` URL, with an optional ``?v=<token>``
            cache-busting query parameter.
        """
        name = minified_filename(regular) if minify else regular
        url = f"/static/{name}"
        return self._with_cache_bust(url) if cache_bust else url

    def _get_global_context(self) -> dict[str, Any]:
        """Get the global context available to all templates."""
        page1_suffix = resolve_pagination_page_path(self.site_config.page_1_path, 1)
        if self.site_config.clean_urls:
            page1_suffix = make_url_clean(page1_suffix)
        context = {
            "site_title": self.site_config.site_title,
            "site_subtitle": self.site_config.site_subtitle,
            "site_description": self.site_config.site_description,
            "site_keywords": self.site_config.site_keywords,
            "site_url": self.site_config.site_url,
            "tag_dir": self.TAG_DIR,
            "category_dir": self.CATEGORY_DIR,
            "favicon_url": self._detect_favicon(),
            "has_platform_icons": self._detect_generated_icons(),
            "blogmore_version": __version__,
            "with_search": self.site_config.with_search,
            "search_url": self._get_search_url(),
            "archive_url": self._get_archive_url(),
            "tags_url": self._get_tags_url(),
            "categories_url": self._get_categories_url(),
            "with_stats": self.site_config.with_stats,
            "stats_url": self._get_stats_url(),
            "with_calendar": self.site_config.with_calendar,
            "forward_calendar": self.site_config.forward_calendar,
            "calendar_url": self._get_calendar_url(),
            "with_graph": self.site_config.with_graph,
            "graph_url": self._get_graph_url(),
            "with_read_time": self.site_config.with_read_time,
            "with_backlinks": self.site_config.with_backlinks,
            "backlinks_title": self.site_config.backlinks_title,
            "with_advert": self.site_config.with_advert,
            "default_author": self.site_config.default_author,
            "extra_head_tags": self.site_config.head,
            "fontawesome_css_url": self._with_cache_bust(self._fontawesome_css_url),
            "fontawesome_woff2_url": FONTAWESOME_CDN_BRANDS_WOFF2_URL,
            "styles_css_url": self._get_asset_url(
                CSS_FILENAME, self.site_config.minify_css
            ),
            "search_css_url": self._get_asset_url(
                SEARCH_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "stats_css_url": self._get_asset_url(
                STATS_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "archive_css_url": self._get_asset_url(
                ARCHIVE_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "tag_cloud_css_url": self._get_asset_url(
                TAG_CLOUD_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "calendar_css_url": self._get_asset_url(
                CALENDAR_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "graph_css_url": self._get_asset_url(
                GRAPH_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "code_css_url": self._get_asset_url(
                CODE_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "theme_js_url": self._get_asset_url(
                THEME_JS_FILENAME,
                self.site_config.minify_js,
                cache_bust=False,
            ),
            "search_js_url": self._get_asset_url(
                SEARCH_JS_FILENAME,
                self.site_config.minify_js,
                cache_bust=False,
            ),
            "codeblocks_js_url": self._get_asset_url(
                CODEBLOCKS_JS_FILENAME,
                self.site_config.minify_js,
                cache_bust=False,
            ),
            "graph_js_url": self._get_asset_url(
                GRAPH_JS_FILENAME,
                self.site_config.minify_js,
                cache_bust=False,
            ),
            "pagination_page1_suffix": page1_suffix,
        }
        # Merge sidebar config into context
        context.update(self.site_config.sidebar_config)
        return context

    def _get_pagination_url(self, base_url: str, page_num: int) -> str:
        """Compute the URL for a given pagination page.

        Joins *base_url* with the path resolved from the configured
        ``page_1_path`` or ``page_n_path`` template.  When ``clean_urls``
        is enabled and the resolved URL ends in ``index.html``, that
        suffix is stripped.

        Args:
            base_url: The URL prefix for the paginated section (e.g.
                ``/2024`` for a year archive).  May be an empty string
                for the main index.
            page_num: The 1-based page number.

        Returns:
            The fully-formed URL for the requested page.
        """
        if page_num == 1:
            relative = resolve_pagination_page_path(self.site_config.page_1_path, 1)
        else:
            relative = resolve_pagination_page_path(
                self.site_config.page_n_path, page_num
            )
        url = f"{base_url}/{relative}"
        # Collapse any double slashes introduced when base_url is empty.
        url = url.replace("//", "/")
        if self.site_config.clean_urls:
            url = make_url_clean(url)
        return url

    def _build_pagination_page_urls(self, base_url: str, total_pages: int) -> list[str]:
        """Build the full list of page URLs for a paginated section.

        Args:
            base_url: The URL prefix for the paginated section.
            total_pages: The total number of pages.

        Returns:
            A list of URLs, one per page, ordered from page 1 to
            *total_pages*.
        """
        return [
            self._get_pagination_url(base_url, page_num)
            for page_num in range(1, total_pages + 1)
        ]

    def _get_pagination_output_path(self, base_dir: Path, page_num: int) -> Path:
        """Compute the output file path for a given pagination page.

        Resolves the appropriate path template from the site configuration
        and joins it onto *base_dir*.  Any required parent directories are
        created automatically.

        Args:
            base_dir: The base directory for this paginated section.
            page_num: The 1-based page number.

        Returns:
            The absolute output file path for the given page.
        """
        if page_num == 1:
            relative = resolve_pagination_page_path(self.site_config.page_1_path, 1)
        else:
            relative = resolve_pagination_page_path(
                self.site_config.page_n_path, page_num
            )
        output_path = base_dir / relative
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    @staticmethod
    def _pagination_prev_next(
        page_num: int,
        page_urls: list[str],
    ) -> tuple[str | None, str | None]:
        """Return the previous and next page URLs for a paginated page.

        Args:
            page_num: The current page number (1-based).
            page_urls: Ordered list of all page URLs (index 0 = page 1).

        Returns:
            A tuple of ``(prev_url, next_url)`` where each element is
            ``None`` when there is no adjacent page.
        """
        prev_url: str | None = page_urls[page_num - 2] if page_num > 1 else None
        next_url: str | None = (
            page_urls[page_num] if page_num < len(page_urls) else None
        )
        return prev_url, next_url

    def _canonical_url_for_path(self, output_path: Path) -> str:
        """Compute the fully-qualified canonical URL for a given output file path.

        When ``clean_urls`` is enabled, index filenames (e.g. ``index.html``)
        are stripped from the URL so the canonical URL ends with a trailing
        slash instead, matching the URLs advertised in the sitemap and
        elsewhere.

        Args:
            output_path: Absolute path to the output file within the output directory.

        Returns:
            The fully-qualified canonical URL for the given file.
        """
        relative = output_path.relative_to(self.site_config.output_dir)
        url = f"/{relative.as_posix()}"
        if self.site_config.clean_urls:
            url = make_url_clean(url)
        return f"{self.site_config.site_url}{url}"

    def generate(self) -> None:
        """Generate the complete static site."""
        content_dir = self._content_dir

        # Mint a fresh cache-busting token for this generation.  All pages
        # rendered during this run will share the same token so that once a
        # visitor downloads a stylesheet it stays cached for the lifetime of
        # this deployment.  A new generation produces a new token, which forces
        # browsers to re-fetch any updated stylesheets.
        self._cache_bust_token = str(int(time.time()))

        # Apply cache-busting to any local extra stylesheets so they are also
        # re-fetched after a new site generation.  Always reassign the list so
        # that removing extra_stylesheets from the config correctly clears the
        # renderer's list on the next build.
        extra_stylesheets = self.site_config.extra_stylesheets or []
        self.renderer.extra_stylesheets = [
            self._with_cache_bust(url) for url in extra_stylesheets
        ]

        # Clean output directory if requested
        if self.site_config.clean_first and self.site_config.output_dir.exists():
            print(f"Removing output directory: {self.site_config.output_dir}")
            try:
                shutil.rmtree(self.site_config.output_dir)
            except OSError:
                # On Linux with concurrent operations the directory may not be
                # fully empty yet.  Wait briefly and retry once before falling
                # back to a best-effort removal.
                time.sleep(0.1)
                try:
                    shutil.rmtree(self.site_config.output_dir)
                except OSError:
                    shutil.rmtree(self.site_config.output_dir, ignore_errors=True)
                    print(
                        "Warning: Some files could not be removed from output directory"
                    )

        # Parse all pages from the pages subdirectory (must be done first so we
        # can exclude them when scanning for posts)
        pages_dir = content_dir / "pages"
        pages = self.parser.parse_pages_directory(pages_dir)
        page_404 = self.parser.parse_404_page(pages_dir)

        # Parse all posts, excluding the pages subdirectory
        print(f"Parsing posts from {content_dir}...")
        posts = self.parser.parse_directory(
            content_dir,
            include_drafts=self.site_config.include_drafts,
            exclude_dirs=[pages_dir],
        )
        print(f"Found {len(posts)} posts")

        # Apply configured reading-speed to every post so that reading_time
        # reflects the user's read_time_wpm setting.
        for post in posts:
            post.words_per_minute = self.site_config.read_time_wpm

        # Apply default author to posts that don't have one
        if self.site_config.default_author:
            for post in posts:
                if post.metadata is not None and "author" not in post.metadata:
                    post.metadata["author"] = self.site_config.default_author
        if pages:
            print(f"Found {len(pages)} pages")

        # Resolve the list of pages to display in the sidebar.  This may be a
        # filtered/reordered subset when the user has configured ``pages:`` in
        # the config file; otherwise it equals ``pages`` unchanged.
        sidebar_pages = self._resolve_sidebar_pages(pages)

        # Create output directory
        self.site_config.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate icons from source image BEFORE generating HTML pages
        # so that the has_apple_touch_icons flag is correctly set
        self._generate_icons()

        # Prepare the FontAwesome CSS URL (and content if optimisation succeeds).
        # Must be done before any HTML is rendered so the correct URL is embedded
        # in every page, but the CSS file itself is written after _copy_static_assets()
        # so it is not overwritten by that step.
        fontawesome_css_content = self._prepare_fontawesome_css()

        # Resolve page output paths before generating any HTML so that
        # page.url_path is set correctly for all pages (including when they
        # appear in the sidebar of individual post pages).
        page_output_paths = self._resolve_page_output_paths(pages)

        # Generate individual post pages
        print("Generating post pages...")
        post_output_paths = self._resolve_post_output_paths(posts)

        # Build the backlink map only when the feature is enabled.  This
        # must happen after _resolve_post_output_paths() so that every
        # post.url_path is set to its final value before link matching.
        backlinks_map: dict[str, list[Backlink]] = {}
        if self.site_config.with_backlinks:
            print("Building backlink map...")
            backlinks_map = build_backlink_map(
                posts,
                site_url=self.site_config.site_url,
            )

        generated_paths: set[str] = set()
        for post in posts:
            output_path = post_output_paths[id(post)]
            path_key = str(output_path)
            if path_key in generated_paths:
                # A newer post has already claimed this path; skip this older one.
                continue
            generated_paths.add(path_key)
            self._generate_post_page(
                post, posts, sidebar_pages, output_path, backlinks_map
            )

        # Generate static pages
        if pages:
            print("Generating static pages...")
            for page in pages:
                self._generate_page(page, sidebar_pages, page_output_paths[id(page)])

        # Generate custom 404 page if present
        if page_404 is not None:
            print("Generating custom 404 page...")
            self._generate_404_page(page_404, sidebar_pages)

        # Generate index page
        print("Generating index page...")
        self._generate_index_page(posts, sidebar_pages)

        # Generate archive page
        print("Generating archive page...")
        self._generate_archive_page(posts, sidebar_pages)

        # Generate date-based archive pages
        print("Generating date-based archive pages...")
        self._generate_date_archives(posts, sidebar_pages)

        # Generate tag pages
        print("Generating tag pages...")
        self._generate_tag_pages(posts, sidebar_pages)

        # Generate tags overview page
        print("Generating tags overview page...")
        self._generate_tags_page(posts, sidebar_pages)

        # Generate category pages
        print("Generating category pages...")
        self._generate_category_pages(posts, sidebar_pages)

        # Generate categories overview page
        print("Generating categories overview page...")
        self._generate_categories_page(posts, sidebar_pages)

        # Generate feeds
        print("Generating RSS and Atom feeds...")
        self._generate_feeds(posts)

        # Generate search index and search page (only when enabled)
        if self.site_config.with_search:
            print("Generating search index and search page...")
            self._generate_search_index(posts)
            self._generate_search_page(sidebar_pages)
        else:
            # Remove any stale search files left over from a previous build
            # that had search enabled.
            self._remove_stale_search_files()

        # Generate statistics page (only when enabled)
        if self.site_config.with_stats:
            print("Generating blog statistics page...")
            self._generate_stats_page(
                posts,
                sidebar_pages,
                backlinks_map if self.site_config.with_backlinks else None,
            )

        # Generate calendar page (only when enabled)
        if self.site_config.with_calendar:
            print("Generating calendar page...")
            self._generate_calendar_page(posts, sidebar_pages)

        # Generate graph page (only when enabled)
        if self.site_config.with_graph:
            print("Generating graph page...")
            self._generate_graph_page(posts, sidebar_pages)

        # Copy static assets if they exist
        self._copy_static_assets()

        # Write the optimised FontAwesome CSS file after static assets have been
        # copied so it is not overwritten by _copy_static_assets().
        if fontawesome_css_content is not None:
            self._write_fontawesome_css(fontawesome_css_content)

        # Copy extra files from extras directory
        self._copy_extras()

        # Generate XML sitemap (only when enabled)
        if self.site_config.with_sitemap:
            print("Generating XML sitemap...")
            self._generate_sitemap()

        print(f"Site generation complete! Output: {self.site_config.output_dir}")

    def _prepare_fontawesome_css(self) -> str | None:
        """Determine the FontAwesome CSS URL and optionally build optimised CSS.

        Extracts the social icon names from the sidebar configuration and
        attempts to fetch the FontAwesome metadata from GitHub to build a
        minimal CSS file.  Updates ``self._fontawesome_css_url`` with the URL
        that every rendered page will reference.

        Returns:
            The CSS content string to write to disk if optimisation succeeded,
            or ``None`` if no social icons are configured or if the metadata
            fetch failed (in the latter case the full CDN URL is used instead).
        """
        socials: list[Any] = self.site_config.sidebar_config.get("socials", [])
        if not socials:
            # No social icons — no FontAwesome CSS needed at all.
            self._fontawesome_css_url = ""
            return None

        icon_names = [
            str(social["site"])
            for social in socials
            if isinstance(social, dict) and "site" in social
        ]
        optimizer = FontAwesomeOptimizer(icon_names)

        try:
            metadata = optimizer.fetch_icon_metadata()
        except (urllib.error.URLError, ValueError, OSError) as error:
            print(f"Warning: Could not fetch FontAwesome metadata: {error}")
            print("Falling back to full FontAwesome CDN stylesheet.")
            self._fontawesome_css_url = FONTAWESOME_CDN_CSS_URL
            return None

        print("Optimizing FontAwesome CSS...")
        self._fontawesome_css_url = (
            FONTAWESOME_LOCAL_CSS_MINIFIED_PATH
            if self.site_config.minify_css
            else FONTAWESOME_LOCAL_CSS_PATH
        )
        return optimizer.build_css(metadata)

    def _write_fontawesome_css(self, css_content: str) -> None:
        """Write the optimised FontAwesome CSS file to the static directory.

        Must be called *after* :meth:`_copy_static_assets` so the file is not
        overwritten.  When ``minify_css`` is enabled the content is minified
        and written as ``fontawesome.min.css``; otherwise it is written as
        ``fontawesome.css``.

        Args:
            css_content: CSS text to write.
        """
        static_dir = self.site_config.output_dir / "static"
        static_dir.mkdir(parents=True, exist_ok=True)
        if self.site_config.minify_css:
            minified = rcssmin.cssmin(css_content)
            fa_min = minified_filename("fontawesome.css")
            css_path = static_dir / fa_min
            css_path.write_text(minified, encoding="utf-8")
            print(f"Generated minified FontAwesome CSS as {fa_min}")
        else:
            css_path = static_dir / "fontawesome.css"
            css_path.write_text(css_content, encoding="utf-8")
            print("Generated optimized FontAwesome CSS")

    def _write_html(self, output_path: Path, html: str) -> None:
        """Write an HTML string to a file, minifying it when configured to do so.

        When ``minify_html`` is enabled the HTML content is passed through the
        ``minify-html`` library before being written.  The output file name is
        not changed — only the content is minified.

        Args:
            output_path: Destination file path.
            html: HTML content to write.
        """
        if self.site_config.minify_html:
            html = minify_html.minify(html, minify_js=False, minify_css=False)
        output_path.write_text(html, encoding="utf-8")

    def _get_asset_source(self, filename: str) -> str | None:
        """Read the text content of a static asset, preferring custom over bundled.

        Looks first in the custom templates directory (``templates_dir/static/``)
        when one is configured, then falls back to the package's bundled templates.
        Returns ``None`` and emits a warning if the asset cannot be found.

        Args:
            filename: The asset filename to look up (e.g. ``"style.css"``).

        Returns:
            The text content of the asset, or ``None`` if it could not be read.
        """
        if self.site_config.templates_dir is not None:
            custom_path = self.site_config.templates_dir / "static" / filename
            if custom_path.is_file():
                return custom_path.read_text(encoding="utf-8")

        try:
            bundled = files("blogmore").joinpath("templates", "static", filename)
            return bundled.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Warning: Could not read bundled {filename} for minification: {e}")
            return None

    def _minify_one_css(
        self,
        output_static: Path,
        source_filename: str,
    ) -> None:
        """Read one source CSS file, minify it, and write the minified output.

        The source CSS is read from the custom templates directory (if
        available) or from the bundled templates.  The minified output filename
        is derived from *source_filename* via
        [`minified_filename`][blogmore.generator.minified_filename] and written
        to ``output_static/<minified_name>``.

        Args:
            output_static: Path to the output static directory.
            source_filename: Source CSS filename (e.g. ``style.css``).
        """
        css_source = self._get_asset_source(source_filename)
        if css_source is None:
            return

        minified_name = minified_filename(source_filename)
        minified = rcssmin.cssmin(css_source)
        output_path = output_static / minified_name
        output_path.write_text(minified, encoding="utf-8")
        print(f"Generated minified CSS as {minified_name}")

    def _write_minified_css(self, output_static: Path) -> None:
        """Minify all CSS files and write them to the output static directory.

        Minifies the main stylesheet (``style.css`` → ``style.min.css``) and
        each of the page-specific stylesheets (``search.css``, ``stats.css``,
        ``archive.css``, ``tag-cloud.css``).  The source CSS for each file is
        read from the custom templates directory (if configured) or from the
        bundled templates.

        Args:
            output_static: Path to the output static directory.
        """
        self._minify_one_css(output_static, CSS_FILENAME)
        for source_filename in _PAGE_SPECIFIC_CSS:
            self._minify_one_css(output_static, source_filename)

    def _write_code_css(self, output_static: Path) -> None:
        """Generate and write the code syntax highlighting CSS file.

        Builds a ``code.css`` (or ``code.min.css`` when ``minify_css`` is
        enabled) from the Pygments styles configured in ``light_mode_code_style``
        and ``dark_mode_code_style``.  The file is always regenerated from the
        configured styles, even when the default styles are in use, so that the
        output is self-contained and does not depend on any hardcoded CSS rules
        in the main stylesheet.

        Args:
            output_static: Path to the output static directory.
        """
        css_content = build_code_css(
            self.site_config.light_mode_code_style,
            self.site_config.dark_mode_code_style,
        )
        if self.site_config.minify_css:
            minified = rcssmin.cssmin(css_content)
            code_css_min = minified_filename(CODE_CSS_FILENAME)
            output_path = output_static / code_css_min
            output_path.write_text(minified, encoding="utf-8")
            print(f"Generated minified code CSS as {code_css_min}")
        else:
            output_path = output_static / CODE_CSS_FILENAME
            output_path.write_text(css_content, encoding="utf-8")
            print(f"Generated code CSS as {CODE_CSS_FILENAME}")

    def _write_minified_js(self, output_static: Path, js_filename: str) -> None:
        """Read a source JavaScript file, minify it, and write it with the minified name.

        The source JS is read from the custom templates directory (if
        available) or from the bundled templates.  The minified output filename
        is derived from *js_filename* via
        [`minified_filename`][blogmore.generator.minified_filename] and written
        to ``output_static/<minified_name>``.

        Args:
            output_static: Path to the output static directory.
            js_filename: The original JavaScript filename (e.g. ``theme.js``).
        """
        js_source = self._get_asset_source(js_filename)
        if js_source is None:
            return

        js_min = minified_filename(js_filename)
        minified = rjsmin.jsmin(js_source)
        output_path = output_static / js_min
        output_path.write_text(minified, encoding="utf-8")
        print(f"Generated minified JS as {js_min}")

    def _resolve_post_output_paths(self, posts: list[Post]) -> dict[int, Path]:
        """Resolve the output path for every post and detect path clashes.

        For each post the method:

        1. Computes the absolute output file path using the configured
           ``post_path`` template.
        2. Sets ``post.url_path`` so that templates and feeds always use the
           correct URL regardless of the configured format.
        3. Groups posts by output path and emits a prominent ``WARNING`` for
           any group that contains more than one post (i.e. a path clash).
           The *newest* post (first in the already-sorted list) wins; older
           posts that share the same path will be skipped during generation.

        Args:
            posts: All posts sorted by date, newest first.

        Returns:
            Mapping from ``id(post)`` to the post's resolved output path.
        """
        post_output_paths: dict[int, Path] = {}
        # Preserve insertion order so we can identify the winner easily.
        path_to_post_ids: dict[str, list[int]] = defaultdict(list)
        post_by_id: dict[int, Post] = {id(post): post for post in posts}

        for post in posts:
            output_path = compute_output_path(
                self.site_config.output_dir, post, self.site_config.post_path
            )
            post_output_paths[id(post)] = output_path

            # Set the post's URL so all templates/feeds reflect the configured scheme.
            relative = output_path.relative_to(self.site_config.output_dir)
            url_path = "/" + relative.as_posix()

            # Apply clean URL transformation: strip index filenames (e.g.
            # "index.html") from paths so the URL ends with a trailing slash.
            if self.site_config.clean_urls:
                url_path = make_url_clean(url_path)

            post.url_path = url_path

            path_to_post_ids[str(output_path)].append(id(post))

        # Detect and warn about path clashes.
        for path_str, clashing_ids in path_to_post_ids.items():
            if len(clashing_ids) > 1:
                clashing_posts = [post_by_id[pid] for pid in clashing_ids]
                winner = clashing_posts[0]  # newest (list is sorted newest-first)
                losers = clashing_posts[1:]
                print(
                    "\nWARNING: Post path clash detected!  "
                    "Multiple posts would be written to the same output file."
                )
                print(f"  Output path : {path_str}")
                print(f"  Winner (newest) : '{winner.title}'")
                for loser in losers:
                    print(f"  Ignored (older): '{loser.title}'")
                print()

        return post_output_paths

    def _generate_post_page(
        self,
        post: Post,
        all_posts: list[Post],
        pages: list[Page],
        output_path: Path,
        backlinks_map: "dict[str, list[Backlink]] | None" = None,
    ) -> None:
        """Generate a single post page.

        Args:
            post: The post to generate a page for.
            all_posts: All posts (sorted newest first), used for prev/next navigation.
            pages: All static pages, passed to the template context.
            output_path: The pre-resolved absolute output file path for this post.
            backlinks_map: Optional mapping from post URL to list of Backlink
                objects, built when ``with_backlinks`` is enabled.  When
                ``None`` or when the post URL has no entry, an empty list is
                used so the template always receives a ``backlinks`` variable.
        """
        context = self._get_global_context()
        context["all_posts"] = all_posts
        context["pages"] = pages

        # Attach the backlinks list for this post to the template context.
        context["backlinks"] = backlinks_map.get(post.url, []) if backlinks_map else []

        # Compute the comment invitation mailto URL for this post.
        invite_email = get_invite_email_for_post(
            post,
            self.site_config.invite_comments,
            self.site_config.invite_comments_to,
        )
        context["invite_comments_mailto"] = (
            build_mailto_url(invite_email, post.title) if invite_email else None
        )

        # Find previous and next posts in chronological order
        # all_posts is already sorted by date (newest first)
        try:
            current_index = all_posts.index(post)
            # Previous post is older (higher index)
            context["prev_post"] = (
                all_posts[current_index + 1]
                if current_index + 1 < len(all_posts)
                else None
            )
            # Next post is newer (lower index)
            context["next_post"] = (
                all_posts[current_index - 1] if current_index > 0 else None
            )
        except ValueError:
            # Post not in list, no navigation
            context["prev_post"] = None
            context["next_post"] = None

        output_path.parent.mkdir(parents=True, exist_ok=True)
        # When clean URLs are enabled, post.url already has index.html stripped;
        # use it directly so the canonical URL matches what we advertise everywhere.
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{post.url}"
                if self.site_config.site_url
                else post.url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)
        html = self.renderer.render_post(post, **context)
        self._write_html(output_path, html)

    def _resolve_sidebar_pages(self, pages: list[Page]) -> list[Page]:
        """Resolve which pages appear in the sidebar and in what order.

        When ``site_config.sidebar_pages`` is ``None`` or empty every page in
        ``pages`` is returned unchanged (the default behaviour).  When a list
        of slugs is provided, only pages whose slug appears in that list are
        returned, in the order defined by the list.  Slugs that do not match
        any existing page are silently ignored.

        Args:
            pages: All parsed static pages.

        Returns:
            The ordered list of pages to display in the sidebar.
        """
        if not self.site_config.sidebar_pages:
            return pages

        pages_by_slug: dict[str, Page] = {page.slug: page for page in pages}
        return [
            pages_by_slug[slug]
            for slug in self.site_config.sidebar_pages
            if slug in pages_by_slug
        ]

    def _resolve_page_output_paths(self, pages: list[Page]) -> dict[int, Path]:
        """Resolve the output path for every static page.

        For each page the method:

        1. Computes the absolute output file path using the configured
           ``page_path`` template.
        2. Sets ``page.url_path`` so that templates always use the correct URL
           regardless of the configured format.

        Args:
            pages: All static pages to resolve paths for.

        Returns:
            Mapping from ``id(page)`` to the page's resolved output path.
        """
        page_output_paths: dict[int, Path] = {}

        for page in pages:
            output_path = compute_page_output_path(
                self.site_config.output_dir, page, self.site_config.page_path
            )
            page_output_paths[id(page)] = output_path

            # Set the page's URL so all templates reflect the configured scheme.
            relative = output_path.relative_to(self.site_config.output_dir)
            url_path = "/" + relative.as_posix()

            # Apply clean URL transformation: strip index filenames (e.g.
            # "index.html") from paths so the URL ends with a trailing slash.
            if self.site_config.clean_urls:
                url_path = make_url_clean(url_path)

            page.url_path = url_path

        return page_output_paths

    def _generate_page(self, page: Page, pages: list[Page], output_path: Path) -> None:
        """Generate a single static page.

        Args:
            page: The static page to generate.
            pages: All static pages, passed to the template context.
            output_path: The pre-resolved absolute output file path for this page.
        """
        context = self._get_global_context()
        context["pages"] = pages

        output_path.parent.mkdir(parents=True, exist_ok=True)

        context["canonical_url"] = self._canonical_url_for_path(output_path)

        html = self.renderer.render_page(page, **context)

        self._write_html(output_path, html)

    def _generate_404_page(self, page: Page, pages: list[Page]) -> None:
        """Generate the custom 404 page in the root of the output directory."""
        context = self._get_global_context()
        context["pages"] = pages
        output_path = self.site_config.output_dir / CUSTOM_404_HTML
        context["canonical_url"] = self._canonical_url_for_path(output_path)

        html = self.renderer.render_page(page, **context)

        self._write_html(output_path, html)

    def _generate_index_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the main index page with pagination.

        Page 1 of the main index is always written to ``index.html`` at the
        output root, regardless of the ``page_1_path`` configuration.  This
        guarantees that the site always has a root ``index.html``.  The
        ``page_1_path`` setting still applies to all other paginated sections
        (archives, tags, categories).  Pages 2 and above of the main index
        use ``page_n_path`` as configured.
        """
        context = self._get_global_context()
        context["pages"] = pages

        # Paginate posts
        paginated_posts = paginate_posts(posts, self.POSTS_PER_PAGE_INDEX)
        if not paginated_posts:
            paginated_posts = [[]]  # Empty page if no posts

        total_pages = len(paginated_posts)

        # Page 1 of the main index is always /index.html (with clean_urls: /)
        # regardless of page_1_path, so that the site root is never displaced.
        page1_url: str = "/index.html"
        if self.site_config.clean_urls:
            page1_url = make_url_clean(page1_url)
        page_urls = [page1_url] + [
            self._get_pagination_url("", page_num)
            for page_num in range(2, total_pages + 1)
        ]

        # Generate each page
        for page_num, page_posts in enumerate(paginated_posts, start=1):
            if page_num == 1:
                output_path = self.site_config.output_dir / "index.html"
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = self._get_pagination_output_path(
                    self.site_config.output_dir, page_num
                )
            context["canonical_url"] = self._canonical_url_for_path(output_path)
            prev_url, next_url = self._pagination_prev_next(page_num, page_urls)
            context["prev_page_url"] = prev_url
            context["next_page_url"] = next_url
            context["pagination_page_urls"] = page_urls
            html = self.renderer.render_index(
                page_posts, page=page_num, total_pages=total_pages, **context
            )

            self._write_html(output_path, html)

    def _generate_archive_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the archive page."""
        context = self._get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.archive_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        archive_url = self._get_archive_url()
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{archive_url}"
                if self.site_config.site_url
                else archive_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)
        html = self.renderer.render_archive(
            posts, page=1, total_pages=1, base_path="/archive", **context
        )
        self._write_html(output_path, html)

    def _generate_paginated_listing(
        self,
        post_list: list[Post],
        base_url: str,
        output_dir: Path,
        posts_per_page: int,
        context: dict[str, Any],
        render_func: Callable[[list[Post], int, int], str],
    ) -> None:
        """Paginate *post_list* and write one HTML file per page.

        Handles all the boilerplate common to date-archive, tag, and category
        listing pages: paginating the posts, building the full list of page
        URLs, and iterating through pages to update the shared *context* dict
        (canonical URL, prev/next links, pagination URL list) before delegating
        rendering to *render_func*.

        Args:
            post_list: The posts to display, already in the desired order.
            base_url: The URL prefix for the section (e.g. ``"/tag/python"``).
            output_dir: The directory into which page files are written.
            posts_per_page: Maximum number of posts per page.
            context: The shared template context dict, mutated in-place for
                each page (``canonical_url``, ``prev_page_url``,
                ``next_page_url``, ``pagination_page_urls``).
            render_func: Callable with signature
                ``(page_posts, page_num, total_pages) -> str`` that produces the
                HTML for one page.  Any page-specific extra arguments (e.g.
                archive title, tag name) should be captured in a closure.
        """
        paginated_posts = paginate_posts(post_list, posts_per_page)
        total_pages = len(paginated_posts)
        page_urls = self._build_pagination_page_urls(base_url, total_pages)

        for page_num, page_posts in enumerate(paginated_posts, start=1):
            output_path = self._get_pagination_output_path(output_dir, page_num)
            context["canonical_url"] = self._canonical_url_for_path(output_path)
            prev_url, next_url = self._pagination_prev_next(page_num, page_urls)
            context["prev_page_url"] = prev_url
            context["next_page_url"] = next_url
            context["pagination_page_urls"] = page_urls
            html = render_func(page_posts, page_num, total_pages)
            self._write_html(output_path, html)

    def _generate_date_archives(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate date-based archive pages (year, month, day) with pagination."""
        # Group posts by year, month, and day
        posts_by_year: dict[int, list[Post]] = defaultdict(list)
        posts_by_month: dict[tuple[int, int], list[Post]] = defaultdict(list)
        posts_by_day: dict[tuple[int, int, int], list[Post]] = defaultdict(list)

        for post in posts:
            if post.date:
                year = post.date.year
                month = post.date.month
                day = post.date.day

                posts_by_year[year].append(post)
                posts_by_month[(year, month)].append(post)
                posts_by_day[(year, month, day)].append(post)

        context = self._get_global_context()
        context["pages"] = pages

        # Generate year archives with pagination
        for year, year_posts in posts_by_year.items():
            year_dir = self.site_config.output_dir / str(year)
            year_dir.mkdir(parents=True, exist_ok=True)
            base_path = f"/{year}"

            def _render_year(
                page_posts: list[Post],
                page_num: int,
                total_pages: int,
                _year: int = year,
                _base: str = base_path,
            ) -> str:
                return self.renderer.render_archive(
                    page_posts,
                    archive_title=f"Posts from {_year}",
                    page=page_num,
                    total_pages=total_pages,
                    base_path=_base,
                    **context,
                )

            self._generate_paginated_listing(
                year_posts,
                base_url=base_path,
                output_dir=year_dir,
                posts_per_page=self.POSTS_PER_PAGE_ARCHIVE,
                context=context,
                render_func=_render_year,
            )

        # Generate month archives with pagination
        for (year, month), month_posts in posts_by_month.items():
            month_dir = self.site_config.output_dir / str(year) / f"{month:02d}"
            month_dir.mkdir(parents=True, exist_ok=True)
            month_name = dt.datetime(year, month, 1).strftime("%B %Y")
            base_path = f"/{year}/{month:02d}"

            def _render_month(
                page_posts: list[Post],
                page_num: int,
                total_pages: int,
                _name: str = month_name,
                _base: str = base_path,
            ) -> str:
                return self.renderer.render_archive(
                    page_posts,
                    archive_title=f"Posts from {_name}",
                    page=page_num,
                    total_pages=total_pages,
                    base_path=_base,
                    **context,
                )

            self._generate_paginated_listing(
                month_posts,
                base_url=base_path,
                output_dir=month_dir,
                posts_per_page=self.POSTS_PER_PAGE_ARCHIVE,
                context=context,
                render_func=_render_month,
            )

        # Generate day archives with pagination
        for (year, month, day), day_posts in posts_by_day.items():
            day_dir = (
                self.site_config.output_dir / str(year) / f"{month:02d}" / f"{day:02d}"
            )
            day_dir.mkdir(parents=True, exist_ok=True)
            date_str = dt.datetime(year, month, day).strftime("%B %d, %Y")
            base_path = f"/{year}/{month:02d}/{day:02d}"

            def _render_day(
                page_posts: list[Post],
                page_num: int,
                total_pages: int,
                _date: str = date_str,
                _base: str = base_path,
            ) -> str:
                return self.renderer.render_archive(
                    page_posts,
                    archive_title=f"Posts from {_date}",
                    page=page_num,
                    total_pages=total_pages,
                    base_path=_base,
                    **context,
                )

            self._generate_paginated_listing(
                day_posts,
                base_url=base_path,
                output_dir=day_dir,
                posts_per_page=self.POSTS_PER_PAGE_ARCHIVE,
                context=context,
                render_func=_render_day,
            )

    def _generate_tag_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each tag with pagination."""
        # Group posts by tag (case-insensitive)
        # Key is lowercase tag, value is (display_name, posts)
        posts_by_tag = self._group_posts_by_tag(posts)

        # Create tag directory
        tag_dir = self.site_config.output_dir / self.TAG_DIR
        tag_dir.mkdir(exist_ok=True)

        # Generate paginated pages for each tag
        for tag_lower, (tag_display, tag_posts) in posts_by_tag.items():
            # Sort tag posts by date (newest first)
            tag_posts.sort(key=post_sort_key, reverse=True)

            # Sanitize tag for filename (use lowercase version)
            safe_tag = sanitize_for_url(tag_lower)

            base_url = f"/{self.TAG_DIR}/{safe_tag}"
            # Each tag's pages live inside tag/{safe_tag}/ directory.
            tag_base_dir = tag_dir / safe_tag

            context = self._get_global_context()
            context["pages"] = pages

            # Default parameter values bind the current loop variables at
            # definition time (early binding), which is the standard Python
            # idiom for capturing loop state in a nested function.
            def _render_tag(
                page_posts: list[Post],
                page_num: int,
                total_pages: int,
                _display: str = tag_display,
                _safe: str = safe_tag,
                _ctx: dict[str, Any] = context,
            ) -> str:
                return self.renderer.render_tag_page(
                    _display,
                    page_posts,
                    page=page_num,
                    total_pages=total_pages,
                    safe_tag=_safe,
                    **_ctx,
                )

            self._generate_paginated_listing(
                tag_posts,
                base_url=base_url,
                output_dir=tag_base_dir,
                posts_per_page=self.POSTS_PER_PAGE_TAG,
                context=context,
                render_func=_render_tag,
            )

    def _group_posts_by_tag(
        self, posts: list[Post]
    ) -> dict[str, tuple[str, list[Post]]]:
        """Group posts by tag (case-insensitive).

        Args:
            posts: List of posts to group

        Returns:
            Dictionary mapping lowercase tag to (display_name, posts)
        """
        return self._group_posts_by_attribute(posts, lambda p: p.tags or [])

    def _generate_tags_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the tags overview page with word cloud."""
        # Group posts by tag to get counts
        posts_by_tag = self._group_posts_by_tag(posts)

        if not posts_by_tag:
            # No tags, skip generation
            return

        # Calculate tag counts and prepare data
        tag_data: list[dict[str, Any]] = [
            {
                "display_name": tag_display,
                "safe_tag": sanitize_for_url(tag_lower),
                "count": len(tag_posts),
                "tag_lower": tag_lower,
            }
            for tag_lower, (tag_display, tag_posts) in posts_by_tag.items()
        ]

        # Sort alphabetically by display name
        tag_data.sort(key=lambda x: x["display_name"].lower())

        self._calculate_cloud_font_sizes(tag_data)

        # Render the tags page
        context = self._get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.tags_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tags_url = self._get_tags_url()
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{tags_url}"
                if self.site_config.site_url
                else tags_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)

        html = self.renderer.render_tags_page(tag_data, **context)

        self._write_html(output_path, html)

    def _generate_categories_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the categories overview page with word cloud."""
        # Group posts by category to get counts
        posts_by_category = self._group_posts_by_category(posts)

        if not posts_by_category:
            # No categories, skip generation
            return

        # Calculate category counts and prepare data
        category_data: list[dict[str, Any]] = [
            {
                "display_name": category_display,
                "safe_category": sanitize_for_url(category_lower),
                "count": len(category_posts),
                "category_lower": category_lower,
            }
            for category_lower, (
                category_display,
                category_posts,
            ) in posts_by_category.items()
        ]

        # Sort alphabetically by display name
        category_data.sort(key=lambda x: x["display_name"].lower())

        self._calculate_cloud_font_sizes(category_data)

        # Render the categories page
        context = self._get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.categories_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        categories_url = self._get_categories_url()
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{categories_url}"
                if self.site_config.site_url
                else categories_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)

        html = self.renderer.render_categories_page(category_data, **context)

        self._write_html(output_path, html)

    def _generate_category_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each category with pagination."""
        # Group posts by category (case-insensitive)
        # Key is lowercase category, value is (display_name, posts)
        posts_by_category = self._group_posts_by_category(posts)

        # Create category directory
        category_dir = self.site_config.output_dir / self.CATEGORY_DIR
        category_dir.mkdir(exist_ok=True)

        # Generate paginated pages for each category
        for category_lower, (
            category_display,
            category_posts,
        ) in posts_by_category.items():
            # Sort category posts by date (newest first)
            category_posts.sort(key=post_sort_key, reverse=True)

            # Sanitize category for filename (use lowercase version)
            safe_category = sanitize_for_url(category_lower)

            base_url = f"/{self.CATEGORY_DIR}/{safe_category}"
            # Each category's pages live inside category/{safe_category}/ directory.
            category_base_dir = category_dir / safe_category

            context = self._get_global_context()
            context["pages"] = pages

            def _render_category(
                page_posts: list[Post],
                page_num: int,
                total_pages: int,
                _display: str = category_display,
                _safe: str = safe_category,
                _ctx: dict[str, Any] = context,
            ) -> str:
                return self.renderer.render_category_page(
                    _display,
                    page_posts,
                    page=page_num,
                    total_pages=total_pages,
                    safe_category=_safe,
                    **_ctx,
                )

            self._generate_paginated_listing(
                category_posts,
                base_url=base_url,
                output_dir=category_base_dir,
                posts_per_page=self.POSTS_PER_PAGE_CATEGORY,
                context=context,
                render_func=_render_category,
            )

    def _group_posts_by_attribute(
        self,
        posts: list[Post],
        get_values: Callable[[Post], list[str]],
    ) -> dict[str, tuple[str, list[Post]]]:
        """Group posts by a string attribute (case-insensitive).

        The first occurrence of each value is used as the display name; all
        subsequent occurrences of the same value (compared case-insensitively)
        are accumulated under the same key.

        Args:
            posts: List of posts to group.
            get_values: Callable that returns the list of attribute values for
                a single post (e.g. the post's tags or a single-element list
                containing the post's category).

        Returns:
            Dictionary mapping the lowercase attribute value to a
            ``(display_name, posts)`` tuple.
        """
        result: dict[str, tuple[str, list[Post]]] = {}
        for post in posts:
            for value in get_values(post):
                value_lower = value.lower()
                if value_lower not in result:
                    # Store the first occurrence as the display name.
                    result[value_lower] = (value, [])
                result[value_lower][1].append(post)
        return result

    def _group_posts_by_category(
        self, posts: list[Post]
    ) -> dict[str, tuple[str, list[Post]]]:
        """Group posts by category (case-insensitive).

        Args:
            posts: List of posts to group

        Returns:
            Dictionary mapping lowercase category to (display_name, posts)
        """
        return self._group_posts_by_attribute(
            posts, lambda p: [p.category] if p.category else []
        )

    def _calculate_cloud_font_sizes(
        self,
        data: list[dict[str, Any]],
        min_size: float = 1.0,
        max_size: float = 2.5,
    ) -> None:
        """Assign ``font_size`` to every item in a word-cloud data list.

        Uses linear interpolation between *min_size* and *max_size* based on
        each item's ``"count"`` field relative to the minimum and maximum
        counts in the list.  When all items share the same count, the midpoint
        size is used for every item.

        Mutates each dict in *data* in-place by adding a ``"font_size"`` key.

        Args:
            data: List of dicts, each containing at least a ``"count"`` key
                with an integer value.
            min_size: The minimum font size (em units) for the least-frequent
                item.
            max_size: The maximum font size (em units) for the most-frequent
                item.
        """
        if not data:
            return

        counts = [item["count"] for item in data]
        min_count = min(counts)
        max_count = max(counts)

        if max_count > min_count:
            for item in data:
                ratio = (item["count"] - min_count) / (max_count - min_count)
                item["font_size"] = min_size + ratio * (max_size - min_size)
        else:
            midpoint = (min_size + max_size) / 2
            for item in data:
                item["font_size"] = midpoint

    def _generate_feeds(self, posts: list[Post]) -> None:
        """Generate RSS and Atom feeds.

        Args:
            posts: List of all posts
        """
        feed_gen = BlogFeedGenerator(
            output_dir=self.site_config.output_dir,
            site_title=self.site_config.site_title,
            site_url=self.site_config.site_url,
            max_posts=self.site_config.posts_per_feed,
        )

        # Generate main index feeds
        feed_gen.generate_index_feeds(posts)

        # Generate category feeds
        posts_by_category = self._group_posts_by_category(posts)
        # Sort posts by date for each category
        for _category_lower, (
            _category_display,
            category_posts,
        ) in posts_by_category.items():
            category_posts.sort(key=post_sort_key, reverse=True)

        feed_gen.generate_category_feeds(posts_by_category)

    def _generate_search_index(self, posts: list[Post]) -> None:
        """Generate the search index JSON file.

        Args:
            posts: List of all posts to index.
        """
        write_search_index(posts, self.site_config.output_dir)

    def _generate_search_page(self, pages: list[Page]) -> None:
        """Generate the search page.

        Args:
            pages: List of static pages (for the sidebar navigation).
        """
        context = self._get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.search_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        search_url = self._get_search_url()
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{search_url}"
                if self.site_config.site_url
                else search_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)
        html = self.renderer.render_search_page(**context)
        self._write_html(output_path, html)

    def _generate_stats_page(
        self,
        posts: list[Post],
        pages: list[Page],
        backlink_map: "dict[str, list[Backlink]] | None" = None,
    ) -> None:
        """Generate the blog statistics page.

        Args:
            posts: All published posts; used to compute statistics.
            pages: List of static pages (for the sidebar navigation).
            backlink_map: Optional mapping from post URL to list of
                :class:`~blogmore.backlinks.Backlink` objects.  When provided,
                the statistics page includes a "Top Internal Links" section.
        """
        context = self._get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.stats_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        stats_url = self._get_stats_url()
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{stats_url}"
                if self.site_config.site_url
                else stats_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)
        blog_stats: BlogStats = compute_blog_stats(
            posts, self.site_config.site_url, backlink_map
        )
        html = self.renderer.render_stats_page(stats=blog_stats, **context)
        self._write_html(output_path, html)

    def _generate_calendar_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the calendar view page.

        Args:
            posts: All published posts; used to populate the calendar grid.
            pages: List of static pages (for the sidebar navigation).
        """
        context = self._get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.calendar_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        calendar_url = self._get_calendar_url()
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{calendar_url}"
                if self.site_config.site_url
                else calendar_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)
        # Determine page1_suffix for archive URL construction.  When
        # clean_urls is enabled, strip any index filename (e.g. "index.html")
        # so that calendar links to year/month/day archives end with a
        # trailing slash instead of "/index.html".
        page1_suffix = self.site_config.page_1_path.lstrip("/")
        if self.site_config.clean_urls:
            page1_suffix = make_url_clean(f"/{page1_suffix}").lstrip("/")
        calendar_years: list[CalendarYear] = build_calendar(
            posts, page1_suffix, forward=self.site_config.forward_calendar
        )
        html = self.renderer.render_calendar_page(
            calendar_years=calendar_years, **context
        )
        self._write_html(output_path, html)

    def _generate_graph_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the post-relationship graph page.

        Args:
            posts: All published posts; used to build graph nodes and edges.
            pages: List of static pages (for the sidebar navigation).
        """
        context = self._get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.graph_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        graph_url = self._get_graph_url()
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{graph_url}"
                if self.site_config.site_url
                else graph_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)
        graph_data: GraphData = build_graph_data(
            posts,
            tag_dir=self.TAG_DIR,
            category_dir=self.CATEGORY_DIR,
            site_url=self.site_config.site_url,
        )
        html = self.renderer.render_graph_page(
            graph_data_json=graph_data.to_json(), **context
        )
        self._write_html(output_path, html)

    def _remove_stale_search_files(self) -> None:
        """Remove search-related files left over from a previous build.

        When search is disabled, any search page (at the configured
        ``search_path`` or the default ``search.html``) and
        ``search_index.json`` that may have been written by an earlier
        build that had search enabled are deleted so they do not appear
        in the output directory.
        """
        # Always remove search_index.json (fixed location).
        stale_json = self.site_config.output_dir / "search_index.json"
        if stale_json.exists():
            stale_json.unlink()

        # Remove the search page at the configured path.
        stale_page = (
            self.site_config.output_dir / self.site_config.search_path.lstrip("/")
        ).resolve()
        if stale_page.exists():
            stale_page.unlink()

        # Also remove the default search.html location for backward
        # compatibility (in case the user previously used the default path).
        default_page = (self.site_config.output_dir / "search.html").resolve()
        if default_page.exists() and default_page != stale_page:
            default_page.unlink()

    def _generate_sitemap(self) -> None:
        """Generate the XML sitemap file.

        Writes ``sitemap.xml`` to the root of the output directory,
        containing an entry for every generated HTML page except the
        configured search page and any HTML files copied verbatim from
        the ``extras`` directory.
        """
        write_sitemap(
            self.site_config.output_dir,
            self.site_config.site_url,
            clean_urls=self.site_config.clean_urls,
            search_path=self.site_config.search_path,
            extra_excluded_paths=self._extras_html_paths,
            extra_urls=self.site_config.sitemap_extras,
        )

    def _copy_static_assets(self) -> None:
        """Copy static assets (CSS, JS, images) to output directory.

        When ``minify_css`` is enabled, ``style.css`` and all page-specific
        CSS files are minified; the originals are not written.

        When ``minify_js`` is enabled, the ``theme.js`` file is minified and
        written as ``theme.min.js`` (and ``search.js`` as ``search.min.js`` if
        search is enabled, ``graph.js`` as ``graph.min.js`` if graph is
        enabled); the originals are not written.
        """
        output_static = self.site_config.output_dir / "static"

        # Pre-compute set of CSS source filenames to skip when minifying.
        _css_source_filenames = {CSS_FILENAME} | set(_PAGE_SPECIFIC_CSS)

        # Clear output static directory if it exists
        if output_static.exists():
            shutil.rmtree(output_static)
        output_static.mkdir(parents=True, exist_ok=True)

        # First, copy bundled static assets
        try:
            # Get bundled static directory
            bundled_static = files("blogmore").joinpath("templates", "static")
            if bundled_static.is_dir():
                for item in bundled_static.iterdir():
                    if item.is_file():
                        # Only copy search.js when search is enabled
                        if (
                            item.name == SEARCH_JS_FILENAME
                            and not self.site_config.with_search
                        ):
                            continue
                        # Only copy graph.js when graph is enabled
                        if (
                            item.name == GRAPH_JS_FILENAME
                            and not self.site_config.with_graph
                        ):
                            continue
                        # When minifying CSS, skip all source CSS files
                        if (
                            item.name in _css_source_filenames
                            and self.site_config.minify_css
                        ):
                            continue
                        # When minifying JS, skip original JS files
                        if (
                            item.name == THEME_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            item.name == SEARCH_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            item.name == CODEBLOCKS_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            item.name == GRAPH_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        # Read content and write to output
                        content = item.read_bytes()
                        output_file = output_static / item.name
                        output_file.write_bytes(content)
                print("Copied bundled static assets")
        except Exception as e:
            print(f"Warning: Could not copy bundled static assets: {e}")

        # Then, copy custom static assets (if provided), which will override bundled ones
        if self.site_config.templates_dir is not None:
            custom_static_dir = self.site_config.templates_dir / "static"
            if custom_static_dir.exists():
                for item in custom_static_dir.rglob("*"):
                    if item.is_file():
                        relative_path = item.relative_to(custom_static_dir)
                        # When minifying CSS, skip all source CSS files from custom dir
                        if (
                            relative_path.name in _css_source_filenames
                            and self.site_config.minify_css
                        ):
                            continue
                        # When minifying JS, skip original JS files from custom dir too
                        if (
                            relative_path.name == THEME_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            relative_path.name == SEARCH_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            relative_path.name == CODEBLOCKS_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            relative_path.name == GRAPH_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        output_file = output_static / relative_path
                        output_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, output_file)
                print(f"Copied custom static assets from {custom_static_dir}")

        # Minify CSS if requested
        if self.site_config.minify_css:
            self._write_minified_css(output_static)

        # Always generate code.css (or code.min.css) from configured Pygments styles.
        self._write_code_css(output_static)

        # Minify JS if requested
        if self.site_config.minify_js:
            self._write_minified_js(output_static, THEME_JS_FILENAME)
            self._write_minified_js(output_static, CODEBLOCKS_JS_FILENAME)
            if self.site_config.with_search:
                self._write_minified_js(output_static, SEARCH_JS_FILENAME)
            if self.site_config.with_graph:
                self._write_minified_js(output_static, GRAPH_JS_FILENAME)

    def _copy_extras(self) -> None:
        """Copy extra files from the extras directory to the output directory.

        Files in the extras directory are copied to the output root, preserving
        directory structure relative to the extras directory. If a file would
        override an existing file, it is allowed but a message is printed.

        After copying, ``self._extras_html_paths`` is updated with the relative
        paths (forward-slash strings) of every HTML file that was copied.  This
        is used by ``_generate_sitemap()`` to exclude those files from the
        sitemap, since they are not pages generated by BlogMore.
        """
        extras_dir = self._content_dir / "extras"

        if not extras_dir.exists():
            return

        # Count how many extras we copy
        extras_count = 0
        override_count = 0
        failed_count = 0

        # Track relative paths of HTML files copied from extras
        extras_html_paths: set[str] = set()

        # Recursively copy all files from the extras directory
        for file_path in extras_dir.rglob("*"):
            # Skip directories
            if file_path.is_file():
                try:
                    # Calculate relative path from extras directory to preserve structure
                    relative_path = file_path.relative_to(extras_dir)
                    # Copy to output_dir root, preserving directory structure
                    output_path = self.site_config.output_dir / relative_path

                    # Check if file already exists
                    file_exists = output_path.exists()

                    # Create parent directories if they don't exist
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file preserving metadata
                    shutil.copy2(file_path, output_path)
                    extras_count += 1

                    # Track HTML files so they can be excluded from the sitemap
                    relative_str = str(relative_path).replace("\\", "/")
                    if relative_str.endswith(".html"):
                        extras_html_paths.add(relative_str)

                    # Print message if we overrode an existing file
                    if file_exists:
                        print(f"Overriding existing file: {relative_path}")
                        override_count += 1
                except (OSError, PermissionError) as e:
                    print(f"Warning: Failed to copy extra file {file_path}: {e}")
                    failed_count += 1
                    continue

        self._extras_html_paths = frozenset(extras_html_paths)

        if extras_count > 0:
            print(f"Copied {extras_count} extra file(s) from {extras_dir}")
        if override_count > 0:
            print(f"Overrode {override_count} existing file(s)")
        if failed_count > 0:
            print(f"Warning: Failed to copy {failed_count} extra file(s)")
