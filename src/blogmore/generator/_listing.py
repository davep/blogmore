"""Mixin providing paginated-listing generation for
[`SiteGenerator`][blogmore.generator.site.SiteGenerator].
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from blogmore.generator._date_archives import _DateArchivesMixin
from blogmore.generator.constants import CATEGORY_DIR, TAG_DIR
from blogmore.generator.utils import paginate_posts
from blogmore.parser import Page, Post, post_sort_key, sanitize_for_url
from blogmore.renderer import TemplateRenderer
from blogmore.site_config import SiteConfig


class _ListingMixin(_DateArchivesMixin):
    """Mixin that generates paginated listing pages for archives, tags, and categories.

    This mixin is intended to be composed into
    [`SiteGenerator`][blogmore.generator.site.SiteGenerator].  It expects
    the host class to provide the following instance attributes:

    - `site_config` ([`SiteConfig`][blogmore.site_config.SiteConfig])
    - `renderer` ([`TemplateRenderer`][blogmore.renderer.TemplateRenderer])
    - `POSTS_PER_PAGE_TAG` (`int`)
    - `POSTS_PER_PAGE_CATEGORY` (`int`)
    - `POSTS_PER_PAGE_ARCHIVE` (`int`)
    """

    site_config: "SiteConfig"
    renderer: "TemplateRenderer"
    POSTS_PER_PAGE_TAG: int
    POSTS_PER_PAGE_CATEGORY: int
    POSTS_PER_PAGE_ARCHIVE: int

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
        page_urls = self._build_pagination_page_urls(base_url, total_pages)  # type: ignore[attr-defined]

        for page_num, page_posts in enumerate(paginated_posts, start=1):
            output_path = self._get_pagination_output_path(output_dir, page_num)  # type: ignore[attr-defined]
            context["canonical_url"] = self._canonical_url_for_path(output_path)  # type: ignore[attr-defined]
            prev_url, next_url = self._pagination_prev_next(page_num, page_urls)  # type: ignore[attr-defined]
            context["prev_page_url"] = prev_url
            context["next_page_url"] = next_url
            context["pagination_page_urls"] = page_urls
            html = render_func(page_posts, page_num, total_pages)
            self._write_html(output_path, html)  # type: ignore[attr-defined]

    def _generate_tag_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each tag with pagination.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
        # Group posts by tag (case-insensitive)
        # Key is lowercase tag, value is (display_name, posts)
        posts_by_tag = self._group_posts_by_tag(posts)  # type: ignore[attr-defined]

        # Create tag directory
        tag_dir = self.site_config.output_dir / TAG_DIR
        tag_dir.mkdir(exist_ok=True)

        # Generate paginated pages for each tag
        for tag_lower, (tag_display, tag_posts) in posts_by_tag.items():
            # Sort tag posts by date (newest first)
            tag_posts.sort(key=post_sort_key, reverse=True)

            # Sanitize tag for filename (use lowercase version)
            safe_tag = sanitize_for_url(tag_lower)

            base_url = f"/{TAG_DIR}/{safe_tag}"
            # Each tag's pages live inside tag/{safe_tag}/ directory.
            tag_base_dir = tag_dir / safe_tag

            context = self._get_global_context()  # type: ignore[attr-defined]
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

    def _generate_tags_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the tags overview page with word cloud.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
        # Group posts by tag to get counts
        posts_by_tag = self._group_posts_by_tag(posts)  # type: ignore[attr-defined]

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

        self._calculate_cloud_font_sizes(tag_data)  # type: ignore[attr-defined]

        # Render the tags page
        context = self._get_global_context()  # type: ignore[attr-defined]
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.tags_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tags_url = self._get_tags_url()  # type: ignore[attr-defined]
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{tags_url}"
                if self.site_config.site_url
                else tags_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)  # type: ignore[attr-defined]

        html = self.renderer.render_tags_page(tag_data, **context)

        self._write_html(output_path, html)  # type: ignore[attr-defined]

    def _generate_categories_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the categories overview page with word cloud.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
        # Group posts by category to get counts
        posts_by_category = self._group_posts_by_category(posts)  # type: ignore[attr-defined]

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

        self._calculate_cloud_font_sizes(category_data)  # type: ignore[attr-defined]

        # Render the categories page
        context = self._get_global_context()  # type: ignore[attr-defined]
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.categories_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        categories_url = self._get_categories_url()  # type: ignore[attr-defined]
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{categories_url}"
                if self.site_config.site_url
                else categories_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)  # type: ignore[attr-defined]

        html = self.renderer.render_categories_page(category_data, **context)

        self._write_html(output_path, html)  # type: ignore[attr-defined]

    def _generate_category_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each category with pagination.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
        # Group posts by category (case-insensitive)
        # Key is lowercase category, value is (display_name, posts)
        posts_by_category = self._group_posts_by_category(posts)  # type: ignore[attr-defined]

        # Create category directory
        category_dir = self.site_config.output_dir / CATEGORY_DIR
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

            base_url = f"/{CATEGORY_DIR}/{safe_category}"
            # Each category's pages live inside category/{safe_category}/ directory.
            category_base_dir = category_dir / safe_category

            context = self._get_global_context()  # type: ignore[attr-defined]
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


### _listing.py ends here
