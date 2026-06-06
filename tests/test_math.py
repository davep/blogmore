"""Unit tests for the LaTeX math Markdown extension."""

import markdown

from blogmore.markdown.math import MathExtension


class TestMathExtension:
    """Tests for the MathExtension with markdown."""

    def _make_md(self) -> markdown.Markdown:
        """Build a Markdown instance with the extension under test.

        Returns:
            A configured Markdown instance.
        """
        return markdown.Markdown(extensions=[MathExtension()])

    def test_inline_math(self) -> None:
        """Test that inline math ($formula$) is wrapped in a math-inline span."""
        md = self._make_md()
        html = md.convert("This is $x^2 + y^2$ math.")
        assert '<span class="math-inline">$x^2 + y^2$</span>' in html

    def test_inline_math_no_spaces(self) -> None:
        """Test that inline math matches spacing rules (no space inside delimiters)."""
        md = self._make_md()

        # Space at start
        html_space_start = md.convert("This is not $ x^2$ math.")
        assert '<span class="math-inline">' not in html_space_start

        # Space at end
        html_space_end = md.convert("This is not $x^2 $ math.")
        assert '<span class="math-inline">' not in html_space_end

    def test_block_math_single_line(self) -> None:
        """Test single-line block math ($$formula$$)."""
        md = self._make_md()
        html = md.convert("$$f(x) = y$$")
        assert '<div class="math-block">$$\nf(x) = y\n$$</div>' in html

    def test_block_math_multi_line(self) -> None:
        """Test multi-line block math ($$ ... $$)."""
        md = self._make_md()
        content = """
$$
f(x) = \\int x dx
$$
"""
        html = md.convert(content)
        assert '<div class="math-block">$$\nf(x) = \\int x dx\n$$</div>' in html

    def test_math_inside_code_protected(self) -> None:
        """Test that math syntax inside code backticks is ignored."""
        md = self._make_md()

        # Inline code
        html_code = md.convert("Ignore `$x^2$` in code.")
        assert "<code>$x^2$</code>" in html_code
        assert "math-inline" not in html_code

    def test_makeextension_returns_instance(self) -> None:
        """Test that makeExtension returns a MathExtension instance."""
        from blogmore.markdown.math import makeExtension

        ext = makeExtension()
        assert isinstance(ext, MathExtension)
