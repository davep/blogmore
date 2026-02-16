"""Utility functions for blogmore."""

import re


def calculate_reading_time(content: str, words_per_minute: int = 200) -> int:
    """
    Calculate the estimated reading time for content in whole minutes.

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
    # Remove code blocks (they typically take longer to read/understand)
    content = re.sub(r"```[\s\S]*?```", "", content)
    content = re.sub(r"`[^`]+`", "", content)

    # Remove markdown links but keep the text: [text](url) -> text
    content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", content)

    # Remove markdown images: ![alt](url) -> ""
    content = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", "", content)

    # Remove HTML tags
    content = re.sub(r"<[^>]+>", "", content)

    # Remove markdown formatting characters
    content = re.sub(r"[*_~`#-]", " ", content)

    # Count words (split by whitespace and filter out empty strings)
    words = [word for word in content.split() if word]
    word_count = len(words)

    # Calculate minutes, rounding to the nearest minute with a minimum of 1
    minutes = max(1, round(word_count / words_per_minute))

    return minutes


def normalize_site_url(site_url: str) -> str:
    """
    Normalize a site URL by removing trailing slashes.

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
