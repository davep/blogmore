"""Template context preparation for the site generator."""

from typing import Any

from blogmore import __version__
from blogmore.clean_url import make_url_clean
from blogmore.fontawesome import FONTAWESOME_CDN_BRANDS_WOFF2_URL
from blogmore.generator.constants import (
    ARCHIVE_CSS_FILENAME,
    CALENDAR_CSS_FILENAME,
    CODE_CSS_FILENAME,
    CODEBLOCKS_JS_FILENAME,
    CSS_FILENAME,
    GRAPH_CSS_FILENAME,
    GRAPH_JS_FILENAME,
    SEARCH_CSS_FILENAME,
    SEARCH_JS_FILENAME,
    STATS_CSS_FILENAME,
    TAG_CLOUD_CSS_FILENAME,
    THEME_JS_FILENAME,
)
from blogmore.generator.paths import (
    get_asset_url,
    get_configured_url,
    with_cache_bust,
)
from blogmore.pagination_path import resolve_pagination_page_path
from blogmore.parser import Page
from blogmore.site_config import SiteConfig


def resolve_sidebar_pages(site_config: SiteConfig, pages: list[Page]) -> list[Page]:
    """Resolve which pages appear in the sidebar and in what order.

    When `site_config.sidebar_pages` is `None` or empty every page in
    `pages` is returned unchanged (the default behaviour).  When a list
    of slugs is provided, only pages whose slug appears in that list are
    returned, in the order defined by the list.  Slugs that do not match
    any existing page are silently ignored.

    Args:
        site_config: The site configuration.
        pages: All parsed static pages.

    Returns:
        The ordered list of pages to display in the sidebar.
    """
    if not site_config.sidebar_pages:
        return pages

    pages_by_slug: dict[str, Page] = {page.slug: page for page in pages}
    return [
        pages_by_slug[slug]
        for slug in site_config.sidebar_pages
        if slug in pages_by_slug
    ]


def build_global_context(
    site_config: SiteConfig,
    cache_bust_token: str,
    fontawesome_css_url: str,
    favicon_url: str | None,
    has_platform_icons: bool,
    tag_dir: str,
    category_dir: str,
) -> dict[str, Any]:
    """Get the global context available to all templates."""
    page1_suffix = resolve_pagination_page_path(site_config.page_1_path, 1)
    if site_config.clean_urls:
        page1_suffix = make_url_clean(page1_suffix)
    context = {
        "site_title": site_config.site_title,
        "site_subtitle": site_config.site_subtitle,
        "site_description": site_config.site_description,
        "site_keywords": site_config.site_keywords,
        "site_url": site_config.site_url,
        "tag_dir": tag_dir,
        "category_dir": category_dir,
        "favicon_url": favicon_url,
        "has_platform_icons": has_platform_icons,
        "blogmore_version": __version__,
        "with_search": site_config.with_search,
        "search_url": get_configured_url(site_config, "search_path"),
        "archive_url": get_configured_url(site_config, "archive_path"),
        "tags_url": get_configured_url(site_config, "tags_path"),
        "categories_url": get_configured_url(site_config, "categories_path"),
        "with_stats": site_config.with_stats,
        "stats_url": get_configured_url(site_config, "stats_path"),
        "with_calendar": site_config.with_calendar,
        "forward_calendar": site_config.forward_calendar,
        "calendar_url": get_configured_url(site_config, "calendar_path"),
        "with_graph": site_config.with_graph,
        "graph_url": get_configured_url(site_config, "graph_path"),
        "with_read_time": site_config.with_read_time,
        "with_backlinks": site_config.with_backlinks,
        "backlinks_title": site_config.backlinks_title,
        "with_advert": site_config.with_advert,
        "default_author": site_config.default_author,
        "extra_head_tags": site_config.head,
        "fontawesome_css_url": with_cache_bust(fontawesome_css_url, cache_bust_token),
        "fontawesome_woff2_url": FONTAWESOME_CDN_BRANDS_WOFF2_URL,
        "styles_css_url": get_asset_url(
            CSS_FILENAME, site_config.minify_css, cache_bust_token
        ),
        "search_css_url": get_asset_url(
            SEARCH_CSS_FILENAME,
            site_config.minify_css,
            cache_bust_token,
        ),
        "stats_css_url": get_asset_url(
            STATS_CSS_FILENAME,
            site_config.minify_css,
            cache_bust_token,
        ),
        "archive_css_url": get_asset_url(
            ARCHIVE_CSS_FILENAME,
            site_config.minify_css,
            cache_bust_token,
        ),
        "tag_cloud_css_url": get_asset_url(
            TAG_CLOUD_CSS_FILENAME,
            site_config.minify_css,
            cache_bust_token,
        ),
        "calendar_css_url": get_asset_url(
            CALENDAR_CSS_FILENAME,
            site_config.minify_css,
            cache_bust_token,
        ),
        "graph_css_url": get_asset_url(
            GRAPH_CSS_FILENAME,
            site_config.minify_css,
            cache_bust_token,
        ),
        "code_css_url": get_asset_url(
            CODE_CSS_FILENAME,
            site_config.minify_css,
            cache_bust_token,
        ),
        "theme_js_url": get_asset_url(
            THEME_JS_FILENAME,
            site_config.minify_js,
            cache_bust_token,
        ),
        "search_js_url": get_asset_url(
            SEARCH_JS_FILENAME,
            site_config.minify_js,
            cache_bust_token,
        ),
        "codeblocks_js_url": get_asset_url(
            CODEBLOCKS_JS_FILENAME,
            site_config.minify_js,
            cache_bust_token,
        ),
        "graph_js_url": get_asset_url(
            GRAPH_JS_FILENAME,
            site_config.minify_js,
            cache_bust_token,
        ),
        "pagination_page1_suffix": page1_suffix,
    }
    # Merge sidebar config into context
    context.update(site_config.sidebar_config)
    return context
