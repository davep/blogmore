"""Mixin providing paginated-listing generation for
[`SiteGenerator`][blogmore.generator.site.SiteGenerator].
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from blogmore.generator._date_archives import DateArchivesMixin
from blogmore.generator.constants import CATEGORY_DIR, TAG_DIR
from blogmore.generator.utils import paginate_posts
from blogmore.parser import Page, Post, post_sort_key, sanitize_for_url
from blogmore.renderer import TemplateRenderer
from blogmore.site_config import SiteConfig


class ListingMixin(DateArchivesMixin):
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

    site_config: SiteConfig
    renderer: TemplateRenderer
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

    def _generate_attribute_pages(
        self,
        posts_by_attr: dict[str, tuple[str, list[Post]]],
        pages: list[Page],
        attr_dir_name: str,
        posts_per_page: int,
        render_func: Callable[..., str],
        display_kwarg: str,
        safe_kwarg: str,
    ) -> None:
        """Helper to generate paginated listing pages for a grouped attribute.

        Args:
            posts_by_attr: Mapping of attribute slug to (display_name, posts).
            pages: List of static pages for the sidebar.
            attr_dir_name: Directory name for the attribute (e.g. ``"tag"``).
            posts_per_page: Maximum number of posts per page.
            render_func: Renderer method (e.g. ``self.renderer.render_tag_page``).
            display_kwarg: The kwarg name for the display name in *render_func*.
            safe_kwarg: The kwarg name for the sanitized slug in *render_func*.
        """
        attr_dir = self.site_config.output_dir / attr_dir_name
        attr_dir.mkdir(exist_ok=True)

        for attr_lower, (attr_display, attr_posts) in posts_by_attr.items():
            attr_posts.sort(key=post_sort_key, reverse=True)
            safe_attr = sanitize_for_url(attr_lower)
            base_url = f"/{attr_dir_name}/{safe_attr}"
            attr_base_dir = attr_dir / safe_attr
            context = self._get_global_context()  # type: ignore[attr-defined]
            context["pages"] = pages

            def _render(
                page_posts: list[Post],
                page_num: int,
                total_pages: int,
                _display: str = attr_display,
                _safe: str = safe_attr,
                _ctx: dict[str, Any] = context,
            ) -> str:
                kwargs = {
                    display_kwarg: _display,
                    safe_kwarg: _safe,
                    "posts": page_posts,
                    "page": page_num,
                    "total_pages": total_pages,
                }
                return render_func(**kwargs, **_ctx)

            self._generate_paginated_listing(
                attr_posts,
                base_url=base_url,
                output_dir=attr_base_dir,
                posts_per_page=posts_per_page,
                context=context,
                render_func=_render,
            )

    def _generate_attribute_overview_page(
        self,
        posts_by_attr: dict[str, tuple[str, list[Post]]],
        pages: list[Page],
        path_attr: str,
        render_func: Callable[..., str],
        context_kwarg: str,
        safe_attr_key: str,
        attr_lower_key: str,
    ) -> None:
        """Helper to generate a grouped attribute overview page (e.g. tags cloud).

        Args:
            posts_by_attr: Mapping of attribute slug to (display_name, posts).
            pages: List of static pages for the sidebar.
            path_attr: SiteConfig attribute name for the page path.
            render_func: Renderer method (e.g. ``self.renderer.render_tags_page``).
            context_kwarg: The kwarg name for the data list in *render_func*.
            safe_attr_key: Key name for the sanitized slug in the data dict.
            attr_lower_key: Key name for the lowercase attribute name in the data dict.
        """
        if not posts_by_attr:
            return

        attr_data: list[dict[str, Any]] = [
            {
                "display_name": attr_display,
                safe_attr_key: sanitize_for_url(attr_lower),
                "count": len(attr_posts),
                attr_lower_key: attr_lower,
            }
            for attr_lower, (attr_display, attr_posts) in posts_by_attr.items()
        ]

        # Sort alphabetically by display name
        attr_data.sort(key=lambda x: x["display_name"].lower())

        self._calculate_cloud_font_sizes(attr_data)  # type: ignore[attr-defined]

        # Render the page
        context = self._get_global_context()  # type: ignore[attr-defined]
        context["pages"] = pages
        kwargs = {context_kwarg: attr_data}
        self._generate_single_page(  # type: ignore[attr-defined]
            path_attr, render_func, context, **kwargs
        )

    def _generate_tag_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each tag with pagination.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
        # Group posts by tag (case-insensitive)
        # Key is lowercase tag, value is (display_name, posts)
        posts_by_tag = self._group_posts_by_tag(posts)  # type: ignore[attr-defined]

        self._generate_attribute_pages(
            posts_by_tag,
            pages,
            TAG_DIR,
            self.POSTS_PER_PAGE_TAG,
            self.renderer.render_tag_page,
            "tag",
            "safe_tag",
        )

    def _generate_tags_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the tags overview page with word cloud.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
        # Group posts by tag to get counts
        posts_by_tag = self._group_posts_by_tag(posts)  # type: ignore[attr-defined]

        self._generate_attribute_overview_page(
            posts_by_tag,
            pages,
            "tags_path",
            self.renderer.render_tags_page,
            "tags",
            "safe_tag",
            "tag_lower",
        )

    def _generate_categories_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the categories overview page with word cloud.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
        # Group posts by category to get counts
        posts_by_category = self._group_posts_by_category(posts)  # type: ignore[attr-defined]

        self._generate_attribute_overview_page(
            posts_by_category,
            pages,
            "categories_path",
            self.renderer.render_categories_page,
            "categories",
            "safe_category",
            "category_lower",
        )

    def _generate_category_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each category with pagination.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
        # Group posts by category (case-insensitive)
        # Key is lowercase category, value is (display_name, posts)
        posts_by_category = self._group_posts_by_category(posts)  # type: ignore[attr-defined]

        self._generate_attribute_pages(
            posts_by_category,
            pages,
            CATEGORY_DIR,
            self.POSTS_PER_PAGE_CATEGORY,
            self.renderer.render_category_page,
            "category",
            "safe_category",
        )


### _listing.py ends here
