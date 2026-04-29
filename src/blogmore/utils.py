"""Utility functions for blogmore."""

import re


def _strip_markdown_formatting(content: str) -> str:
    """Strip Markdown and HTML formatting from *content*, returning plain text.

    Removes fenced and inline code blocks, Markdown links and images, HTML
    tags, and common Markdown emphasis characters so that the result contains
    only prose words.

    Args:
        content: Raw Markdown or HTML text to strip.

    Returns:
        The input with all Markdown and HTML formatting removed.
    """
    content = re.sub(r"```[\s\S]*?```", "", content)
    content = re.sub(r"`[^`]+`", "", content)
    content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", content)
    content = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", "", content)
    content = re.sub(r"<[^>]+>", "", content)
    return re.sub(r"[*_~`#-]", " ", content)


def count_words(content: str) -> int:
    """Count the number of words in the given content.

    Strips common Markdown and HTML formatting before counting so that only
    prose words are included.  The same normalisation rules as
    :func:`calculate_reading_time` are applied.

    Args:
        content: The text content to analyse (may include Markdown/HTML).

    Returns:
        The number of words in the content.

    Examples:
        >>> count_words("Hello world")
        2
        >>> count_words("word " * 10)
        10
    """
    return len([word for word in _strip_markdown_formatting(content).split() if word])


def calculate_reading_time(content: str, words_per_minute: int = 200) -> int:
    """Calculate the estimated reading time for content in whole minutes.

    Uses the standard reading speed of 200 words per minute. Strips markdown
    formatting and counts only actual words to provide an accurate estimate.

    Args:
        content: The text content to analyze (can include markdown)
        words_per_minute: Average reading speed (default: 200 WPM)

    Returns:
        Estimated reading time in whole minutes (minimum 1 minute)

    Examples:
        >>> calculate_reading_time("Hello world")
        1
        >>> calculate_reading_time("word " * 400)
        2
    """
    words = [word for word in _strip_markdown_formatting(content).split() if word]
    return max(1, round(len(words) / words_per_minute))


def make_urls_absolute(html_content: str, base_url: str) -> str:
    """Rewrite root-relative URLs in HTML content to absolute URLs.

    Converts ``src`` and ``href`` attributes whose values begin with ``/``
    to full absolute URLs by prepending *base_url*.  Attributes that already
    contain an absolute URL (i.e. they include a scheme such as ``https://``)
    are left unchanged.

    Args:
        html_content: HTML string that may contain root-relative URL references.
        base_url: The absolute base URL to prepend (e.g. ``https://example.com``).
            Any trailing slash is ignored because root-relative paths already
            start with ``/``.

    Returns:
        HTML string with root-relative ``src``/``href`` values replaced by
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
        site_url: The site URL to normalize

    Returns:
        The normalized site URL without trailing slash, or empty string if empty

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
