"""Unit tests for the strikethrough module."""

import markdown

from blogmore.strikethrough import StrikethroughExtension


class TestStrikethroughExtension:
    """Tests for the StrikethroughExtension with markdown."""

    def _make_md(self) -> markdown.Markdown:
        """Build a Markdown instance with the extension under test.

        Returns:
            A configured Markdown instance.
        """
        return markdown.Markdown(extensions=[StrikethroughExtension()])

    def test_basic_strikethrough(self) -> None:
        """Test that basic strikethrough syntax is converted to a del element."""
        md = self._make_md()
        html = md.convert("~~strikethrough~~")
        assert "<del>strikethrough</del>" in html

    def test_strikethrough_inline(self) -> None:
        """Test that strikethrough works within surrounding text."""
        md = self._make_md()
        html = md.convert("Here is some ~~deleted text~~ in a sentence.")
        assert "<del>deleted text</del>" in html
        assert "Here is some" in html
        assert "in a sentence." in html

    def test_strikethrough_multiple_words(self) -> None:
        """Test that strikethrough works with multiple words."""
        md = self._make_md()
        html = md.convert("~~multiple words here~~")
        assert "<del>multiple words here</del>" in html

    def test_single_tilde_not_converted(self) -> None:
        """Test that a single tilde is not treated as strikethrough."""
        md = self._make_md()
        html = md.convert("~not strikethrough~")
        assert "<del>" not in html

    def test_strikethrough_alongside_other_formatting(self) -> None:
        """Test that strikethrough works alongside bold and italic."""
        md = self._make_md()
        html = md.convert("**bold**, *italic*, ~~strikethrough~~")
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html
        assert "<del>strikethrough</del>" in html

    def test_makeextension_returns_instance(self) -> None:
        """Test that makeExtension returns a StrikethroughExtension instance."""
        from blogmore.strikethrough import makeExtension

        ext = makeExtension()
        assert isinstance(ext, StrikethroughExtension)
