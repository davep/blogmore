"""Utility functions for blogmore."""


def normalize_site_url(site_url: str) -> str:
    """
    Normalize a site URL by removing trailing slashes.

    Args:
        site_url: The site URL to normalize

    Returns:
        The normalized site URL without trailing slash, or empty string if empty
    """
    return site_url.rstrip("/") if site_url else ""
