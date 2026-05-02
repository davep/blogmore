"""Boilerplate for paginated listing pages (tags, categories, archives)."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from blogmore.generator.paths import (
    build_pagination_page_urls,
    get_pagination_output_path,
    pagination_prev_next,
)
from blogmore.generator.utils import paginate_posts
from blogmore.parser import Post
from blogmore.site_config import SiteConfig


def generate_paginated_listing(
    site_config: SiteConfig,
    post_list: list[Post],
    base_url: str,
    output_dir: Path,
    posts_per_page: int,
    context: dict[str, Any],
    render_func: Callable[[list[Post], int, int], str],
    write_html_func: Callable[[Path, str], None],
    canonical_url_func: Callable[[Path], str],
) -> None:
    """Paginate `post_list` and write one HTML file per page."""
    paginated_posts = paginate_posts(post_list, posts_per_page)
    total_pages = len(paginated_posts)
    page_urls = build_pagination_page_urls(site_config, base_url, total_pages)

    for page_num, page_posts in enumerate(paginated_posts, start=1):
        output_path = get_pagination_output_path(site_config, output_dir, page_num)
        context["canonical_url"] = canonical_url_func(output_path)
        prev_url, next_url = pagination_prev_next(page_num, page_urls)
        context["prev_page_url"] = prev_url
        context["next_page_url"] = next_url
        context["pagination_page_urls"] = page_urls
        html = render_func(page_posts, page_num, total_pages)
        write_html_func(output_path, html)
