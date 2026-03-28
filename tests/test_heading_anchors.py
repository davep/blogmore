"""Unit tests for the heading_anchors module."""

import markdown
from markdown.extensions import Extension

from blogmore.markdown.heading_anchors import (
    ANCHOR_SYMBOL,
    HEADING_TAGS,
    HeadingAnchorsExtension,
    HeadingAnchorsProcessor,
)


class TestHeadingAnchorsConstants:
    """Tests for module-level constants."""

    def test_anchor_symbol_is_pilcrow(self) -> None:
        """Test that ANCHOR_SYMBOL is the pilcrow character."""
        assert ANCHOR_SYMBOL == "¶"

    def test_heading_tags_contains_h2_through_h6(self) -> None:
        """Test that HEADING_TAGS covers h2 through h6 but not h1."""
        assert frozenset(["h2", "h3", "h4", "h5", "h6"]) == HEADING_TAGS

    def test_heading_tags_does_not_contain_h1(self) -> None:
        """Test that h1 is excluded from HEADING_TAGS."""
        assert "h1" not in HEADING_TAGS


class TestHeadingAnchorsExtension:
    """Tests for the HeadingAnchorsExtension with markdown."""

    def _make_md(
        self, extra_extensions: list[str | Extension] | None = None
    ) -> markdown.Markdown:
        """Build a Markdown instance with the extension under test.

        Args:
            extra_extensions: Additional extensions to include alongside
                the heading anchors extension.

        Returns:
            A configured Markdown instance.
        """
        extensions: list[str | Extension] = ["toc", HeadingAnchorsExtension()]
        if extra_extensions:
            extensions.extend(extra_extensions)
        return markdown.Markdown(extensions=extensions)

    def test_auto_id_heading_gets_anchor(self) -> None:
        """Test that a plain heading gets an auto-generated anchor."""
        md = self._make_md()
        html = md.convert("## My Heading")
        assert 'class="heading-anchor"' in html
        assert 'href="#my-heading"' in html
        assert ANCHOR_SYMBOL in html

    def test_anchor_element_is_inside_heading(self) -> None:
        """Test that the anchor element is placed inside the heading tag."""
        md = self._make_md()
        html = md.convert("## Section Title")
        # The anchor must appear before the closing </h2>
        assert '<a aria-label="Link to this heading" class="heading-anchor" href="#section-title">' in html
        close_pos = html.index("</h2>")
        anchor_pos = html.index("heading-anchor")
        assert anchor_pos < close_pos

    def test_custom_id_via_attr_list(self) -> None:
        """Test that {#custom-id} syntax sets a custom ID on the heading."""
        md = markdown.Markdown(extensions=["toc", "attr_list", HeadingAnchorsExtension()])
        html = md.convert("## My Great Heading {#custom-id}")
        assert 'id="custom-id"' in html
        assert 'href="#custom-id"' in html
        assert "My Great Heading" in html
        # The raw {#custom-id} text should not appear in the output
        assert "{#custom-id}" not in html

    def test_custom_id_anchor_link_uses_custom_id(self) -> None:
        """Test that the anchor link references the custom ID."""
        md = markdown.Markdown(extensions=["toc", "attr_list", HeadingAnchorsExtension()])
        html = md.convert("### Installation {#installation}")
        assert 'id="installation"' in html
        assert 'href="#installation"' in html

    def test_auto_id_takes_precedence_when_no_custom_id(self) -> None:
        """Test that auto-generated IDs are used when no custom ID is set."""
        md = self._make_md()
        html = md.convert("## Hello World")
        assert 'id="hello-world"' in html
        assert 'href="#hello-world"' in html

    def test_h2_gets_anchor(self) -> None:
        """Test that h2 headings get anchor links."""
        md = self._make_md()
        html = md.convert("## Heading Two")
        assert "heading-anchor" in html

    def test_h3_gets_anchor(self) -> None:
        """Test that h3 headings get anchor links."""
        md = self._make_md()
        html = md.convert("### Heading Three")
        assert "heading-anchor" in html

    def test_h4_gets_anchor(self) -> None:
        """Test that h4 headings get anchor links."""
        md = self._make_md()
        html = md.convert("#### Heading Four")
        assert "heading-anchor" in html

    def test_h5_gets_anchor(self) -> None:
        """Test that h5 headings get anchor links."""
        md = self._make_md()
        html = md.convert("##### Heading Five")
        assert "heading-anchor" in html

    def test_h6_gets_anchor(self) -> None:
        """Test that h6 headings get anchor links."""
        md = self._make_md()
        html = md.convert("###### Heading Six")
        assert "heading-anchor" in html

    def test_h1_does_not_get_anchor(self) -> None:
        """Test that h1 headings do not get anchor links."""
        md = self._make_md()
        html = md.convert("# Heading One")
        assert "heading-anchor" not in html

    def test_anchor_has_aria_label(self) -> None:
        """Test that the anchor link has an aria-label for accessibility."""
        md = self._make_md()
        html = md.convert("## My Section")
        assert 'aria-label="Link to this heading"' in html

    def test_multiple_headings_each_get_anchor(self) -> None:
        """Test that all headings in a document receive their own anchor."""
        md = self._make_md()
        html = md.convert("## First\n\n## Second\n\n### Third")
        assert 'href="#first"' in html
        assert 'href="#second"' in html
        assert 'href="#third"' in html
        assert html.count("heading-anchor") == 3

    def test_heading_with_inline_formatting_gets_anchor(self) -> None:
        """Test that headings with inline markup still get anchor links."""
        md = self._make_md()
        html = md.convert("## Hello **World**")
        assert "<strong>World</strong>" in html
        assert "heading-anchor" in html

    def test_non_heading_content_unaffected(self) -> None:
        """Test that regular paragraphs and other elements are not modified."""
        md = self._make_md()
        html = md.convert("This is a paragraph.\n\n## A Heading\n\nAnother paragraph.")
        assert html.count("heading-anchor") == 1

    def test_mixed_custom_and_auto_ids(self) -> None:
        """Test a document with both custom and auto-generated heading IDs."""
        md = markdown.Markdown(extensions=["toc", "attr_list", HeadingAnchorsExtension()])
        content = "## Custom Heading {#my-custom}\n\n## Auto Heading"
        html = md.convert(content)
        assert 'href="#my-custom"' in html
        assert 'href="#auto-heading"' in html
        assert html.count("heading-anchor") == 2

    def test_makeextension_factory(self) -> None:
        """Test that the makeExtension factory function works."""
        from blogmore.markdown.heading_anchors import makeExtension

        extension = makeExtension()
        assert isinstance(extension, HeadingAnchorsExtension)

    def test_processor_registration(self) -> None:
        """Test that the processor is registered with the correct name."""
        md = markdown.Markdown(extensions=[HeadingAnchorsExtension()])
        assert "heading_anchors" in md.treeprocessors

    def test_processor_runs_after_toc(self) -> None:
        """Test that the heading anchors processor runs after the toc processor.

        The registry is iterated from highest to lowest priority, so a higher
        index means the processor runs later (lower priority).
        """
        md = markdown.Markdown(extensions=["toc", HeadingAnchorsExtension()])
        tp = md.treeprocessors
        toc_index = tp.get_index_for_name("toc")
        anchor_index = tp.get_index_for_name("heading_anchors")
        # heading_anchors must have a lower sort priority (higher index) than toc
        assert anchor_index > toc_index


