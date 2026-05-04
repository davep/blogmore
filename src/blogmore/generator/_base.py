"""Abstract base class shared by all [`SiteGenerator`][blogmore.generator.site.SiteGenerator] mixins.

[`GeneratorBase`][blogmore.generator._base.GeneratorBase] declares every
instance attribute and every method that is called *across* mixin boundaries
so that mypy can type-check all mixin code without `# type: ignore` comments.

Every mixin whose class hierarchy does not already include another mixin that
inherits from this base must inherit from it directly.  At runtime the MRO of
[`SiteGenerator`][blogmore.generator.site.SiteGenerator] ensures that all
abstract stubs are satisfied by the concrete implementations scattered across
the various mixin modules.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any

from blogmore.parser import Post
from blogmore.renderer import TemplateRenderer
from blogmore.site_config import SiteConfig


class GeneratorBase(ABC):
    """Shared abstract base for all `SiteGenerator` mixin classes.

    Declares the complete set of instance attributes and cross-mixin method
    stubs that the mixin layer depends on.  Inheriting from this class gives
    mypy full visibility of the composed interface without requiring any
    `# type: ignore` pragmas in mixin code.

    The class is intentionally abstract: it is never instantiated on its own.
    [`SiteGenerator`][blogmore.generator.site.SiteGenerator] is the only
    concrete subclass and it satisfies every abstract stub by composing all
    mixin implementations.
    """

    # ------------------------------------------------------------------
    # Instance attributes
    # These are declared here once so that every mixin can reference them
    # on `self` without repeating the annotations in each module.
    # ------------------------------------------------------------------

    site_config: SiteConfig
    renderer: TemplateRenderer
    _fontawesome_css_url: str
    _cache_bust_token: str
    _extras_html_paths: frozenset[str]
    POSTS_PER_PAGE_INDEX: int
    POSTS_PER_PAGE_TAG: int
    POSTS_PER_PAGE_CATEGORY: int
    POSTS_PER_PAGE_ARCHIVE: int

    # ------------------------------------------------------------------
    # Cross-mixin method stubs
    # Each stub is declared here and implemented in exactly one mixin.
    # Declaring them as @abstractmethod means SiteGenerator cannot be
    # instantiated if a mixin is accidentally removed from its bases.
    # ------------------------------------------------------------------

    # -- AssetsMixin (called by ContextMixin) --------------------------

    @abstractmethod
    def _detect_favicon(self) -> str | None:
        """Return the URL path of the site favicon, or ``None`` if absent."""

    @abstractmethod
    def _detect_generated_icons(self) -> bool:
        """Return ``True`` when platform icons have been generated."""

    # -- ContextMixin (called by DateArchivesMixin, ListingMixin,
    #                  OptionalPagesMixin, PagesMixin) ------------------

    @abstractmethod
    def _get_global_context(self) -> dict[str, Any]:
        """Return the global template context dict populated for the current build."""

    @abstractmethod
    def _get_search_url(self) -> str:
        """Return the URL path for the configured search page."""

    @abstractmethod
    def _get_archive_url(self) -> str:
        """Return the URL path for the configured archive page."""

    @abstractmethod
    def _get_tags_url(self) -> str:
        """Return the URL path for the configured tags overview page."""

    @abstractmethod
    def _get_categories_url(self) -> str:
        """Return the URL path for the configured categories overview page."""

    @abstractmethod
    def _get_stats_url(self) -> str:
        """Return the URL path for the configured statistics page."""

    @abstractmethod
    def _get_calendar_url(self) -> str:
        """Return the URL path for the configured calendar page."""

    @abstractmethod
    def _get_graph_url(self) -> str:
        """Return the URL path for the configured graph page."""

    # -- MinifyMixin (called by ListingMixin, OptionalPagesMixin,
    #                 PagesMixin) ---------------------------------------

    @abstractmethod
    def _write_html(self, output_path: Path, html: str) -> None:
        """Write *html* to *output_path*, minifying when configured."""

    # -- PathsMixin (called by ListingMixin, PagesMixin) ---------------

    @abstractmethod
    def _get_pagination_url(self, base_url: str, page_num: int) -> str:
        """Return the URL for *page_num* within *base_url*."""

    @abstractmethod
    def _build_pagination_page_urls(self, base_url: str, total_pages: int) -> list[str]:
        """Return the full ordered list of page URLs for a paginated section."""

    @abstractmethod
    def _get_pagination_output_path(self, base_dir: Path, page_num: int) -> Path:
        """Return the output file path for *page_num* inside *base_dir*."""

    @abstractmethod
    def _canonical_url_for_path(self, output_path: Path) -> str:
        """Return the fully-qualified canonical URL for *output_path*."""

    @staticmethod
    @abstractmethod
    def _pagination_prev_next(
        page_num: int,
        page_urls: list[str],
    ) -> tuple[str | None, str | None]:
        """Return ``(prev_url, next_url)`` for *page_num* in *page_urls*."""

    # -- GroupingMixin (called by ListingMixin, OptionalPagesMixin) ----

    @abstractmethod
    def _group_posts_by_tag(
        self, posts: list[Post]
    ) -> dict[str, tuple[str, list[Post]]]:
        """Return posts grouped by tag (case-insensitive)."""

    @abstractmethod
    def _group_posts_by_category(
        self, posts: list[Post]
    ) -> dict[str, tuple[str, list[Post]]]:
        """Return posts grouped by category (case-insensitive)."""

    @abstractmethod
    def _calculate_cloud_font_sizes(
        self,
        data: list[dict[str, Any]],
        min_size: float = 1.0,
        max_size: float = 2.5,
    ) -> None:
        """Assign ``font_size`` to every item in a word-cloud data list."""

    # -- ListingMixin (called by DateArchivesMixin — template method) --

    @abstractmethod
    def _generate_paginated_listing(
        self,
        post_list: list[Post],
        base_url: str,
        output_dir: Path,
        posts_per_page: int,
        context: dict[str, Any],
        render_func: Callable[[list[Post], int, int], str],
    ) -> None:
        """Paginate *post_list* and write one HTML file per page."""


### _base.py ends here
