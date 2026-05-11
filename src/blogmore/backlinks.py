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
from blogmore.markdown.plain_text import markdown_to_plain_text
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
# Compiled regular expressions for Markdown link detection.

# Inline links: [link text](url) or [link text](url "optional title")
# The URL portion allows one level of balanced parentheses so that paths such
# as /2016/11/15/seen_by_davep_(the_return).html are captured in full.
# The atomic group (?>...) prevents catastrophic backtracking when the regex
# engine encounters a long run of characters without a matching closing ")"
# (Python 3.11+ feature; this codebase targets 3.12+).
_INLINE_LINK_RE: re.Pattern[str] = re.compile(
    r"\[([^\]]*)\]\(((?>[^()]+|\([^()]*\))*)\)"
)

# Reference-style link definitions: [id]: url  (at the start of any line)
_LINK_DEF_RE: re.Pattern[str] = re.compile(r"^\[([^\]]+)\]:\s+(\S+)", re.MULTILINE)

# Reference-style links: [text][ref] or [text][] (implicit ref = text)
_REF_LINK_RE: re.Pattern[str] = re.compile(r"\[([^\]]+)\]\[([^\]]*)\]")


@dataclass
class Backlink:
    """A back-link reference from one post to another.

    Attributes:
        source_post: The post whose Markdown content contains the link.
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
    content: str,
    link_data: list[tuple[int, int, str, Post]],
) -> list[tuple[Post, Markup]]:
    """Extract HTML-safe snippets for multiple links in one pass.

    Args:
        content: The raw Markdown source of the post.
        link_data: List of (match_start, match_end, link_text, target_post) tuples.

    Returns:
        List of (target_post, snippet_markup) tuples.
    """
    if not link_data:
        return []

    # Sort links by start position in reverse to avoid shifting indices while inserting markers
    sorted_links = sorted(link_data, key=lambda x: x[0], reverse=True)

    # Insert unique markers for each link
    marked_content = content
    for i, (start, end, _, _) in enumerate(sorted_links):
        marker = f"{_BACKLINK_MARKER_PREFIX}{i}_"
        marked_content = marked_content[:start] + marker + marked_content[end:]

    # Convert the entire marked document to plain text in one pass
    plain_full = markdown_to_plain_text(marked_content)

    results: list[tuple[Post, Markup]] = []
    # Process links in original sorted order (which corresponds to markers 0, 1, 2...)
    for i, (_, _, link_text, target_post) in enumerate(sorted_links):
        marker = f"{_BACKLINK_MARKER_PREFIX}{i}_"
        marker_pos = plain_full.find(marker)
        if marker_pos == -1:
            continue

        marker_end_pos = marker_pos + len(marker)
        context_start = max(0, marker_pos - _SNIPPET_CONTEXT_CHARS)
        context_end = min(len(plain_full), marker_end_pos + _SNIPPET_CONTEXT_CHARS)
        excerpt = plain_full[context_start:context_end]

        prefix = "…" if context_start > 0 else ""
        suffix = "…" if context_end < len(plain_full) else ""

        # HTML-escape the whole plain-text snippet.
        escaped: Markup = Markup.escape(f"{prefix}{excerpt}{suffix}")

        # Replace the marker with the highlighted link text.
        plain_link_text = markdown_to_plain_text(link_text) if link_text else ""
        if plain_link_text:
            escaped_link_text = Markup.escape(plain_link_text)
            highlighted = Markup(
                f'<strong class="backlink-link-text">{escaped_link_text}</strong>'
            )
            escaped = Markup(escaped.replace(marker, highlighted, 1))
        else:
            escaped = Markup(escaped.replace(marker, Markup(""), 1))

        results.append((target_post, escaped))

    return results


def _extract_link_url(raw_url: str) -> str:
    """Extract only the URL portion from a raw link target.

    Strips an optional title attribute (text in quotes or parentheses
    following a space after the URL) from a link target string such as
    ``/foo.html "My Title"``.

    Args:
        raw_url: The raw URL string as captured from Markdown source.

    Returns:
        The URL with any title attribute removed.
    """
    # A title may follow the URL after whitespace: url "title" or url 'title'
    return raw_url.split()[0] if raw_url.strip() else raw_url


def _find_links(content: str) -> list[tuple[str, int, int, str]]:
    """Find all hyperlinks in Markdown source content.

    Recognises inline links (``[text](url)``) and reference-style links
    (``[text][ref]`` with a ``[ref]: url`` definition elsewhere in the
    document).

    Args:
        content: Raw Markdown source to scan.

    Returns:
        A list of ``(url, match_start, match_end, link_text)`` tuples.
        *match_start* and *match_end* are the character positions of the
        full link syntax within *content* (useful for context extraction);
        *link_text* is the display text of the link as written in the
        Markdown source.
    """
    results: list[tuple[str, int, int, str]] = []

    # Collect reference link definitions first.
    refs: dict[str, str] = {}
    for definition in _LINK_DEF_RE.finditer(content):
        refs[definition.group(1).lower()] = definition.group(2).strip()

    # Inline links: [text](url)
    for match in _INLINE_LINK_RE.finditer(content):
        url = _extract_link_url(match.group(2))
        if url:
            results.append((url, match.start(), match.end(), match.group(1)))

    # Reference-style links: [text][ref] or [text][]
    for match in _REF_LINK_RE.finditer(content):
        ref_id = match.group(2).lower() or match.group(1).lower()
        url = refs.get(ref_id, "")
        if url:
            results.append((url, match.start(), match.end(), match.group(1)))

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
        url: The raw URL from a Markdown link.
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

    Scans the raw Markdown content of every post for internal links and
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
            source_post.content
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
                source_post.content, internal_links
            ):
                backlinks[target_post.url].append(
                    Backlink(source_post=source_post, snippet=snippet)
                )

    return backlinks


### backlinks.py ends here
