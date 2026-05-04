"""Protocol defining the interface for the site generator.

This module provides a [`GeneratorProtocol`][blogmore.generator._protocol.GeneratorProtocol]
that describes the combined interface of all generator mixins.  It is used
to provide type safety for cross-mixin method calls without requiring
circular imports or ``type: ignore`` pragmas.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from blogmore.parser import Post
    from blogmore.renderer import TemplateRenderer
    from blogmore.site_config import SiteConfig


class GeneratorProtocol(Protocol):
    """Protocol describing the full interface of the [`SiteGenerator`][blogmore.generator.site.SiteGenerator].

    This protocol includes all attributes and methods provided by the various
    generator mixins ([`AssetsMixin`][blogmore.generator._assets.AssetsMixin],
    [`ContextMixin`][blogmore.generator._context.ContextMixin], etc.) and is
    used to type the ``self`` argument in mixin methods that call methods
    defined in other mixins.
    """

    site_config: SiteConfig
    renderer: TemplateRenderer
    _fontawesome_css_url: str
    _cache_bust_token: str
    _extras_html_paths: frozenset[str]

    # Pagination constants
    POSTS_PER_PAGE_INDEX: int
    POSTS_PER_PAGE_TAG: int
    POSTS_PER_PAGE_CATEGORY: int
    POSTS_PER_PAGE_ARCHIVE: int

    def _with_cache_bust(self, url: str) -> str: ...

    def _get_asset_url(
        self,
        regular: str,
        minify: bool,
        *,
        cache_bust: bool = True,
    ) -> str: ...

    def _get_global_context(self) -> dict[str, Any]: ...

    def _detect_favicon(self) -> str | None: ...

    def _detect_generated_icons(self) -> bool: ...

    def _get_search_url(self) -> str: ...

    def _get_archive_url(self) -> str: ...

    def _get_tags_url(self) -> str: ...

    def _get_categories_url(self) -> str: ...

    def _get_stats_url(self) -> str: ...

    def _get_calendar_url(self) -> str: ...

    def _get_graph_url(self) -> str: ...

    def _get_pagination_url(self, base_url: str, page_num: int) -> str: ...

    def _build_pagination_page_urls(
        self, base_url: str, total_pages: int
    ) -> list[str]: ...

    def _get_pagination_output_path(self, base_dir: Path, page_num: int) -> Path: ...

    def _pagination_prev_next(
        self,
        page_num: int,
        page_urls: list[str],
    ) -> tuple[str | None, str | None]: ...

    def _canonical_url_for_path(self, output_path: Path) -> str: ...

    def _write_html(self, output_path: Path, html: str) -> None: ...

    def _generate_paginated_listing(
        self,
        post_list: list[Post],
        base_url: str,
        output_dir: Path,
        posts_per_page: int,
        context: dict[str, Any],
        render_func: Callable[[list[Post], int, int], str],
    ) -> None: ...

    def _group_posts_by_tag(
        self, posts: list[Post]
    ) -> dict[str, tuple[str, list[Post]]]: ...

    def _group_posts_by_category(
        self, posts: list[Post]
    ) -> dict[str, tuple[str, list[Post]]]: ...

    def _calculate_cloud_font_sizes(
        self,
        data: list[dict[str, Any]],
        min_size: float = 1.0,
        max_size: float = 2.5,
    ) -> None: ...
