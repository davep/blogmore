"""Utility functions for blogmore."""

import re

from blogmore.markdown.plain_text import markdown_to_plain_text


def strip_markdown(content: str) -> str:
    """Remove common Markdown and HTML formatting from content.

    Args:
        content: The text content to clean up.

    Returns:
        The cleaned text with formatting removed.

    Note:
        This is *not* a full Markdown to plain text converter. It handles
        common formatting characters and structures, but may not cover all
        edge cases or extensions. The main goal is to remove formatting
        characters that would interfere with things like word counting,
        while preserving the actual text content.
    """
    # Remove code blocks
    content = re.sub(r"```[\s\S]*?```", "", content)
    # Remove markdown images: ![alt](url) -> ""
    content = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", "", content)
    # Remove markdown links but keep the text: [text](url) -> text
    content = re.sub(r"\[([^\]]*)\]\([^\)]+\)", r"\1", content)
    # Remove HTML tags
    content = re.sub(r"<[^>]+>", "", content)
    # Remove markdown formatting characters
    content = re.sub(r"[*_~`#-]", " ", content)
    # Collapse multiple spaces into one.
    return re.sub(r"\s+", " ", content).strip()


def count_words(content: str) -> int:
    """Count the number of words in the given content.

    Converts the Markdown content to plain text using the proper Markdown
    parser (excluding fenced code blocks, which are not readable prose)
    before splitting on whitespace.

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
    return len(
        [
            word
            for word in markdown_to_plain_text(
                content, exclude_code_blocks=True
            ).split()
            if word
        ]
    )


def calculate_reading_time(content: str, words_per_minute: int = 200) -> int:
    """Calculate the estimated reading time for content in whole minutes.

    Args:
        content: The text content to analyse (can include markdown)
        words_per_minute: Average reading speed (default: 200 WPM)

    Returns:
        Estimated reading time in whole minutes (minimum 1 minute).

    Examples:
        >>> calculate_reading_time("Hello world")
        1
        >>> calculate_reading_time("word " * 400)
        2
    """
    return max(1, round(count_words(content) / words_per_minute))


def make_urls_absolute(html_content: str, base_url: str) -> str:
    """Rewrite root-relative URLs in HTML content to absolute URLs.

    Converts `src` and `href` attributes whose values begin with `/`
    to full absolute URLs by prepending *base_url*.  Attributes that already
    contain an absolute URL (i.e. they include a scheme such as `https://`)
    are left unchanged.

    Args:
        html_content: HTML string that may contain root-relative URL references.
        base_url: The absolute base URL to prepend (e.g. ``https://example.com``).
            Any trailing slash is ignored because root-relative paths already
            start with ``/``.

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


### utils.py ends here
