"""Markdown extension for GitHub-style admonitions/alerts."""

import re
from typing import Any
from xml.etree.ElementTree import Element, SubElement

from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension


class AdmonitionProcessor(BlockProcessor):
    """Block processor that converts GitHub-style alerts to admonition divs."""

    # Supported admonition types with their icons (Unicode symbols)
    ADMONITION_TYPES = {
        "note": "ℹ️",
        "tip": "💡",
        "important": "❗",
        "warning": "⚠️",
        "caution": "🚨",
    }

    # Pattern to match GitHub alert syntax: > [!TYPE]
    ALERT_RE = re.compile(r"^>\s*\[!(note|tip|important|warning|caution)\]\s*$", re.IGNORECASE)
    # Pattern to match blockquote lines: > content
    BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")

    def test(self, parent: Element, block: str) -> bool:
        """Test if this block is a GitHub alert.

        Args:
            parent: The parent element
            block: The block of text to test

        Returns:
            True if the block starts with a GitHub alert marker
        """
        # Check if first line matches alert pattern
        lines = block.split("\n")
        if lines and self.ALERT_RE.match(lines[0]):
            return True
        return False

    def run(self, parent: Element, blocks: list[str]) -> bool:
        """Process the GitHub alert block.

        Args:
            parent: The parent element
            blocks: List of remaining blocks to process

        Returns:
            True if the block was successfully processed
        """
        block = blocks.pop(0)
        lines = block.split("\n")

        # Extract the alert type from the first line
        first_line = lines[0]
        match = self.ALERT_RE.match(first_line)
        if not match:
            return False

        alert_type = match.group(1).lower()
        icon = self.ADMONITION_TYPES.get(alert_type, "ℹ️")

        # Collect the content lines (remaining blockquote lines)
        content_lines = []
        for line in lines[1:]:
            # Check if it's a blockquote line
            quote_match = self.BLOCKQUOTE_RE.match(line)
            if quote_match:
                # Extract the content after '>'
                content_lines.append(quote_match.group(1))
            elif line.strip() == "":
                # Empty lines within the alert
                content_lines.append("")
            else:
                # Not a blockquote line anymore, put it back
                blocks.insert(0, line)
                break

        # Create the admonition div
        admonition_div = SubElement(parent, "div")
        admonition_div.set("class", f"admonition admonition-{alert_type}")

        # Create the title/header
        title_div = SubElement(admonition_div, "div")
        title_div.set("class", "admonition-title")
        title_div.text = f"{icon} {alert_type.capitalize()}"

        # Create the content div
        content_div = SubElement(admonition_div, "div")
        content_div.set("class", "admonition-content")

        # Join and process the content
        content_text = "\n".join(content_lines).strip()
        if content_text:
            # Parse the content as markdown by creating a new parser
            # and processing the text
            self.parser.parseBlocks(content_div, [content_text])

        return True


class AdmonitionsExtension(Extension):
    """Markdown extension for GitHub-style admonitions."""

    def extendMarkdown(self, md: Any) -> None:
        """Register the extension with the Markdown instance.

        Args:
            md: The Markdown instance
        """
        processor = AdmonitionProcessor(md.parser)
        # Add with priority higher than blockquote processor (85)
        # so it runs before standard blockquote processing
        md.parser.blockprocessors.register(processor, "github_admonitions", 90)


def makeExtension(**kwargs: Any) -> AdmonitionsExtension:
    """Create and return an instance of the extension.

    Args:
        **kwargs: Configuration options

    Returns:
        An instance of AdmonitionsExtension
    """
    return AdmonitionsExtension(**kwargs)
