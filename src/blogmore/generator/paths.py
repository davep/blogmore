"""Path and URL resolution for the site generator."""

from pathlib import Path

from blogmore.clean_url import make_url_clean
from blogmore.generator.utils import minified_filename
from blogmore.pagination_path import resolve_pagination_page_path
from blogmore.site_config import SiteConfig


def get_configured_url(site_config: SiteConfig, path_field_name: str) -> str:
    """Return the URL path for a configured page, derived from a config field.

    Strips any leading slash from the config value, prepends a fresh
    `/`, and optionally applies [`make_url_clean`][blogmore.clean_url.make_url_clean]
    when `clean_urls` is enabled.

    Args:
        site_config: The site configuration.
        path_field_name: The name of the [`SiteConfig`][blogmore.site_config.SiteConfig]
            attribute that holds the page path (e.g. `search_path`).

    Returns:
        The URL path for the configured page, always starting with `/`.
    """
    path: str = getattr(site_config, path_field_name)
    url = "/" + path.lstrip("/")
    if site_config.clean_urls:
        url = make_url_clean(url)
    return url


def with_cache_bust(url: str, token: str) -> str:
    """Return a URL with a cache-busting query parameter appended.

    External URLs (i.e. those that start with `http://` or `https://`)
    are returned unchanged.  Local URLs (starting with `/`) have
    `?v=<token>` appended so that browsers re-fetch them when the site is
    regenerated.  If no cache-busting token has been set (e.g. before
    [`generate()`][blogmore.generator.site.SiteGenerator.generate] is called) the URL is returned as-is.

    Args:
        url: The URL to process.
        token: The cache-busting token.

    Returns:
        The URL with a cache-busting query parameter appended, or the
        original URL if it is external or the token has not been set.
    """
    if not token or not url or url.startswith(("http://", "https://")):
        return url
    return f"{url}?v={token}"


def get_asset_url(
    regular: str,
    minify: bool,
    token: str,
    *,
    cache_bust: bool = True,
) -> str:
    """Build the `/static/` URL for one asset, choosing the minified variant when requested.

    When *minify* is `True` the minified filename is derived from
    *regular* via [`minified_filename`][blogmore.generator.utils.minified_filename].

    Args:
        regular: Filename for the non-minified asset (e.g. `style.css`).
        minify: When `True`, the minified filename is used.
        token: The cache-busting token.
        cache_bust: When `True` (the default), the URL is passed through
            [`with_cache_bust`][blogmore.generator.paths.with_cache_bust]
            so that browsers re-fetch the file after each build.

    Returns:
        The `/static/<filename>` URL, with an optional `?v=<token>`
        cache-busting query parameter.
    """
    name = minified_filename(regular) if minify else regular
    url = f"/static/{name}"
    return with_cache_bust(url, token) if cache_bust else url


def get_pagination_url(site_config: SiteConfig, base_url: str, page_num: int) -> str:
    """Compute the URL for a given pagination page.

    Joins *base_url* with the path resolved from the configured
    `page_1_path` or `page_n_path` template.  When `clean_urls`
    is enabled and the resolved URL ends in `index.html`, that
    suffix is stripped.

    Args:
        site_config: The site configuration.
        base_url: The URL prefix for the paginated section (e.g.
            `/2024` for a year archive).  May be an empty string
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
        A tuple of `(prev_url, next_url)` where each element is
        `None` when there is no adjacent page.
    """
    prev_url: str | None = page_urls[page_num - 2] if page_num > 1 else None
    next_url: str | None = page_urls[page_num] if page_num < len(page_urls) else None
    return prev_url, next_url


def canonical_url_for_path(site_config: SiteConfig, output_path: Path) -> str:
    """Compute the fully-qualified canonical URL for a given output file path.

    When `clean_urls` is enabled, index filenames (e.g. `index.html`)
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
