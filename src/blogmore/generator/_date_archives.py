"""Mixin providing date-based archive page generation for
[`SiteGenerator`][blogmore.generator.site.SiteGenerator].
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from blogmore.parser import Page, Post
from blogmore.renderer import TemplateRenderer
from blogmore.site_config import SiteConfig

if TYPE_CHECKING:
    from blogmore.generator._protocol import GeneratorProtocol


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

    def _generate_date_archives(
        self: GeneratorProtocol, posts: list[Post], pages: list[Page]
    ) -> None:
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

            self._generate_paginated_listing(
                day_posts,
                base_url=base_path,
                output_dir=day_dir,
                posts_per_page=self.POSTS_PER_PAGE_ARCHIVE,
                context=context,
                render_func=_render_day,
            )


### _date_archives.py ends here
