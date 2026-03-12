"""Markdown extension to add hover anchor links to headings."""

from typing import Any
from xml.etree.ElementTree import Element, SubElement

import markdown as _markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

HEADING_TAGS = frozenset(["h2", "h3", "h4", "h5", "h6"])

ANCHOR_SYMBOL = "¶"


class HeadingAnchorsProcessor(Treeprocessor):
    """Tree processor that adds hover anchor links to headings with IDs.

    Iterates over all heading elements (h2–h6) in the markdown tree and
    appends a small anchor link element to each heading that carries an
    ``id`` attribute.  The anchor is styled via CSS so that it is
    invisible by default and fades in when the user hovers over the
    heading, allowing readers to copy a direct link to any section
    without affecting the page layout.
    """

    def run(self, root: Element) -> Element | None:
        """Add anchor links to all headings that have IDs.

        Args:
            root: The root element of the markdown element tree.

        Returns:
            None; the tree is modified in place.
        """
        for element in root.iter():
            if element.tag in HEADING_TAGS:
                heading_id = element.get("id")
                if heading_id:
                    self._add_anchor_link(element, heading_id)
        return None

    def _add_anchor_link(self, heading: Element, heading_id: str) -> None:
        """Append a hover-visible anchor link to a heading element.

        Args:
            heading: The heading element to modify.
            heading_id: The ``id`` value of the heading, used as the
                link fragment.
        """
        anchor = SubElement(heading, "a")
        anchor.set("class", "heading-anchor")
        anchor.set("href", f"#{heading_id}")
        anchor.set("aria-label", "Link to this heading")
        anchor.text = ANCHOR_SYMBOL


class HeadingAnchorsExtension(Extension):
    """Markdown extension that adds hover anchor links to headings.

    When enabled, every heading element (h2–h6) that carries an ``id``
    attribute receives a small anchor link (``¶``) at the end of its
    text.  The link is hidden by default and revealed on hover via CSS,
    giving readers a convenient way to obtain a permalink to any section
    without disrupting the visual layout.

    This extension should be combined with the ``toc`` and ``attr_list``
    extensions:

    * ``toc`` automatically assigns ``id`` attributes to all headings
      whose text does not already specify one.
    * ``attr_list`` allows authors to specify custom ``id`` values using
      the ``{#custom-id}`` syntax directly in the heading line.

    This extension's tree processor runs at priority 4 (lower than
    ``toc`` at 5), so it always operates on headings after their final
    ``id`` has been determined.
    """

    def extendMarkdown(self, md: _markdown.Markdown) -> None:
        """Register the heading anchors tree processor.

        Args:
            md: The Markdown instance to extend.
        """
        processor = HeadingAnchorsProcessor(md)
        # Priority 4 — runs after toc (priority 5) so IDs are finalised first.
        md.treeprocessors.register(processor, "heading_anchors", 4)


def makeExtension(**kwargs: Any) -> HeadingAnchorsExtension:
    """Create and return an instance of the HeadingAnchorsExtension.

    Args:
        **kwargs: Configuration options (unused; accepted for API compatibility).

    Returns:
        An instance of HeadingAnchorsExtension.
    """
    return HeadingAnchorsExtension(**kwargs)
