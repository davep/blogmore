"""Unit tests for the admonitions module."""

import markdown

from blogmore.admonitions import AdmonitionsExtension


class TestAdmonitionsExtension:
    """Test the AdmonitionsExtension with markdown."""

    def test_note_admonition(self) -> None:
        """Test that note admonitions are rendered correctly."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> [!NOTE]
> This is a note."""
        html = md.convert(text)
        assert 'class="admonition admonition-note"' in html
        assert 'class="admonition-title"' in html
        assert "Note" in html
        assert "This is a note" in html
        assert "ℹ️" in html

    def test_tip_admonition(self) -> None:
        """Test that tip admonitions are rendered correctly."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> [!TIP]
> This is a helpful tip."""
        html = md.convert(text)
        assert 'class="admonition admonition-tip"' in html
        assert "Tip" in html
        assert "This is a helpful tip" in html
        assert "💡" in html

    def test_important_admonition(self) -> None:
        """Test that important admonitions are rendered correctly."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> [!IMPORTANT]
> This is important information."""
        html = md.convert(text)
        assert 'class="admonition admonition-important"' in html
        assert "Important" in html
        assert "This is important information" in html
        assert "❗" in html

    def test_warning_admonition(self) -> None:
        """Test that warning admonitions are rendered correctly."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> [!WARNING]
> This is a warning."""
        html = md.convert(text)
        assert 'class="admonition admonition-warning"' in html
        assert "Warning" in html
        assert "This is a warning" in html
        assert "⚠️" in html

    def test_caution_admonition(self) -> None:
        """Test that caution admonitions are rendered correctly."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> [!CAUTION]
> This is a caution."""
        html = md.convert(text)
        assert 'class="admonition admonition-caution"' in html
        assert "Caution" in html
        assert "This is a caution" in html
        assert "🚨" in html

    def test_case_insensitive(self) -> None:
        """Test that admonition types are case-insensitive."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> [!note]
> Lowercase note."""
        html = md.convert(text)
        assert 'class="admonition admonition-note"' in html
        assert "Note" in html

    def test_multiline_content(self) -> None:
        """Test admonitions with multiple lines of content."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> [!NOTE]
> This is the first line.
> This is the second line.
> This is the third line."""
        html = md.convert(text)
        assert "This is the first line" in html
        assert "This is the second line" in html
        assert "This is the third line" in html

    def test_formatted_content(self) -> None:
        """Test that markdown formatting works inside admonitions."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> [!NOTE]
> This is **bold** and *italic* text."""
        html = md.convert(text)
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html

    def test_empty_admonition(self) -> None:
        """Test admonitions with no content."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = "> [!NOTE]"
        html = md.convert(text)
        assert 'class="admonition admonition-note"' in html
        assert "Note" in html

    def test_admonition_with_blank_lines(self) -> None:
        """Test admonitions that include blank lines in content."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> [!NOTE]
> First paragraph.
>
> Second paragraph."""
        html = md.convert(text)
        assert "First paragraph" in html
        assert "Second paragraph" in html

    def test_regular_blockquote_not_affected(self) -> None:
        """Test that regular blockquotes without alert syntax still work."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> This is a regular blockquote.
> It should not be styled as an admonition."""
        html = md.convert(text)
        # Should be a regular blockquote
        assert "<blockquote>" in html
        assert 'class="admonition' not in html

    def test_multiple_admonitions(self) -> None:
        """Test multiple admonitions in the same document."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> [!NOTE]
> First note.

> [!WARNING]
> A warning."""
        html = md.convert(text)
        # Count the number of top-level admonition divs (with specific class patterns)
        assert 'admonition-note' in html
        assert 'admonition-warning' in html
        assert "First note" in html
        assert "A warning" in html

    def test_admonition_with_link(self) -> None:
        """Test that links work inside admonitions."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> [!NOTE]
> Check out [this link](https://example.com)."""
        html = md.convert(text)
        assert '<a href="https://example.com">this link</a>' in html

    def test_admonition_with_code(self) -> None:
        """Test that inline code works inside admonitions."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> [!NOTE]
> Use the `code` tag."""
        html = md.convert(text)
        assert "<code>code</code>" in html

    def test_content_after_admonition(self) -> None:
        """Test that content after an admonition is processed correctly."""
        md = markdown.Markdown(extensions=[AdmonitionsExtension()])
        text = """> [!NOTE]
> This is a note.

This is regular text after the note."""
        html = md.convert(text)
        assert 'class="admonition admonition-note"' in html
        assert "This is a note" in html
        assert "This is regular text after the note" in html
