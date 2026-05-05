"""Paginated-listing generation for the site generator."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from blogmore.generator.constants import CATEGORY_DIR, TAG_DIR
from blogmore.generator.grouping import (
    calculate_cloud_font_sizes,
    group_posts_by_category,
    group_posts_by_tag,
)
from blogmore.generator.html import write_html
from blogmore.generator.paths import (
    build_pagination_page_urls,
    canonical_url_for_path,
    get_pagination_output_path,
    pagination_prev_next,
)
from blogmore.generator.utils import paginate_posts
from blogmore.parser import Page, Post, post_sort_key, sanitize_for_url

if TYPE_CHECKING:
    from blogmore.generator.context import ContextBuilder
    from blogmore.renderer import TemplateRenderer
    from blogmore.site_config import SiteConfig


class ListingGenerator:
    """Generates paginated listing pages for archives, tags, and categories."""

    POSTS_PER_PAGE_TAG: Final[int] = 10
    """The number of posts to show per page on tag listing pages."""
    POSTS_PER_PAGE_CATEGORY: Final[int] = 10
    """The number of posts to show per page on category listing pages."""
    POSTS_PER_PAGE_ARCHIVE: Final[int] = 10
    """The number of posts to show per page on date archive listing pages."""

    def __init__(
        self,
        site_config: SiteConfig,
        renderer: TemplateRenderer,
        context_builder: ContextBuilder,
    ) -> None:
        """Initialize the listing generator.

        Args:
            site_config: The site configuration.
            renderer: The template renderer.
            context_builder: The context builder.
        """
        self.site_config = site_config
        self.renderer = renderer
        self.context_builder = context_builder

    def generate_paginated_listing(
        self,
        post_list: list[Post],
        base_url: str,
        output_dir: Path,
        posts_per_page: int,
        context: dict[str, Any],
        render_func: Callable[[list[Post], int, int], str],
    ) -> None:
        """Paginate *post_list* and write one HTML file per page.

        Args:
            post_list: The posts to display, already in the desired order.
            base_url: The URL prefix for the section (e.g. ``"/tag/python"``).
            output_dir: The directory into which page files are written.
            posts_per_page: Maximum number of posts per page.
            context: The shared template context dict, mutated in-place for
                each page.
            render_func: Callable with signature
                ``(page_posts, page_num, total_pages) -> str`` that produces the
                HTML for one page.
        """
        paginated_posts = paginate_posts(post_list, posts_per_page)
        total_pages = len(paginated_posts)
        page_urls = build_pagination_page_urls(self.site_config, base_url, total_pages)

        for page_num, page_posts in enumerate(paginated_posts, start=1):
            output_path = get_pagination_output_path(
                self.site_config, output_dir, page_num
            )
            context["canonical_url"] = canonical_url_for_path(
                self.site_config, output_path
            )
            prev_url, next_url = pagination_prev_next(page_num, page_urls)
            context["prev_page_url"] = prev_url
            context["next_page_url"] = next_url
            context["pagination_page_urls"] = page_urls
            html = render_func(page_posts, page_num, total_pages)
            write_html(output_path, html, self.site_config.minify_html)

    def generate_date_archives(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate date-based archive pages (year, month, day) with pagination.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
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

        context = self.context_builder.get_global_context()
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
                _ctx: dict[str, Any] = context,
            ) -> str:
                return self.renderer.render_archive(
                    page_posts,
                    archive_title=f"Posts from {_year}",
                    page=page_num,
                    total_pages=total_pages,
                    base_path=_base,
                    **_ctx,
                )

            self.generate_paginated_listing(
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
                _ctx: dict[str, Any] = context,
            ) -> str:
                return self.renderer.render_archive(
                    page_posts,
                    archive_title=f"Posts from {_name}",
                    page=page_num,
                    total_pages=total_pages,
                    base_path=_base,
                    **_ctx,
                )

            self.generate_paginated_listing(
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
                _ctx: dict[str, Any] = context,
            ) -> str:
                return self.renderer.render_archive(
                    page_posts,
                    archive_title=f"Posts from {_date}",
                    page=page_num,
                    total_pages=total_pages,
                    base_path=_base,
                    **_ctx,
                )

            self.generate_paginated_listing(
                day_posts,
                base_url=base_path,
                output_dir=day_dir,
                posts_per_page=self.POSTS_PER_PAGE_ARCHIVE,
                context=context,
                render_func=_render_day,
            )

    def generate_tag_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each tag with pagination.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
        posts_by_tag = group_posts_by_tag(posts)

        tag_dir = self.site_config.output_dir / TAG_DIR
        tag_dir.mkdir(exist_ok=True)

        for tag_lower, (tag_display, tag_posts) in posts_by_tag.items():
            tag_posts.sort(key=post_sort_key, reverse=True)
            safe_tag = sanitize_for_url(tag_lower)
            base_url = f"/{TAG_DIR}/{safe_tag}"
            tag_base_dir = tag_dir / safe_tag

            context = self.context_builder.get_global_context()
            context["pages"] = pages

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

            self.generate_paginated_listing(
                tag_posts,
                base_url=base_url,
                output_dir=tag_base_dir,
                posts_per_page=self.POSTS_PER_PAGE_TAG,
                context=context,
                render_func=_render_tag,
            )

    def generate_tags_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the tags overview page with word cloud.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
        posts_by_tag = group_posts_by_tag(posts)

        if not posts_by_tag:
            return

        tag_data: list[dict[str, Any]] = [
            {
                "display_name": tag_display,
                "safe_tag": sanitize_for_url(tag_lower),
                "count": len(tag_posts),
                "tag_lower": tag_lower,
            }
            for tag_lower, (tag_display, tag_posts) in posts_by_tag.items()
        ]

        tag_data.sort(key=lambda x: x["display_name"].lower())
        calculate_cloud_font_sizes(tag_data)

        context = self.context_builder.get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.tags_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        tags_url = self.context_builder.get_tags_url()
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{tags_url}"
                if self.site_config.site_url
                else tags_url
            )
        else:
            context["canonical_url"] = canonical_url_for_path(
                self.site_config, output_path
            )

        html = self.renderer.render_tags_page(tag_data, **context)
        write_html(output_path, html, self.site_config.minify_html)

    def generate_categories_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the categories overview page with word cloud.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
        posts_by_category = group_posts_by_category(posts)

        if not posts_by_category:
            return

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

        category_data.sort(key=lambda x: x["display_name"].lower())
        calculate_cloud_font_sizes(category_data)

        context = self.context_builder.get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.categories_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        categories_url = self.context_builder.get_categories_url()
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{categories_url}"
                if self.site_config.site_url
                else categories_url
            )
        else:
            context["canonical_url"] = canonical_url_for_path(
                self.site_config, output_path
            )

        html = self.renderer.render_categories_page(category_data, **context)
        write_html(output_path, html, self.site_config.minify_html)

    def generate_category_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each category with pagination.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
        posts_by_category = group_posts_by_category(posts)

        category_dir = self.site_config.output_dir / CATEGORY_DIR
        category_dir.mkdir(exist_ok=True)

        for category_lower, (
            category_display,
            category_posts,
        ) in posts_by_category.items():
            category_posts.sort(key=post_sort_key, reverse=True)
            safe_category = sanitize_for_url(category_lower)
            base_url = f"/{CATEGORY_DIR}/{safe_category}"
            category_base_dir = category_dir / safe_category

            context = self.context_builder.get_global_context()
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

            self.generate_paginated_listing(
                category_posts,
                base_url=base_url,
                output_dir=category_base_dir,
                posts_per_page=self.POSTS_PER_PAGE_CATEGORY,
                context=context,
                render_func=_render_category,
            )
