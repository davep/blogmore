"""Back-linking system for BlogMore.

Calculates which posts link to other posts, providing data for a
"References & mentions" section displayed on individual post pages.

This module is only consulted when `with_backlinks` is enabled in the
site configuration.  When the feature is disabled none of these functions
are called, so users pay no cost for a feature they do not use.
"""

##############################################################################
# Python imports.
import re
from dataclasses import dataclass

##############################################################################
# Third-party imports.
from markupsafe import Markup

##############################################################################
# Local imports.
from blogmore.markdown.plain_text import html_to_plain_text
from blogmore.parser import Post

##############################################################################
# Number of plain-text characters to include on each side of a link in
# a rendered snippet.
_SNIPPET_CONTEXT_CHARS: int = 100

##############################################################################
# Distinctive marker prefix used to locate link positions within the
# full-document plain-text conversion.
_BACKLINK_MARKER_PREFIX: str = "BKLINK8f3a2b19_"

##############################################################################
# Compiled regular expression for HTML link detection.
# Matches <a href="...">text</a>, capturing the URL and the link text.
# The href attribute can be in any position within the opening tag and
# can use either single or double quotes.
_HTML_LINK_RE: re.Pattern[str] = re.compile(
    r'<a\s+(?:[^>]*?\s+)?href=(["\'])(.*?)\1[^>]*?>(.*?)</a>', re.DOTALL
)


@dataclass
class Backlink:
    """A back-link reference from one post to another.

    Attributes:
        source_post: The post whose content contains the link.
        snippet: HTML-safe excerpt from the source post surrounding the
            link, with up to `_SNIPPET_CONTEXT_CHARS` characters of
            context on each side and an ellipsis (``…``) where the
            excerpt is truncated.  The link text itself is wrapped in a
            ``<strong class="backlink-link-text">`` element so it
            stands out from the surrounding context.
    """

    source_post: Post
    snippet: Markup


def _extract_snippets(
    html_content: str,
    link_data: list[tuple[int, int, str, Post]],
) -> list[tuple[Post, Markup]]:
    """Extract HTML-safe snippets for multiple links in one pass.

    Args:
        html_content: The rendered HTML content of the post.
        link_data: List of (match_start, match_end, link_html, target_post) tuples.

    Returns:
        List of (target_post, snippet_markup) tuples.
    """
    if not link_data:
        return []

    # Sort links by start position in reverse to avoid shifting indices while inserting markers
    sorted_links = sorted(link_data, key=lambda x: x[0], reverse=True)

    # Insert unique markers for each link into the HTML
    marked_html = html_content
    for i, (start, end, _, _) in enumerate(sorted_links):
        marker = f"{_BACKLINK_MARKER_PREFIX}{i}_"
        marked_html = marked_html[:start] + marker + marked_html[end:]

    # Pre-calculate the plain-text representation of every link's text.
    # We use html_to_plain_text to strip any tags (like <em> or <code>)
    # from the link text.
    plain_link_texts = [
        html_to_plain_text(lt) if lt else "" for _, _, lt, _ in sorted_links
    ]

    # Convert the entire marked document to plain text in one pass.
    # This strips all remaining HTML tags while preserving our markers.
    plain_full = html_to_plain_text(marked_html)

    # Locate the spans of all markers in the plain text. We will use these
    # to "snap" the context window boundaries so that we never extract
    # a partial marker.
    marker_pattern = re.escape(_BACKLINK_MARKER_PREFIX) + r"\d+_"
    marker_spans = [m.span() for m in re.finditer(marker_pattern, plain_full)]

    results: list[tuple[Post, Markup]] = []
    # Process links in original sorted order (which corresponds to markers 0, 1, 2...)
    for i, (_, _, _, target_post) in enumerate(sorted_links):
        marker = f"{_BACKLINK_MARKER_PREFIX}{i}_"
        marker_pos = plain_full.find(marker)
        if marker_pos == -1:
            continue

        marker_end_pos = marker_pos + len(marker)
        context_start = max(0, marker_pos - _SNIPPET_CONTEXT_CHARS)
        context_end = min(len(plain_full), marker_end_pos + _SNIPPET_CONTEXT_CHARS)

        # Snap boundaries to avoid cutting through any marker.
        for ms_start, ms_end in marker_spans:
            if ms_start < context_start < ms_end:
                # context_start is inside a marker; snap to the end of it
                # to exclude the partial marker from the snippet.
                context_start = ms_end
            if ms_start < context_end < ms_end:
                # context_end is inside a marker; snap to the start of it
                # to exclude the partial marker from the snippet.
                context_end = ms_start

        excerpt = plain_full[context_start:context_end]

        prefix = "…" if context_start > 0 else ""
        suffix = "…" if context_end < len(plain_full) else ""

        # HTML-escape the whole plain-text snippet.
        escaped: Markup = Markup.escape(f"{prefix}{excerpt}{suffix}")

        # 1. Replace the "main" marker (the one for this backlink) with the
        # highlighted link text.
        plain_link_text = plain_link_texts[i]
        if plain_link_text:
            escaped_link_text = Markup.escape(plain_link_text)
            highlighted = Markup(
                f'<strong class="backlink-link-text">{escaped_link_text}</strong>'
            )
            escaped = Markup(escaped.replace(marker, highlighted, 1))
        else:
            escaped = Markup(escaped.replace(marker, Markup(""), 1))

        # 2. Replace any other markers that fell into this excerpt window
        # with their plain-text link text.
        def _replace_secondary(match: re.Match[str]) -> str:
            other_index = int(match.group(1))
            return str(Markup.escape(plain_link_texts[other_index]))

        secondary_pattern = re.escape(_BACKLINK_MARKER_PREFIX) + r"(\d+)_"
        escaped = Markup(re.sub(secondary_pattern, _replace_secondary, str(escaped)))

        results.append((target_post, escaped))

    return results


