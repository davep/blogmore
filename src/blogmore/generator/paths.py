"""Pagination, path-resolution and canonical-URL helpers for the site generator."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from blogmore.clean_url import make_url_clean
from blogmore.page_path import compute_page_output_path
from blogmore.pagination_path import resolve_pagination_page_path
from blogmore.post_path import compute_output_path

if TYPE_CHECKING:
    from blogmore.parser import Page, Post
    from blogmore.site_config import SiteConfig


def get_pagination_url(site_config: SiteConfig, base_url: str, page_num: int) -> str:
    """Compute the URL for a given pagination page.

    Joins *base_url* with the path resolved from the configured
    ``page_1_path`` or ``page_n_path`` template.  When ``clean_urls``
    is enabled and the resolved URL ends in ``index.html``, that
    suffix is stripped.

    Args:
        site_config: The site configuration.
        base_url: The URL prefix for the paginated section (e.g.
            ``/2024`` for a year archive).  May be an empty string
            for the main index.
        page_num: The 1-based page number.

    Returns:
        The fully-formed URL for the requested page.
    """
    if page_num == 1:
        relative = resolve_pagination_page_path(site_config.page_1_path, 1)
    else:
        relative = resolve_pagination_page_path(site_config.page_n_path, page_num)
    url = f"{base_url}/{relative}"
    # Collapse any double slashes introduced when base_url is empty.
    url = url.replace("//", "/")
    if site_config.clean_urls:
        url = make_url_clean(url)
    return url


def build_pagination_page_urls(
    site_config: SiteConfig, base_url: str, total_pages: int
) -> list[str]:
    """Build the full list of page URLs for a paginated section.

    Args:
        site_config: The site configuration.
        base_url: The URL prefix for the paginated section.
        total_pages: The total number of pages.

    Returns:
        A list of URLs, one per page, ordered from page 1 to
        *total_pages*.
    """
    return [
        get_pagination_url(site_config, base_url, page_num)
        for page_num in range(1, total_pages + 1)
    ]


def get_pagination_output_path(
    site_config: SiteConfig, base_dir: Path, page_num: int
) -> Path:
    """Compute the output file path for a given pagination page.

    Resolves the appropriate path template from the site configuration
    and joins it onto *base_dir*.  Any required parent directories are
    created automatically.

    Args:
        site_config: The site configuration.
        base_dir: The base directory for this paginated section.
        page_num: The 1-based page number.

    Returns:
        The absolute output file path for the given page.
    """
    if page_num == 1:
        relative = resolve_pagination_page_path(site_config.page_1_path, 1)
    else:
        relative = resolve_pagination_page_path(site_config.page_n_path, page_num)
    output_path = base_dir / relative
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def pagination_prev_next(
    page_num: int,
    page_urls: list[str],
) -> tuple[str | None, str | None]:
    """Return the previous and next page URLs for a paginated page.

    Args:
        page_num: The current page number (1-based).
        page_urls: Ordered list of all page URLs (index 0 = page 1).

    Returns:
        A tuple of ``(prev_url, next_url)`` where each element is
        ``None`` when there is no adjacent page.
    """
    prev_url: str | None = page_urls[page_num - 2] if page_num > 1 else None
    next_url: str | None = page_urls[page_num] if page_num < len(page_urls) else None
    return prev_url, next_url


def canonical_url_for_path(site_config: SiteConfig, output_path: Path) -> str:
    """Compute the fully-qualified canonical URL for a given output file path.

    When ``clean_urls`` is enabled, index filenames (e.g. ``index.html``)
    are stripped from the URL so the canonical URL ends with a trailing
    slash instead, matching the URLs advertised in the sitemap and
    elsewhere.

    Args:
        site_config: The site configuration.
        output_path: Absolute path to the output file within the output directory.

    Returns:
        The fully-qualified canonical URL for the given file.
    """
    relative = output_path.relative_to(site_config.output_dir)
    url = f"/{relative.as_posix()}"
    if site_config.clean_urls:
        url = make_url_clean(url)
    return f"{site_config.site_url}{url}"


def resolve_post_output_paths(
    site_config: SiteConfig, posts: list[Post]
) -> dict[int, Path]:
    """Resolve the output path for every post and detect path clashes.

    For each post the method:

    1. Computes the absolute output file path using the configured
       ``post_path`` template.
    2. Sets ``post.url_path`` so that templates and feeds always use the
       correct URL regardless of the configured format.
    3. Groups posts by output path and emits a prominent ``WARNING`` for
       any group that contains more than one post (i.e. a path clash).
       The *newest* post (first in the already-sorted list) wins; older
       posts that share the same path will be skipped during generation.

    Args:
        site_config: The site configuration.
        posts: All posts sorted by date, newest first.

    Returns:
        Mapping from ``id(post)`` to the post's resolved output path.
    """
    post_output_paths: dict[int, Path] = {}
    # Preserve insertion order so we can identify the winner easily.
    path_to_post_ids: dict[str, list[int]] = defaultdict(list)
    post_by_id: dict[int, Post] = {id(post): post for post in posts}

    for post in posts:
        output_path = compute_output_path(
            site_config.output_dir, post, site_config.post_path
        )
        post_output_paths[id(post)] = output_path

        # Set the post's URL so all templates/feeds reflect the configured scheme.
        relative = output_path.relative_to(site_config.output_dir)
        url_path = "/" + relative.as_posix()

        # Apply clean URL transformation: strip index filenames (e.g.
        # "index.html") from paths so the URL ends with a trailing slash.
        if site_config.clean_urls:
            url_path = make_url_clean(url_path)

        post.url_path = url_path

        path_to_post_ids[str(output_path)].append(id(post))

    # Detect and warn about path clashes.
    for path_str, clashing_ids in path_to_post_ids.items():
        if len(clashing_ids) > 1:
            clashing_posts = [post_by_id[pid] for pid in clashing_ids]
            winner = clashing_posts[0]  # newest (list is sorted newest-first)
            losers = clashing_posts[1:]
            print(
                "\nWARNING: Post path clash detected!  "
                "Multiple posts would be written to the same output file."
            )
            print(f"  Output path : {path_str}")
            print(f"  Winner (newest) : '{winner.title}'")
            for loser in losers:
                print(f"  Ignored (older): '{loser.title}'")
            print()

    return post_output_paths


def resolve_page_output_paths(
    site_config: SiteConfig, pages: list[Page]
) -> dict[int, Path]:
    """Resolve the output path for every static page.

    For each page the method:

    1. Computes the absolute output file path using the configured
       ``page_path`` template.
    2. Sets ``page.url_path`` so that templates always use the correct URL
       regardless of the configured format.

    Args:
        site_config: The site configuration.
        pages: All static pages to resolve paths for.

    Returns:
        Mapping from ``id(page)`` to the page's resolved output path.
    """
    page_output_paths: dict[int, Path] = {}

    for page in pages:
        output_path = compute_page_output_path(
            site_config.output_dir, page, site_config.page_path
        )
        page_output_paths[id(page)] = output_path

        # Set the page's URL so all templates reflect the configured scheme.
        relative = output_path.relative_to(site_config.output_dir)
        url_path = "/" + relative.as_posix()

        # Apply clean URL transformation: strip index filenames (e.g.
        # "index.html") from paths so the URL ends with a trailing slash.
        if site_config.clean_urls:
            url_path = make_url_clean(url_path)

        page.url_path = url_path

    return page_output_paths


def resolve_sidebar_pages(site_config: SiteConfig, pages: list[Page]) -> list[Page]:
    """Resolve which pages appear in the sidebar and in what order.

    When ``site_config.sidebar_pages`` is ``None`` or empty every page in
    ``pages`` is returned unchanged (the default behaviour).  When a list
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
