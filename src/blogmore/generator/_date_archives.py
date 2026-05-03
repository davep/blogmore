"""Mixin providing date-based archive page generation for
[`SiteGenerator`][blogmore.generator.site.SiteGenerator].
"""

import datetime as dt
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from blogmore.parser import Page, Post
from blogmore.renderer import TemplateRenderer
from blogmore.site_config import SiteConfig


class DateArchivesMixin:
    """Mixin that generates year, month, and day archive pages with pagination.

    This mixin is intended to be composed into
    [`SiteGenerator`][blogmore.generator.site.SiteGenerator] via
    [`ListingMixin`][blogmore.generator._listing.ListingMixin].  It expects
    the host class to provide the following instance attributes:

    - `site_config` ([`SiteConfig`][blogmore.site_config.SiteConfig])
    - `renderer` ([`TemplateRenderer`][blogmore.renderer.TemplateRenderer])
    - `POSTS_PER_PAGE_ARCHIVE` (`int`)
    """

    site_config: SiteConfig
    renderer: TemplateRenderer
    POSTS_PER_PAGE_ARCHIVE: int

    def _generate_date_archive_level(
        self,
        posts_by_date: dict[Any, list[Post]],
        context: dict[str, Any],
        path_format: str,
        title_format: str,
        date_args_func: Callable[[Any], dict[str, Any]],
    ) -> None:
        """Helper to generate one level of date-based archives (year, month, or day).

        Args:
            posts_by_date: Mapping of date key (int or tuple) to posts.
            context: Shared template context dict.
            path_format: Format string for the URL path.
            title_format: Format string for the archive title.
            date_args_func: Callable that converts a date key to format kwargs.
        """
        for date_key, level_posts in posts_by_date.items():
            date_args = date_args_func(date_key)
            base_path = path_format.format(**date_args)
            output_dir = self.site_config.output_dir / base_path.lstrip("/")
            output_dir.mkdir(parents=True, exist_ok=True)
            archive_title = title_format.format(**date_args)

            def _render(
                page_posts: list[Post],
                page_num: int,
                total_pages: int,
                _title: str = archive_title,
                _base: str = base_path,
                _ctx: dict[str, Any] = context,
            ) -> str:
                return self.renderer.render_archive(
                    page_posts,
                    archive_title=f"Posts from {_title}",
                    page=page_num,
                    total_pages=total_pages,
                    base_path=_base,
                    **_ctx,
                )

            self._generate_paginated_listing(  # type: ignore[attr-defined]
                level_posts,
                base_url=base_path,
                output_dir=output_dir,
                posts_per_page=self.POSTS_PER_PAGE_ARCHIVE,
                context=context,
                render_func=_render,
            )

    def _generate_date_archives(self, posts: list[Post], pages: list[Page]) -> None:
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

        context = self._get_global_context()  # type: ignore[attr-defined]
        context["pages"] = pages

        # Generate year archives
        self._generate_date_archive_level(
            posts_by_year,
            context,
            path_format="/{year}",
            title_format="{year}",
            date_args_func=lambda y: {"year": y},
        )

        # Generate month archives
        self._generate_date_archive_level(
            posts_by_month,
            context,
            path_format="/{year}/{month:02d}",
            title_format="{month_name} {year}",
            date_args_func=lambda k: {
                "year": k[0],
                "month": k[1],
                "month_name": dt.datetime(k[0], k[1], 1).strftime("%B"),
            },
        )

        # Generate day archives
        self._generate_date_archive_level(
            posts_by_day,
            context,
            path_format="/{year}/{month:02d}/{day:02d}",
            title_format="{month_name} {day:02d}, {year}",
            date_args_func=lambda k: {
                "year": k[0],
                "month": k[1],
                "day": k[2],
                "month_name": dt.datetime(k[0], k[1], 1).strftime("%B"),
            },
        )


### _date_archives.py ends here