def _find_links(html_content: str) -> list[tuple[str, int, int, str]]:
    """Find all hyperlinks in rendered HTML content.

    Args:
        html_content: Rendered HTML content to scan.

    Returns:
        A list of ``(url, match_start, match_end, link_text)`` tuples.
        *match_start* and *match_end* are the character positions of the
        full ``<a>`` tag syntax within *html_content*; *link_text* is the
        HTML content of the link.
    """
    results: list[tuple[str, int, int, str]] = []

    for match in _HTML_LINK_RE.finditer(html_content):
        url = match.group(2).strip()
        if url:
            results.append((url, match.start(), match.end(), match.group(3)))

    return results


def _normalize_url_path(url: str) -> str:
    """Normalise a URL path for comparison by removing `index.html`, `.html`, and trailing slashes.

    Produces a canonical form that can be compared regardless of whether
    `clean_urls` is enabled or which URL format the author used in a link.

    Args:
        url: URL path to normalise (should start with ``/``).

    Returns:
        The normalised path without a trailing slash, `.html` extension,
        or `index.html` suffix.
    """
    url = url.rstrip("/")
    if url.endswith("/index.html"):
        url = url[: -len("/index.html")]
    elif url.endswith(".html"):
        url = url[: -len(".html")]
    return url


def _to_path(url: str, site_url: str) -> str | None:
    """Convert a link URL to a root-relative path.

    Handles absolute paths (``/path``), full URLs (``https://example.com/path``),
    and rejects genuinely external links or non-HTTP schemes.  Fragment-only
    links (``#section``) and relative links (``../path``) are also rejected.

    Args:
        url: The raw URL from an HTML link.
        site_url: The site's base URL (e.g. ``https://example.com``), used
            to strip the domain from full URLs that point back to this site.

    Returns:
        The root-relative path (starting with `/`) if the URL points to
        this site, or `None` otherwise.
    """
    url = url.strip()
    if not url or url.startswith("#"):
        return None

    # Strip fragment and query string before any other processing.
    url = url.split("#")[0].split("?")[0]
    if not url:
        return None

    # Already a root-relative path.
    if url.startswith("/"):
        return url

    # Full URL — only accept if it points back to this site.
    if "://" in url:
        if site_url:
            # Normalise both sides: strip trailing slash.
            stripped_site = site_url.rstrip("/")
            if url.startswith(stripped_site + "/") or url == stripped_site:
                return "/" + url[len(stripped_site) :].lstrip("/")
        return None

    # Relative path (e.g. ../2024/…) — skip; too ambiguous to resolve safely.
    return None


def build_backlink_map(
    posts: list[Post],
    site_url: str = "",
) -> dict[str, list[Backlink]]:
    """Build a mapping from post URL to the list of posts that link to it.

    Scans the rendered HTML content of every post for internal links and
    records which posts link to which other posts.  Self-links are ignored.
    Links that resolve to pages (as opposed to posts) are automatically
    excluded because the mapping is built solely from `posts`.

    The work to build this map is proportional to the total number of links
    in all posts.  It is only called when `with_backlinks` is enabled in
    the site configuration.

    Args:
        posts: All posts for the site, sorted by date (newest first).
        site_url: The site's base URL (e.g. ``https://example.com``).
            Used to recognise full URLs that point back to this site.

    Returns:
        A dictionary mapping each post's URL to a (possibly empty) list
        of [`blogmore.backlinks.Backlink`][blogmore.backlinks.Backlink] objects representing other posts that link
        to it.  Every post in *posts* has an entry in the returned dict,
        even if it has no inbound links.
    """
    # Build a normalised-URL → Post mapping so we can look up targets quickly.
    normalized_to_post: dict[str, Post] = {}
    for post in posts:
        normalized_to_post[_normalize_url_path(post.url)] = post

    # Initialise a list for every post (even those with no backlinks).
    backlinks: dict[str, list[Backlink]] = {post.url: [] for post in posts}

    for source_post in posts:
        internal_links: list[tuple[int, int, str, Post]] = []
        for raw_url, match_start, match_end, link_text in _find_links(
            source_post.html_content
        ):
            path = _to_path(raw_url, site_url)
            if path is None:
                continue
            normalized = _normalize_url_path(path)
            target_post = normalized_to_post.get(normalized)
            if target_post is None or target_post is source_post:
                continue
            internal_links.append((match_start, match_end, link_text, target_post))

        if internal_links:
            for target_post, snippet in _extract_snippets(
                source_post.html_content, internal_links
            ):
                backlinks[target_post.url].append(
                    Backlink(source_post=source_post, snippet=snippet)
                )

    return backlinks


### backlinks.py ends here
