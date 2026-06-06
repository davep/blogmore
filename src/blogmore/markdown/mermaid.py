"""Markdown extension to support Mermaid diagrams.

This module provides a custom preprocessor that intercepts fenced code blocks
with the language 'mermaid' and outputs them as raw `<pre class="mermaid">`
elements, stashed in the markdown HTML stash to prevent Pygments highlighting
or escaping from codehilite.
"""

import html
import re
from typing import Any

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor


class MermaidPreprocessor(Preprocessor):
    """Preprocessor to handle fenced code blocks containing Mermaid diagrams.

    Scans the source Markdown for fenced code blocks starting with ````mermaid`
    and wraps the contained code in a `<pre class="mermaid">` tag. The content
    is HTML-escaped and stashed in the HTML stash so it does not get processed
    by subsequent Markdown extensions or code block highlighting.
    """

    FENCE_START = re.compile(r"^(\s*)```mermaid\s*$")
    FENCE_END = re.compile(r"^\s*```\s*$")

    def run(self, lines: list[str]) -> list[str]:
        """Process markdown lines, converting mermaid blocks to HTML.

        Args:
            lines: The input lines of markdown.

        Returns:
            The processed lines with mermaid code blocks converted to stashed HTML.
        """
        new_lines: list[str] = []
        in_mermaid = False
        mermaid_lines: list[str] = []
        indent = ""

        for line in lines:
            if not in_mermaid:
                match = self.FENCE_START.match(line)
                if match:
                    in_mermaid = True
                    indent = match.group(1)
                    mermaid_lines = []
                else:
                    new_lines.append(line)
            else:
                if self.FENCE_END.match(line):
                    in_mermaid = False
                    code = "\n".join(mermaid_lines)
                    escaped_code = html.escape(code)
                    placeholder = self.md.htmlStash.store(
                        f'<pre class="mermaid">{escaped_code}</pre>'
                    )
                    new_lines.append(indent + placeholder)
                else:
                    if line.startswith(indent):
                        mermaid_lines.append(line[len(indent) :])
                    else:
                        mermaid_lines.append(line)

        if in_mermaid:
            new_lines.append(indent + "```mermaid")
            new_lines.extend(mermaid_lines)

        return new_lines


class MermaidExtension(Extension):
    """Markdown extension to support Mermaid diagrams."""

    def extendMarkdown(self, md: Any) -> None:
        """Register the mermaid preprocessor with the Markdown instance.

        Args:
            md: The Markdown instance to extend.
        """
        md.preprocessors.register(MermaidPreprocessor(md), "mermaid", 30)


def makeExtension(**kwargs: Any) -> MermaidExtension:
    """Create and return an instance of the MermaidExtension.

    Args:
        **kwargs: Configuration options.

    Returns:
        An instance of MermaidExtension.
    """
    return MermaidExtension(**kwargs)
