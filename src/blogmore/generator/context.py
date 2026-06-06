"""Template-context and URL-helper methods for the site generator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from blogmore import __version__
from blogmore.clean_url import make_url_clean
from blogmore.fontawesome import FONTAWESOME_CDN_BRANDS_WOFF2_URL
from blogmore.generator.constants import (
    ARCHIVE_CSS_FILENAME,
    BUNDLE_CSS_FILENAME,
    CALENDAR_CSS_FILENAME,
    CATEGORY_DIR,
    CODE_CSS_FILENAME,
    CODEBLOCKS_JS_FILENAME,
    CSS_FILENAME,
    GRAPH_CSS_FILENAME,
    GRAPH_JS_FILENAME,
    SEARCH_CSS_FILENAME,
    SEARCH_JS_FILENAME,
    STATS_CSS_FILENAME,
    TAG_CLOUD_CSS_FILENAME,
    TAG_DIR,
    THEME_JS_FILENAME,
)
from blogmore.generator.utils import minified_filename
from blogmore.image_html import render_logo_picture_html
from blogmore.pagination_path import resolve_pagination_page_path

if TYPE_CHECKING:
    from blogmore.image_manager import ImageManager
    from blogmore.site_config import SiteConfig


class ContextBuilder:
    """Builds template contexts and resolves configured page URLs."""

    def __init__(
        self,
        site_config: SiteConfig,
        cache_bust_token: str = "",
        favicon_url: str | None = None,
        has_platform_icons: bool = False,
        fontawesome_css_url: str = "",
        fontawesome_is_bundled: bool = False,
        theme_js_content: str | None = None,
        image_manager: ImageManager | None = None,
    ) -> None:
        """Initialize the context builder.

        Args:
            site_config: The site configuration.
            cache_bust_token: Token used for URL cache-busting.
            favicon_url: URL for the site favicon.
            has_platform_icons: Whether generated platform icons exist.
            fontawesome_css_url: URL for the FontAwesome stylesheet.
            fontawesome_is_bundled: Whether FontAwesome is included in the bundle.
            theme_js_content: The content of theme.js for inlining.
            image_manager: The image manager for image optimisation.
        """
        self.site_config = site_config
        self.cache_bust_token = cache_bust_token
        self.favicon_url = favicon_url
        self.has_platform_icons = has_platform_icons
        self.fontawesome_css_url = fontawesome_css_url
        self.fontawesome_is_bundled = fontawesome_is_bundled
        self.theme_js_content = theme_js_content
        self.image_manager = image_manager
        self.has_series = False

    def with_cache_bust(self, url: str) -> str:
        """Return a URL with a cache-busting query parameter appended.

        External URLs (i.e. those that start with ``http://`` or ``https://``)
        are returned unchanged.  Local URLs (starting with ``/``) have
        ``?v=<token>`` appended so that browsers re-fetch them when the site is
        regenerated.

        Args:
            url: The URL to process.

        Returns:
            The URL with a cache-busting query parameter appended, or the
            original URL if it is external or the token has not been set.
        """
        if (
            not self.cache_bust_token
            or not url
            or url.startswith(("http://", "https://"))
        ):
            return url
        return f"{url}?v={self.cache_bust_token}"

    def get_configured_url(self, path_field_name: str) -> str:
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

    def get_search_url(self) -> str:
        """Return the URL path for the configured search page.

        Returns:
            The URL path for the search page, always starting with ``/``.
        """
        return self.get_configured_url("search_path")

    def get_archive_url(self) -> str:
        """Return the URL path for the configured archive page.

        Returns:
            The URL path for the archive page, always starting with ``/``.
        """
        return self.get_configured_url("archive_path")

    def get_tags_url(self) -> str:
        """Return the URL path for the configured tags overview page.

        Returns:
            The URL path for the tags page, always starting with ``/``.
        """
        return self.get_configured_url("tags_path")

    def get_series_index_url(self) -> str:
        """Return the URL path for the configured series index page.

        Returns:
            The URL path for the series index page, always starting with ``/``.
        """
        return self.get_configured_url("series_index_path")

    def get_categories_url(self) -> str:
        """Return the URL path for the configured categories overview page.

        Returns:
            The URL path for the categories page, always starting with ``/``.
        """
        return self.get_configured_url("categories_path")

    def get_stats_url(self) -> str:
        """Return the URL path for the configured statistics page.

        Returns:
            The URL path for the statistics page, always starting with ``/``.
        """
        return self.get_configured_url("stats_path")

    def get_calendar_url(self) -> str:
        """Return the URL path for the configured calendar page.

        Returns:
            The URL path for the calendar page, always starting with ``/``.
        """
        return self.get_configured_url("calendar_path")

    def get_graph_url(self) -> str:
        """Return the URL path for the configured graph page.

        Returns:
            The URL path for the graph page, always starting with ``/``.
        """
        return self.get_configured_url("graph_path")

    def get_asset_url(
        self,
        regular: str,
        minify: bool,
        *,
        cache_bust: bool = True,
    ) -> str:
        """Build the ``/static/`` URL for one asset, choosing the minified variant when requested.

        When *minify* is ``True`` the minified filename is derived from
        *regular* via [`minified_filename`][blogmore.generator.utils.minified_filename].

        Args:
            regular: Filename for the non-minified asset (e.g. ``"style.css"``).
            minify: When ``True``, the minified filename is used.
            cache_bust: When ``True`` (the default), the URL is passed through
                [`with_cache_bust`][blogmore.generator.context.ContextBuilder.with_cache_bust]
                so that browsers re-fetch the file after each build.

        Returns:
            The ``/static/<filename>`` URL, with an optional ``?v=<token>``
            cache-busting query parameter.
        """
        name = minified_filename(regular) if minify else regular
        url = f"/static/{name}"
        return self.with_cache_bust(url) if cache_bust else url

    def get_global_context(self) -> dict[str, Any]:
        """Get the global context available to all templates.

        Returns:
            A dictionary containing all site-wide template variables.
        """
        page1_suffix = resolve_pagination_page_path(self.site_config.page_1_path, 1)
        if self.site_config.clean_urls:
            page1_suffix = make_url_clean(page1_suffix)
        context = {
            "site_title": self.site_config.site_title,
            "site_subtitle": self.site_config.site_subtitle,
            "site_description": self.site_config.site_description,
            "site_keywords": self.site_config.site_keywords,
            "site_url": self.site_config.site_url,
            "tag_dir": TAG_DIR,
            "category_dir": CATEGORY_DIR,
            "favicon_url": self.favicon_url,
            "has_platform_icons": self.has_platform_icons,
            "blogmore_version": __version__,
            "with_search": self.site_config.with_search,
            "search_url": self.get_search_url(),
            "archive_url": self.get_archive_url(),
            "tags_url": self.get_tags_url(),
            "categories_url": self.get_categories_url(),
            "has_series": self.has_series,
            "series_index_url": self.get_series_index_url(),
            "series_css_url": self.get_asset_url(
                "series.css", self.site_config.minify_css
            ),
            "with_stats": self.site_config.with_stats,
            "stats_url": self.get_stats_url(),
            "with_calendar": self.site_config.with_calendar,
            "forward_calendar": self.site_config.forward_calendar,
            "calendar_url": self.get_calendar_url(),
            "with_graph": self.site_config.with_graph,
            "graph_url": self.get_graph_url(),
            "with_mermaid": self.site_config.with_mermaid,
            "has_mermaid": False,
            "with_maths": self.site_config.with_maths,
            "maths_provider": self.site_config.maths_provider,
            "has_math": False,
            "with_read_time": self.site_config.with_read_time,
            "with_gfi": self.site_config.with_gfi,
            "with_backlinks": self.site_config.with_backlinks,
            "with_related": self.site_config.with_related,
            "backlinks_title": self.site_config.backlinks_title,
            "related_title": self.site_config.related_title,
            "with_advert": self.site_config.with_advert,
            "show_author": self.site_config.show_author,
            "default_author": self.site_config.default_author,
            "default_author_url": self.site_config.default_author_url,
            "extra_head_tags": self.site_config.head,
            "bundle_css": self.site_config.bundle_css,
            "bundle_css_url": self.get_asset_url(
                BUNDLE_CSS_FILENAME, self.site_config.minify_css
            ),
            "inline_theme_js": self.site_config.inline_theme_js,
            "theme_js_content": self.theme_js_content,
            "fontawesome_is_bundled": self.fontawesome_is_bundled,
            "fontawesome_css_url": self.with_cache_bust(self.fontawesome_css_url),
            "fontawesome_woff2_url": FONTAWESOME_CDN_BRANDS_WOFF2_URL,
            "styles_css_url": self.get_asset_url(
                CSS_FILENAME, self.site_config.minify_css
            ),
            "search_css_url": self.get_asset_url(
                SEARCH_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "stats_css_url": self.get_asset_url(
                STATS_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "archive_css_url": self.get_asset_url(
                ARCHIVE_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "tag_cloud_css_url": self.get_asset_url(
                TAG_CLOUD_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "calendar_css_url": self.get_asset_url(
                CALENDAR_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "graph_css_url": self.get_asset_url(
                GRAPH_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "code_css_url": self.get_asset_url(
                CODE_CSS_FILENAME,
                self.site_config.minify_css,
            ),
            "theme_js_url": self.get_asset_url(
                THEME_JS_FILENAME,
                self.site_config.minify_js,
            ),
            "search_js_url": self.get_asset_url(
                SEARCH_JS_FILENAME,
                self.site_config.minify_js,
            ),
            "codeblocks_js_url": self.get_asset_url(
                CODEBLOCKS_JS_FILENAME,
                self.site_config.minify_js,
            ),
            "graph_js_url": self.get_asset_url(
                GRAPH_JS_FILENAME,
                self.site_config.minify_js,
            ),
            "pagination_page1_suffix": page1_suffix,
            "site_logo_html": None,
        }
        # Merge sidebar config into context
        context.update(self.site_config.sidebar_config)

        # If image optimisation is on and the logo is a local file, replace the
        # plain site_logo URL with the responsive <picture> HTML string.
        logo_path = self.site_config.sidebar_config.get("site_logo")
        if self.image_manager and logo_path and self.site_config.optimise_images:
            assert self.site_config.content_dir is not None
            result = render_logo_picture_html(
                logo_path,
                self.site_config.content_dir,
                self.site_config.site_title,
                self.image_manager,
            )
            if result is not None:
                context["site_logo_html"], context["site_logo"] = result

        # Ensure SiteConfig fields take precedence over any residual sidebar_config values.
        context["socials_title"] = self.site_config.socials_title
        context["links_title"] = self.site_config.links_title
        return context
