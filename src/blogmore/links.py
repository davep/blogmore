"""Functionality for managing and analyzing external links in blog posts."""

import csv
import re
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

from blogmore import __version__
from blogmore.console import print_error, print_warning
from blogmore.markdown.external_links import is_external_link
from blogmore.parser import Post

# Compiled regular expression for extracting href attributes from anchor tags.
_LINK_RE: re.Pattern[str] = re.compile(r'<a\s+(?:[^>]*?\s+)?href=["\']([^"\']*)["\']')

_GET_CHECK_BYTE_LIMIT: int = 1024
"""The number of bytes to request and read when checking a link via GET.

A value of 1024 bytes (1 KiB) is chosen because it fits within a single TCP
packet (typical MSS is ~1.4 KiB), avoiding extra network packets while
ensuring we consume enough of the response buffer to allow the socket to close
cleanly. It also acts as a safety limit if a server ignores the Range header
and attempts to send a large file.
"""


class RateLimitedError(Exception):
    """Raised when a request returns HTTP 429 Too Many Requests."""

    def __init__(self, url: str) -> None:
        """Initialize the error.

        Args:
            url: The URL that was rate limited.
        """
        super().__init__(f"HTTP 429 Too Many Requests for {url}")
        self.url = url


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
        links = _LINK_RE.findall(post.html_content)
        seen_links = set()
        for href in links:
            if is_external_link(href, site_domain) and href not in seen_links:
                seen_links.add(href)
                writer.writerow([href, str(post.path)])


def should_ignore_link(link: str, ignore_list: list[str]) -> bool:
    """Determine if an external link should be ignored.

    Args:
        link: The link to check.
        ignore_list: List of ignored bare domains or URL prefixes.

    Returns:
        True if the link should be ignored, False otherwise.
    """
    for item in ignore_list:
        if "://" in item:
            # URL prefix check
            if (
                link == item
                or link.startswith(item + "/")
                or link.startswith(item + "?")
                or link.startswith(item + "#")
            ):
                return True
        else:
            # Bare domain check
            try:
                parsed = urlparse(link)
                netloc = parsed.netloc.lower()
                if ":" in netloc:
                    netloc = netloc.split(":")[0]
                ignore_domain = item.lower()
                if netloc == ignore_domain or netloc.endswith(f".{ignore_domain}"):
                    return True
            except Exception:
                pass
    return False


def _check_single_link_get(url: str, user_agent: str, timeout: float) -> str | None:
    """Check a link using GET with a small range of bytes.

    Args:
        url: The URL to check.
        user_agent: The User-Agent header value.
        timeout: Network timeout in seconds.

    Returns:
        None if the link is working, or a string describing the error if broken.

    Raises:
        RateLimitedError: If the server returns HTTP 429.
    """
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", user_agent)
    req.add_header("Range", f"bytes=0-{_GET_CHECK_BYTE_LIMIT}")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            if 200 <= status < 400:
                # Read a small amount of bytes, then close (which urlopen's context manager does automatically)
                response.read(_GET_CHECK_BYTE_LIMIT)
                return None
            return f"HTTP {status} (GET)"
    except urllib.error.HTTPError as e:
        status = e.code
        if status == 429:
            raise RateLimitedError(url) from e
        return f"HTTP {status}: {e.reason} (GET)"
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if "timed out" in reason.lower() or "timeout" in reason.lower():
            return "Connection timed out (GET)"
        return f"Network error: {reason} (GET)"
    except TimeoutError:
        return "Connection timed out (GET)"
    except Exception as e:
        return f"Unexpected error: {str(e)} (GET)"


def _check_single_link(url: str, user_agent: str, timeout: float) -> str | None:
    """Check a link using HEAD, falling back to GET if 403 or 405.

    Args:
        url: The URL to check.
        user_agent: The User-Agent header value.
        timeout: Network timeout in seconds.

    Returns:
        None if the link is working, or a string describing the error if broken.

    Raises:
        RateLimitedError: If the server returns HTTP 429.
    """
    req = urllib.request.Request(url, method="HEAD")
    req.add_header("User-Agent", user_agent)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            if 200 <= status < 400:
                return None
            return f"HTTP {status}"
    except urllib.error.HTTPError as e:
        status = e.code
        if status in (403, 405):
            return _check_single_link_get(url, user_agent, timeout)
        if status == 429:
            raise RateLimitedError(url) from e
        return f"HTTP {status}: {e.reason}"
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if "timed out" in reason.lower() or "timeout" in reason.lower():
            return "Connection timed out"
        return f"Network error: {reason}"
    except TimeoutError:
        return "Connection timed out"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def check_external_links(
    posts: list[Post],
    site_url: str | None = None,
    ignore_list: list[str] | None = None,
    delay: float = 0.0,
    timeout: float = 5.0,
    verbose: bool = False,
) -> int:
    """Check all external links found in posts.

    Args:
        posts: The list of posts to check.
        site_url: The site URL to filter out internal links.
        ignore_list: Optional list of bare domains or URL prefixes to ignore.
        delay: Delay in seconds between checking each link.
        timeout: Network timeout in seconds for link validation.
        verbose: If True, print successfully resolved links as well.

    Returns:
        0 if all links are OK, or 1 if any broken links are found.
    """
    site_domain: str | None = None
    if site_url:
        parsed = urlparse(site_url)
        site_domain = parsed.netloc.lower()

    user_agent = f"BlogMore v{__version__} (https://blogmore.davep.dev/)"

    # Cache of check results: Map from link to error message (or None if working)
    cache: dict[str, str | None] = {}
    # Domains that have rate limited us (HTTP 429)
    off_limits_domains: set[str] = set()
    broken_links_found = False

    try:
        for post in posts:
            # Extract <a> hrefs
            links = _LINK_RE.findall(post.html_content)

            for href in links:
                if not is_external_link(href, site_domain):
                    continue

                if should_ignore_link(href, ignore_list or []):
                    continue

                # Parse domain for 429 tracking
                try:
                    parsed_href = urlparse(href)
                    domain = parsed_href.netloc.lower()
                    if ":" in domain:
                        domain = domain.split(":")[0]
                except Exception:
                    domain = ""

                # If domain is off-limits due to 429, skip it
                if domain in off_limits_domains:
                    continue

                # If we already checked this link in this session, reuse the result
                if href in cache:
                    error = cache[href]
                    if error is not None:
                        print(f"{post.path}: {href} - {error}")
                        broken_links_found = True
                    elif verbose:
                        print(f"{post.path}: {href} - OK")
                    continue

                # Introduce delay if requested
                if delay > 0.0:
                    time.sleep(delay)

                # Check the link
                try:
                    error = _check_single_link(href, user_agent, timeout)
                    cache[href] = error
                    if error is not None:
                        print(f"{post.path}: {href} - {error}")
                        broken_links_found = True
                    elif verbose:
                        print(f"{post.path}: {href} - OK")
                except RateLimitedError:
                    print_warning(
                        f"Domain {domain} is now off limits (received HTTP 429 Too Many Requests)"
                    )
                    off_limits_domains.add(domain)
                    cache[href] = "HTTP 429 Too Many Requests"
                    print(f"{post.path}: {href} - HTTP 429 Too Many Requests")
                    broken_links_found = True
    except KeyboardInterrupt:
        print_error("\nLink checking interrupted by user. Exiting.")
        return 1

    return 1 if broken_links_found else 0
