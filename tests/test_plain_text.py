"""Tests for the markdown.plain_text module."""

##############################################################################
# Application imports.
from blogmore.markdown.plain_text import markdown_to_plain_text


class TestMarkdownToPlainText:
    """Tests for markdown_to_plain_text."""

    def test_plain_text_unchanged(self) -> None:
        """Plain prose without any Markdown syntax passes through unchanged."""
        assert markdown_to_plain_text("Hello world") == "Hello world"

    def test_empty_string(self) -> None:
        """An empty string returns an empty string."""
        assert markdown_to_plain_text("") == ""

    def test_whitespace_only(self) -> None:
        """A string of only whitespace returns an empty string."""
        assert markdown_to_plain_text("   \n\t  ") == ""

    def test_bold_double_asterisk(self) -> None:
        """**bold** syntax is stripped; the inner text is preserved."""
        assert markdown_to_plain_text("This is **bold** text") == "This is bold text"

    def test_italic_single_asterisk(self) -> None:
        """*italic* syntax is stripped; the inner text is preserved."""
        assert markdown_to_plain_text("This is *italic* text") == "This is italic text"

    def test_strikethrough(self) -> None:
        """~~strikethrough~~ syntax is stripped; the inner text is preserved."""
        assert (
            markdown_to_plain_text("This is ~~struck~~ text") == "This is struck text"
        )

    def test_inline_code(self) -> None:
        """`inline code` backtick syntax is stripped; the code text is preserved."""
        assert markdown_to_plain_text("Use `foo()` here") == "Use foo() here"

    def test_atx_heading_marker_removed(self) -> None:
        """ATX heading markers (## etc.) are stripped; the heading text remains."""
        assert markdown_to_plain_text("## My Heading") == "My Heading"

    def test_inline_link_reduced_to_text(self) -> None:
        """[text](url) inline links are reduced to their link text."""
        assert (
            markdown_to_plain_text("See [this post](/2024/01/post.html) for details")
            == "See this post for details"
        )

    def test_whitespace_collapsed(self) -> None:
        """Multiple blank lines and spaces are collapsed to a single space."""
        result = markdown_to_plain_text("Hello\n\nworld\n  text")
        assert result == "Hello world text"

    def test_blockquote_prefix_stripped(self) -> None:
        """Blockquote `>` marker characters are not present in the output."""
        result = markdown_to_plain_text("> This is a blockquote.")
        assert ">" not in result
        assert "This is a blockquote." in result

    def test_fenced_code_block_delimiters_stripped(self) -> None:
        """Fenced code block ``` delimiters are not present in the output."""
        content = "```python\nprint('hello')\n```"
        result = markdown_to_plain_text(content)
        assert "```" not in result
        assert "print" in result

    def test_fenced_code_block_language_tag_stripped(self) -> None:
        """The language specifier on a fenced code block is not in the output."""
        content = "```python\ncode\n```"
        result = markdown_to_plain_text(content)
        assert "python" not in result

    def test_unordered_list_markers_stripped(self) -> None:
        """List `- ` bullet markers are stripped; item text is preserved."""
        content = "- First\n- Second\n- Third"
        result = markdown_to_plain_text(content)
        assert "-" not in result
        assert "First" in result
        assert "Second" in result
        assert "Third" in result

    def test_ordered_list_markers_stripped(self) -> None:
        """Ordered list `1.` markers are stripped; item text is preserved."""
        content = "1. Alpha\n2. Beta\n3. Gamma"
        result = markdown_to_plain_text(content)
        assert "1." not in result
        assert "Alpha" in result
        assert "Beta" in result

    def test_html_tags_stripped(self) -> None:
        """Inline HTML tags inside Markdown are removed."""
        result = markdown_to_plain_text("Hello <em>world</em>")
        assert "<" not in result
        assert "world" in result

    def test_horizontal_rule_produces_no_text(self) -> None:
        """A horizontal rule (`---`) produces no meaningful text output."""
        result = markdown_to_plain_text("Before\n\n---\n\nAfter")
        assert "---" not in result
        assert "Before" in result
        assert "After" in result

    def test_nested_blockquote_stripped(self) -> None:
        """Nested blockquote `>>` prefixes do not appear in the output."""
        result = markdown_to_plain_text(">> Deeply quoted")
        assert ">" not in result
        assert "Deeply quoted" in result

    def test_mixed_block_and_inline(self) -> None:
        """A mix of block-level and inline Markdown is fully stripped."""
        content = (
            "## Introduction\n\n"
            "> Blockquote with **bold** text.\n\n"
            "Normal paragraph with `code` and [link text](/url).\n\n"
            "```\ncode block\n```"
        )
        result = markdown_to_plain_text(content)
        assert "#" not in result
        assert ">" not in result
        assert "```" not in result
        assert "**" not in result
        assert "Introduction" in result
        assert "Blockquote" in result
        assert "bold" in result
        assert "code" in result
        assert "link text" in result
