"""First-paragraph extraction from Markdown content.

Converts Markdown to HTML using all BlogMore extensions and then locates
the first top-level paragraph that contains real text, returning it as
plain text.  Block-level containers (admonitions, blockquotes, tables,
lists, etc.) are skipped, as are paragraphs that consist entirely of
images.
"""

import re
from html.parser import HTMLParser
from typing import Any

import markdown

from blogmore.markdown.admonitions import AdmonitionsExtension
from blogmore.markdown.external_links import ExternalLinksExtension
from blogmore.markdown.heading_anchors import HeadingAnchorsExtension
from blogmore.markdown.strikethrough import StrikethroughExtension


def create_custom_extensions(site_url: str = "") -> list[Any]:
    """Create instances of all custom BlogMore Markdown extensions.

    This is the single source of truth for BlogMore's custom Markdown extension
    set.  Both the full-rendering parser and the lightweight extraction instance
    pull their custom-extension list from here, so any new extension added to
    this list is automatically included in both contexts.

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


def _make_extraction_markdown() -> markdown.Markdown:
    """Create a Markdown instance configured for first-paragraph text extraction.

    Includes all BlogMore custom extensions and the standard extensions needed
    to correctly identify paragraph boundaries.  Intentionally omits
    presentation-only extensions such as ``codehilite`` and ``toc`` that are
    not required for plain-text extraction.

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


class _FirstParagraphExtractor(HTMLParser):
    """HTML parser that extracts plain text from the first non-image-only paragraph.

    Only top-level ``<p>`` elements are considered; paragraphs nested inside
    block-level containers such as admonition ``<div>`` elements, blockquotes,
    or list items are skipped.  A paragraph that consists entirely of images
    (no text data) is also skipped so that posts that open with a banner image
    return the following descriptive paragraph instead.
    """

    _BLOCK_TAGS: frozenset[str] = frozenset(
        {
            "div",
            "blockquote",
            "ul",
            "ol",
            "table",
            "thead",
            "tbody",
            "tr",
            "td",
            "th",
            "pre",
            "figure",
            "section",
            "article",
            "aside",
            "nav",
            "header",
            "footer",
            "main",
        }
    )

    def __init__(self) -> None:
        """Initialise the extractor.

        Sets up all tracking state used during parsing:

        * ``_block_depth`` — current nesting level inside block-level container
          elements (``<div>``, ``<blockquote>``, ``<ul>``, etc.).  Any ``<p>``
          encountered while this is non-zero is nested and therefore skipped.
        * ``_in_paragraph`` — whether the parser is currently inside a
          candidate top-level ``<p>`` element.
        * ``_chunks`` — raw character-data fragments collected from the current
          paragraph, joined and normalised when the paragraph ends.
        * ``_has_text`` — set to ``True`` as soon as non-whitespace data is
          seen inside the current paragraph; keeps image-only paragraphs from
          being returned.
        * ``_result`` — the accepted plain-text paragraph (empty until found).
        * ``_done`` — short-circuit flag; once ``True`` all further events are
          ignored.
        """
        super().__init__(convert_charrefs=True)
        self._block_depth: int = 0
        self._in_paragraph: bool = False
        self._chunks: list[str] = []
        self._has_text: bool = False
        self._result: str = ""
        self._done: bool = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Process an opening HTML tag.

        Args:
            tag: The lowercase tag name.
            attrs: List of ``(attribute-name, value)`` pairs for the tag.
        """
        if self._done:
            return
        if tag in self._BLOCK_TAGS:
            self._block_depth += 1
        elif tag == "p" and self._block_depth == 0 and not self._in_paragraph:
            self._in_paragraph = True
            self._chunks = []
            self._has_text = False

    def handle_endtag(self, tag: str) -> None:
        """Process a closing HTML tag.

        Args:
            tag: The lowercase tag name.
        """
        if self._done:
            return
        if tag in self._BLOCK_TAGS:
            if self._block_depth > 0:
                self._block_depth -= 1
        elif tag == "p" and self._in_paragraph:
            self._in_paragraph = False
            text = re.sub(r"\s+", " ", "".join(self._chunks)).strip()
            if self._has_text and text:
                self._result = text
                self._done = True

    def handle_data(self, data: str) -> None:
        """Process character data between tags.

        Args:
            data: The text content between tags.
        """
        if self._done or not self._in_paragraph:
            return
        self._chunks.append(data)
        if data.strip():
            self._has_text = True

    @property
    def result(self) -> str:
        """Get the extracted paragraph text.

        Returns:
            The extracted first paragraph text, or an empty string if none was
            found.
        """
        return self._result


def extract_first_paragraph(content: str) -> str:
    """Extract the first paragraph from markdown content as plain text.

    Converts the markdown to HTML using all BlogMore extensions, then finds
    the first top-level ``<p>`` element that contains actual text.  Paragraphs
    that consist solely of images are skipped.

    Args:
        content: The markdown content to extract from.

    Returns:
        The first paragraph as plain text, or an empty string if none is found.
    """
    if not content.strip():
        return ""
    html_content = _make_extraction_markdown().convert(content)
    extractor = _FirstParagraphExtractor()
    extractor.feed(html_content)
    return extractor.result
