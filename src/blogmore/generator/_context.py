"""Mixin providing template-context and URL-helper methods for
[`SiteGenerator`][blogmore.generator.site.SiteGenerator].
"""

from typing import TYPE_CHECKING, Any

from blogmore import __version__
from blogmore.clean_url import make_url_clean
from blogmore.fontawesome import (
    FONTAWESOME_CDN_BRANDS_WOFF2_URL,
)
from blogmore.generator.constants import (
    ARCHIVE_CSS_FILENAME,
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
from blogmore.pagination_path import resolve_pagination_page_path

if TYPE_CHECKING:
    from blogmore.site_config import SiteConfig


class _ContextMixin:
    """Mixin that builds template contexts and resolves configured page URLs.

    This mixin is intended to be composed into
    [`SiteGenerator`][blogmore.generator.site.SiteGenerator].  It expects
    the host class to provide the following instance attributes:

    - `site_config` ([`SiteConfig`][blogmore.site_config.SiteConfig])
    - `_fontawesome_css_url` (`str`)
    - `_cache_bust_token` (`str`)
    """

    site_config: "SiteConfig"
    _fontawesome_css_url: str
    _cache_bust_token: str

    def _with_cache_bust(self, url: str) -> str:
        """Return a URL with a cache-busting query parameter appended.

        External URLs (i.e. those that start with ``http://`` or ``https://``)
        are returned unchanged.  Local URLs (starting with ``/``) have
        ``?v=<token>`` appended so that browsers re-fetch them when the site is
        regenerated.  If no cache-busting token has been set (e.g. before
        [`generate`][blogmore.generator.site.SiteGenerator.generate] is called)
        the URL is returned as-is.

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
        *regular* via [`minified_filename`][blogmore.generator.utils.minified_filename].

        Args:
            regular: Filename for the non-minified asset (e.g. ``"style.css"``).
            minify: When ``True``, the minified filename is used.
            cache_bust: When ``True`` (the default), the URL is passed through
                [`_with_cache_bust`][blogmore.generator._context._ContextMixin._with_cache_bust]
                so that browsers re-fetch the file after each build.

        Returns:
            The ``/static/<filename>`` URL, with an optional ``?v=<token>``
            cache-busting query parameter.
        """
        name = minified_filename(regular) if minify else regular
        url = f"/static/{name}"
        return self._with_cache_bust(url) if cache_bust else url

    def _get_global_context(self) -> dict[str, Any]:
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
            "favicon_url": self._detect_favicon(),  # type: ignore[attr-defined]
            "has_platform_icons": self._detect_generated_icons(),  # type: ignore[attr-defined]
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
            ),
            "search_js_url": self._get_asset_url(
                SEARCH_JS_FILENAME,
                self.site_config.minify_js,
            ),
            "codeblocks_js_url": self._get_asset_url(
                CODEBLOCKS_JS_FILENAME,
                self.site_config.minify_js,
            ),
            "graph_js_url": self._get_asset_url(
                GRAPH_JS_FILENAME,
                self.site_config.minify_js,
            ),
            "pagination_page1_suffix": page1_suffix,
        }
        # Merge sidebar config into context
        context.update(self.site_config.sidebar_config)
        return context


### _context.py ends here
