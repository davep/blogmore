"""Unit tests for the external_links module."""

import markdown

from blogmore.external_links import ExternalLinksExtension, ExternalLinksProcessor


class TestExternalLinksProcessor:
    """Test the ExternalLinksProcessor class."""

    def test_is_external_link_absolute_external(self) -> None:
        """Test that absolute external URLs are identified correctly."""
        processor = ExternalLinksProcessor(None, site_url="https://example.com")
        assert processor._is_external_link("https://external.com/page")
        assert processor._is_external_link("http://external.com/page")

    def test_is_external_link_relative(self) -> None:
        """Test that relative URLs are identified as internal."""
        processor = ExternalLinksProcessor(None, site_url="https://example.com")
        assert not processor._is_external_link("/posts/my-post")
        assert not processor._is_external_link("posts/my-post")
        assert not processor._is_external_link("../posts/my-post")

    def test_is_external_link_anchor(self) -> None:
        """Test that anchor links are identified as internal."""
        processor = ExternalLinksProcessor(None, site_url="https://example.com")
        assert not processor._is_external_link("#section")
        assert not processor._is_external_link("#top")

    def test_is_external_link_same_domain(self) -> None:
        """Test that links to the same domain are identified as internal."""
        processor = ExternalLinksProcessor(None, site_url="https://example.com")
        assert not processor._is_external_link("https://example.com/page")
        assert not processor._is_external_link("https://www.example.com/page")

    def test_is_external_link_no_site_url(self) -> None:
        """Test external link detection when no site URL is configured."""
        processor = ExternalLinksProcessor(None, site_url=None)
        # With no site URL, all absolute URLs are considered external
        assert processor._is_external_link("https://example.com/page")
        # Relative links are still internal
        assert not processor._is_external_link("/page")
        assert not processor._is_external_link("page")

    def test_is_external_link_with_subdomain(self) -> None:
        """Test that different subdomains are treated as external."""
        processor = ExternalLinksProcessor(None, site_url="https://example.com")
        # Different subdomain should be external
        assert processor._is_external_link("https://blog.example.com/page")
        # Note: www is treated as the same as no subdomain
        assert not processor._is_external_link("https://www.example.com/page")


class TestExternalLinksExtension:
    """Test the ExternalLinksExtension with markdown."""

    def test_external_link_gets_target_blank(self) -> None:
        """Test that external links get target='_blank' attribute."""
        md = markdown.Markdown(
            extensions=[ExternalLinksExtension(site_url="https://example.com")]
        )
        html = md.convert("[External link](https://external.com)")
        assert 'target="_blank"' in html
        assert 'rel="noopener noreferrer"' in html

    def test_internal_link_no_target(self) -> None:
        """Test that internal links do not get target='_blank' attribute."""
        md = markdown.Markdown(
            extensions=[ExternalLinksExtension(site_url="https://example.com")]
        )
        html = md.convert("[Internal link](/posts/my-post)")
        assert 'target="_blank"' not in html
        assert 'rel="noopener noreferrer"' not in html

    def test_anchor_link_no_target(self) -> None:
        """Test that anchor links do not get target='_blank' attribute."""
        md = markdown.Markdown(
            extensions=[ExternalLinksExtension(site_url="https://example.com")]
        )
        html = md.convert("[Anchor link](#section)")
        assert 'target="_blank"' not in html
        assert 'rel="noopener noreferrer"' not in html

    def test_same_domain_link_no_target(self) -> None:
        """Test that links to same domain do not get target='_blank'."""
        md = markdown.Markdown(
            extensions=[ExternalLinksExtension(site_url="https://example.com")]
        )
        html = md.convert("[Same domain](https://example.com/page)")
        assert 'target="_blank"' not in html
        assert 'rel="noopener noreferrer"' not in html

    def test_multiple_links_mixed(self) -> None:
        """Test document with both internal and external links."""
        md = markdown.Markdown(
            extensions=[ExternalLinksExtension(site_url="https://example.com")]
        )
        text = """[Internal](/posts/my-post)
[External](https://external.com)
[Anchor](#top)
[Another External](https://another.com/page)
"""
        html = md.convert(text)

        # Count occurrences of target="_blank"
        # Should be 2 (for the two external links)
        assert html.count('target="_blank"') == 2
        assert html.count('rel="noopener noreferrer"') == 2

    def test_no_site_url_all_absolute_external(self) -> None:
        """Test that without site URL, all absolute URLs are treated as external."""
        md = markdown.Markdown(extensions=[ExternalLinksExtension(site_url="")])
        html = md.convert("[Link](https://example.com)")
        assert 'target="_blank"' in html
        assert 'rel="noopener noreferrer"' in html

    def test_relative_link_without_site_url(self) -> None:
        """Test that relative links are still internal without site URL."""
        md = markdown.Markdown(extensions=[ExternalLinksExtension(site_url="")])
        html = md.convert("[Link](/page)")
        assert 'target="_blank"' not in html
        assert 'rel="noopener noreferrer"' not in html

    def test_link_in_paragraph(self) -> None:
        """Test external links within paragraphs."""
        md = markdown.Markdown(
            extensions=[ExternalLinksExtension(site_url="https://example.com")]
        )
        html = md.convert("Check out [this site](https://external.com) for more info.")
        assert 'target="_blank"' in html
        assert 'rel="noopener noreferrer"' in html
        assert "<p>" in html  # Ensure paragraph structure is preserved

    def test_link_in_list(self) -> None:
        """Test external links within lists."""
        md = markdown.Markdown(
            extensions=[ExternalLinksExtension(site_url="https://example.com")]
        )
        text = """- [Internal link](/page)
- [External link](https://external.com)
"""
        html = md.convert(text)
        assert html.count('target="_blank"') == 1
        assert html.count('rel="noopener noreferrer"') == 1

    def test_empty_href(self) -> None:
        """Test that empty hrefs are handled gracefully."""
        md = markdown.Markdown(
            extensions=[ExternalLinksExtension(site_url="https://example.com")]
        )
        # This is valid markdown but unusual
        html = md.convert("[Empty link]()")
        # Should not crash, and empty links should not get target="_blank"
        assert 'target="_blank"' not in html
