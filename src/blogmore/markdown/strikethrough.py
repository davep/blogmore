"""Markdown extension to support strikethrough text using ``~~text~~`` syntax."""

import re
import xml.etree.ElementTree as etree
from typing import Any

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor


class StrikethroughInlineProcessor(InlineProcessor):
    """Inline processor that converts ``~~text~~`` to ``<del>text</del>``."""

    def handleMatch(  # type: ignore[override]
        self, m: re.Match[str], data: str
    ) -> tuple[etree.Element, int, int]:
        """Convert a matched ``~~text~~`` span to a ``<del>`` element.

        Args:
            m: The regex match object containing the strikethrough content.
            data: The full inline text being processed.

        Returns:
            A tuple of the ``<del>`` element and the start and end positions
            of the match within `data`.
        """
        element = etree.Element("del")
        element.text = m.group(1)
        return element, m.start(0), m.end(0)


class StrikethroughExtension(Extension):
    """Markdown extension that adds strikethrough text support.

    Converts ``~~text~~`` to ``<del>text</del>`` in the generated HTML,
    producing text that browsers render with a line through it.
    """

    def extendMarkdown(self, md: Any) -> None:
        """Register the strikethrough inline processor with the Markdown instance.

        Args:
            md: The Markdown instance to extend.
        """
        pattern = r"~~(.+?)~~"
        processor = StrikethroughInlineProcessor(pattern, md)
        md.inlinePatterns.register(processor, "strikethrough", 175)


def makeExtension(**kwargs: Any) -> StrikethroughExtension:
    """Create and return an instance of the StrikethroughExtension.

    Args:
        **kwargs: Configuration options (unused; accepted for API compatibility).

    Returns:
        An instance of StrikethroughExtension.
    """
    return StrikethroughExtension(**kwargs)
