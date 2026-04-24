"""Markdown to plain text conversion utility.

Provides :func:`markdown_to_plain_text` — the canonical way to convert a
Markdown string to clean, whitespace-collapsed plain text within BlogMore.
It runs the input through the Python-Markdown library so that all block
structures (fenced code, blockquotes, tables, admonitions, etc.) are handled
correctly before HTML tags are stripped.

This module is also the single source of truth for BlogMore's custom Markdown
extension set via :func:`create_custom_extensions`, which is consumed by the
full site parser, the first-paragraph extractor, and any other context that
needs to render or strip BlogMore-flavoured Markdown.
"""

##############################################################################
# Python imports.
import re
from html.parser import HTMLParser
from typing import Any

##############################################################################
# Third-party imports.
import markdown

##############################################################################
# Local imports.
from blogmore.markdown.admonitions import AdmonitionsExtension
from blogmore.markdown.external_links import ExternalLinksExtension
from blogmore.markdown.heading_anchors import HeadingAnchorsExtension
from blogmore.markdown.strikethrough import StrikethroughExtension


def create_custom_extensions(site_url: str = "") -> list[Any]:
    """Create instances of all custom BlogMore Markdown extensions.

    This is the single source of truth for BlogMore's custom Markdown
    extension set.  The full-rendering parser, the first-paragraph
    extractor, and the plain-text converter all pull their custom-extension
    list from here, so any new extension is automatically included in every
    context.

    Args:
        site_url: Base URL of the site; forwarded to
            :class:`~blogmore.markdown.external_links.ExternalLinksExtension`
            so it can distinguish internal from external links.

    Returns:
        A list of configured custom Markdown extension instances.
    """
    return [
        AdmonitionsExtension(),
        ExternalLinksExtension(site_url=site_url),
        HeadingAnchorsExtension(),
        StrikethroughExtension(),
    ]


def _make_markdown_instance() -> markdown.Markdown:
    """Create a Markdown instance suitable for plain-text extraction.

    Includes all BlogMore custom extensions and the standard extensions
    needed to correctly parse all block structures.  Intentionally omits
    presentation-only extensions (``codehilite``, ``toc``) that are not
    required for text extraction.

    Returns:
        A fresh, configured :class:`markdown.Markdown` instance.
    """
    return markdown.Markdown(
        extensions=[
            "fenced_code",
            "tables",
            "footnotes",
            *create_custom_extensions(),
        ],
    )


class _AllTextExtractor(HTMLParser):
    """HTML parser that accumulates all visible text nodes.

    Unlike the first-paragraph extractor, this parser simply collects every
    character-data node encountered in the HTML, producing a plain-text
    representation of the entire document.
    """

    def __init__(self) -> None:
        """Initialise the extractor."""
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        """Accumulate a character-data node.

        Args:
            data: Text content from the current HTML node.
        """
        self._chunks.append(data)

    @property
    def text(self) -> str:
        """Return all accumulated text with whitespace collapsed.

        Returns:
            Plain-text content with all whitespace runs normalised to a
            single space and leading/trailing whitespace removed.
        """
        return re.sub(r"\s+", " ", "".join(self._chunks)).strip()


def markdown_to_plain_text(text: str) -> str:
    """Convert a Markdown string to clean plain text.

    Runs the input through Python-Markdown (with all BlogMore extensions and
    common block-level extensions such as ``fenced_code``, ``tables``, and
    ``footnotes``) to produce HTML, then strips all HTML tags and collapses
    whitespace.  This correctly handles all Markdown block structures
    including fenced code blocks, blockquotes, admonitions, and tables —
    none of these leave raw Markdown syntax characters in the result.

    Args:
        text: Raw Markdown text to convert.

    Returns:
        Plain-text representation with whitespace collapsed to single spaces,
        or an empty string if *text* is blank.
    """
    if not text.strip():
        return ""
    html = _make_markdown_instance().convert(text)
    extractor = _AllTextExtractor()
    extractor.feed(html)
    return extractor.text


### plain_text.py ends here
