"""Unit tests for the Mermaid Markdown extension."""

import markdown

from blogmore.markdown.mermaid import MermaidExtension


class TestMermaidExtension:
    """Tests for the MermaidExtension with markdown."""

    def _make_md(self) -> markdown.Markdown:
        """Build a Markdown instance with the extension under test.

        Returns:
            A configured Markdown instance.
        """
        return markdown.Markdown(extensions=[MermaidExtension()])

    def test_mermaid_fenced_block(self) -> None:
        """Test that a mermaid code block is converted to pre class="mermaid"."""
        md = self._make_md()
        content = """
Here is a diagram:

```mermaid
graph TD
    A[Start] --> B(Process)
```

And some text after.
"""
        html = md.convert(content)
        assert (
            '<pre class="mermaid">graph TD\n    A[Start] --&gt; B(Process)</pre>'
            in html
        )
        assert "Here is a diagram:" in html
        assert "And some text after." in html

    def test_mermaid_multiple_blocks(self) -> None:
        """Test that multiple mermaid code blocks in a single document are handled."""
        md = self._make_md()
        content = """
```mermaid
graph TD
    A --> B
```

Middle text.

```mermaid
sequenceDiagram
    Alice->>Bob: Hello
```
"""
        html = md.convert(content)
        assert '<pre class="mermaid">graph TD\n    A --&gt; B</pre>' in html
        assert (
            '<pre class="mermaid">sequenceDiagram\n    Alice-&gt;&gt;Bob: Hello</pre>'
            in html
        )
        assert "Middle text." in html

    def test_mermaid_non_closed_fence(self) -> None:
        """Test a mermaid fence that does not close."""
        md = self._make_md()
        content = """
```mermaid
graph TD
    A --> B
"""
        html = md.convert(content)
        assert "graph TD" in html
        assert "mermaid" in html

    def test_makeextension_returns_instance(self) -> None:
        """Test that makeExtension returns a MermaidExtension instance."""
        from blogmore.markdown.mermaid import makeExtension

        ext = makeExtension()
        assert isinstance(ext, MermaidExtension)