class TestHeadingAnchorsProcessor:
    """Tests for the HeadingAnchorsProcessor class directly."""

    def test_processor_returns_none(self) -> None:
        """Test that the run method returns None (in-place modification)."""
        import xml.etree.ElementTree as ET

        md = markdown.Markdown()
        processor = HeadingAnchorsProcessor(md)
        root = ET.fromstring("<div><h2 id='test'>Hello</h2></div>")
        result = processor.run(root)
        assert result is None

    def test_heading_without_id_is_not_modified(self) -> None:
        """Test that a heading without an ID attribute is left unchanged."""
        import xml.etree.ElementTree as ET

        md = markdown.Markdown()
        processor = HeadingAnchorsProcessor(md)
        root = ET.fromstring("<div><h2>No ID</h2></div>")
        processor.run(root)
        heading = root.find("h2")
        assert heading is not None
        assert list(heading) == []  # no children added

    def test_heading_with_id_gets_anchor_child(self) -> None:
        """Test that a heading with an ID receives an anchor child element."""
        import xml.etree.ElementTree as ET

        md = markdown.Markdown()
        processor = HeadingAnchorsProcessor(md)
        root = ET.fromstring("<div><h2 id='my-section'>Hello</h2></div>")
        processor.run(root)
        heading = root.find("h2")
        assert heading is not None
        children = list(heading)
        assert len(children) == 1
        anchor = children[0]
        assert anchor.tag == "a"
        assert anchor.get("class") == "heading-anchor"
        assert anchor.get("href") == "#my-section"
        assert anchor.text == ANCHOR_SYMBOL
