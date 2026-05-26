"""Functionality for managing and analyzing external links in blog posts."""

import csv
import re
import sys
from urllib.parse import urlparse

from blogmore.markdown.external_links import is_external_link
from blogmore.parser import Post


def dump_external_links(posts: list[Post], site_url: str | None = None) -> None:
    """Dump all external links found in posts to stdout in CSV format.

    Args:
        posts: The list of posts to scan.
        site_url: The site URL to filter out internal links.
    """
    site_domain: str | None = None
    if site_url:
        parsed = urlparse(site_url)
        site_domain = parsed.netloc.lower()

    writer = csv.writer(sys.stdout)

    for post in posts:
        # Extract <a> hrefs
        links = re.findall(
            r'<a\s+(?:[^>]*?\s+)?href=["\']([^"\']*)["\']', post.html_content
        )
        seen_links = set()
        for href in links:
            if is_external_link(href, site_domain) and href not in seen_links:
                seen_links.add(href)
                writer.writerow([href, str(post.path)])
