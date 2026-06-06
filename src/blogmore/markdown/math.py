"""Markdown extension to support LaTeX mathematical equations.

This module provides a custom preprocessor for block equations (marked by `$$`)
and an inline processor for inline formulas (marked by `$`), wrapping them in
`<div class="math-block">` and `<span class="math-inline">` tags respectively to
protect them from Markdown formatting and to allow conditional CDN loading.
"""

import re
import xml.etree.ElementTree as etree
from typing import Any

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.preprocessors import Preprocessor


class BlockMathPreprocessor(Preprocessor):
    """Preprocessor to handle block math equations marked by $$ delimiters.

    Scans the document lines for block math equations (either single-line or
    multi-line) and wraps them in a `<div class="math-block">` tag. The block
    is stashed in the HTML stash to protect it from subsequent Markdown parsing.
    """

    FENCE_START = re.compile(r"^(\s*)\$\$\s*$")
    FENCE_END = re.compile(r"^\s*\$\$\s*$")
    SINGLE_LINE = re.compile(r"^(\s*)\$\$(.+?)\$\$\s*$")

    def run(self, lines: list[str]) -> list[str]:
        """Process markdown lines, extracting block math equations.

        Args:
            lines: The input lines of markdown.

        Returns:
            The processed lines with block math equations converted to stashed HTML.
        """
        new_lines: list[str] = []
        in_math = False
        math_lines: list[str] = []
        indent = ""

        for line in lines:
            if not in_math:
                # Check for single line block math first
                single_match = self.SINGLE_LINE.match(line)
                if single_match:
                    indent = single_match.group(1)
                    formula = single_match.group(2).strip()
                    placeholder = self.md.htmlStash.store(
                        f'<div class="math-block">$$\n{formula}\n$$</div>'
                    )
                    new_lines.append(indent + placeholder)
                    continue

                # Check for multi-line block math start
                match = self.FENCE_START.match(line)
                if match:
                    in_math = True
                    indent = match.group(1)
                    math_lines = []
                else:
                    new_lines.append(line)
            else:
                if self.FENCE_END.match(line):
                    in_math = False
                    formula = "\n".join(math_lines)
                    placeholder = self.md.htmlStash.store(
                        f'<div class="math-block">$$\n{formula}\n$$</div>'
                    )
                    new_lines.append(indent + placeholder)
                else:
                    if line.startswith(indent):
                        math_lines.append(line[len(indent) :])
                    else:
                        math_lines.append(line)

        if in_math:
            new_lines.append(indent + "$$")
            new_lines.extend(math_lines)

        return new_lines


class InlineMathProcessor(InlineProcessor):
    """Inline processor for inline LaTeX formulas marked by single $ delimiters.

    Extracts inline formulas and wraps them in a `<span class="math-inline">` element.
    """

    def handleMatch(  # type: ignore[override]
        self, m: re.Match[str], data: str
    ) -> tuple[etree.Element, int, int]:
        """Convert a matched inline math formula to a math span.

        Args:
            m: The regex match object containing the formula.
            data: The full inline text being processed.

        Returns:
            A tuple of the math span element and the start and end positions
            of the match within `data`.
        """
        element = etree.Element("span")
        element.set("class", "math-inline")
        element.text = f"${m.group(1)}$"
        return element, m.start(0), m.end(0)


class MathExtension(Extension):
    """Markdown extension to support LaTeX math rendering."""

    def extendMarkdown(self, md: Any) -> None:
        """Register the math preprocessor and inline processor.

        Args:
            md: The Markdown instance to extend.
        """
        # Register the block math preprocessor with priority higher than fenced_code (25)
        md.preprocessors.register(BlockMathPreprocessor(md), "block_math", 28)

        # Register the inline math processor with priority higher than escape (180)
        # to ensure it parses dollar signs before they are escaped, but after code
        # span processor (190) so code backticks are protected.
        inline_pattern = r"\$([^\$\s](?:[^\$]*?[^\$\s])?)\$"
        md.inlinePatterns.register(
            InlineMathProcessor(inline_pattern, md), "inline_math", 185
        )


def makeExtension(**kwargs: Any) -> MathExtension:
    """Create and return an instance of the MathExtension.

    Args:
        **kwargs: Configuration options.

    Returns:
        An instance of MathExtension.
    """
    return MathExtension(**kwargs)
