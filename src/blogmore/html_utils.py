"""HTML and URL utility functions for blogmore.

Provides helpers for parsing and manipulating HTML content and formatting URLs,
including word counting, reading time estimation, feed simplification, and
relative-to-absolute URL translation.
"""

from __future__ import annotations

import re

from blogmore.markdown.plain_text import html_to_plain_text


def count_words_from_html(html_content: str) -> int:
    """Count the number of words in the given HTML content.

    Strips HTML tags (excluding fenced code blocks, which are not readable
    prose) before splitting on whitespace.

    Args:
        html_content: The HTML content to analyse.

    Returns:
        The number of words in the content.

    Examples:
        >>> count_words_from_html("<p>Hello world</p>")
        2
        >>> count_words_from_html("<p>word </p>" * 10)
        10
    """
    return len(
        [
            word
            for word in re.findall(
                r"\w+", html_to_plain_text(html_content, exclude_code_blocks=True)
            )
            if word
        ]
    )


def calculate_reading_time_from_html(
    html_content: str, words_per_minute: int = 200
) -> int:
    """Calculate the estimated reading time for HTML content in whole minutes.

    Args:
        html_content: The HTML content to analyse.
        words_per_minute: Average reading speed (default: 200 WPM).

    Returns:
        Estimated reading time in whole minutes (minimum 1 minute).

    Examples:
        >>> calculate_reading_time_from_html("<p>Hello world</p>")
        1
        >>> calculate_reading_time_from_html("<p>word </p>" * 400)
        2
    """
    return max(1, round(count_words_from_html(html_content) / words_per_minute))


def make_urls_absolute(html_content: str, base_url: str) -> str:
    """Rewrite root-relative URLs in HTML content to absolute URLs.

    Converts `src` and `href` attributes whose values begin with `/`
    to full absolute URLs by prepending `base_url`.  Attributes that already
    contain an absolute URL (i.e. they include a scheme such as `https://`)
    are left unchanged.

    Args:
        html_content: HTML string that may contain root-relative URL references.
        base_url: The absolute base URL to prepend (e.g. `https://example.com`).
            Any trailing slash is ignored because root-relative paths already
            start with `/`.

    Returns:
        HTML string with root-relative `src`/`href` values replaced by
        absolute URLs.

    Examples:
        >>> make_urls_absolute('<img src="/img/photo.jpg">', "https://example.com")
        '<img src="https://example.com/img/photo.jpg">'
        >>> make_urls_absolute('<a href="/about.html">About</a>', "https://example.com")
        '<a href="https://example.com/about.html">About</a>'
    """
    stripped = base_url.rstrip("/")

    def _replace(match: re.Match[str]) -> str:
        attr, quote, path = match.group(1), match.group(2), match.group(3)
        return f"{attr}={quote}{stripped}{path}{quote}"

    return re.sub(
        r'(src|href)=(["\'])(/[^"\']*)\2',
        _replace,
        html_content,
    )


def normalize_site_url(site_url: str) -> str:
    """Normalize a site URL by removing trailing slashes.

    This function ensures consistent URL handling by stripping trailing slashes
    from site URLs. This prevents double slashes in generated URLs when paths
    are concatenated with the site URL.

    Edge cases:
    - Empty string: Returns empty string (allows fallback URL to be used)
    - Single slash: Returns empty string (treated as equivalent to empty)
    - Multiple trailing slashes: All are removed

    Args:
        site_url: The site URL to normalize.

    Returns:
        The normalized site URL without trailing slash, or empty string if empty.

    Examples:
        >>> normalize_site_url("https://example.com/")
        "https://example.com"
        >>> normalize_site_url("https://example.com")
        "https://example.com"
        >>> normalize_site_url("")
        ""
        >>> normalize_site_url("/")
        ""
    """
    return site_url.rstrip("/") if site_url else ""


def remove_heading_anchors(html_content: str) -> str:
    """Remove heading anchor elements from HTML content.

    This function locates anchor tags with the `heading-anchor` class
    (e.g., `<a class="heading-anchor" ...>¶</a>`) and removes them entirely.
    Any legitimate copy of the `¶` character that is not inside a heading anchor
    element will not be touched.

    Args:
        html_content: The HTML content to process.

    Returns:
        HTML string with heading anchor elements removed.
    """
    return re.sub(
        r'<a\b[^>]*\bclass=["\']heading-anchor["\'][^>]*>.*?</a>',
        "",
        html_content,
        flags=re.DOTALL,
    )


def simplify_html_for_feeds(html_content: str) -> str:
    """Simplify HTML content for better compatibility with RSS/Atom feed readers.

    Currently performs the following transformations:
    - Replaces `<picture>` elements with their nested `<img>` fallback tags,
      ensuring that images display correctly in readers that don't support
      the modern `<picture>` element.
    - Removes heading anchor elements to prevent the anchor symbol from appearing
      in the feed content.

    Args:
        html_content: The HTML content to simplify.

    Returns:
        Simplified HTML string.
    """
    # Replace <picture>...</picture> with just the nested <img> tag.
    # We look for <img ...> inside the picture tags and capture it.
    # The [^>]*? ensures we handle multi-line tags or attributes correctly.
    simplified = re.sub(
        r"<picture\b[^>]*>.*?(<img\b[^>]*>).*?</picture>",
        r"\1",
        html_content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return remove_heading_anchors(simplified)
