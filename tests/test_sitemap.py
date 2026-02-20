"""Unit tests for the sitemap module."""

from pathlib import Path

import pytest

from blogmore.sitemap import (
    EXCLUDED_PAGES,
    SITEMAP_FILENAME,
    SITEMAP_XMLNS,
    collect_sitemap_urls,
    generate_sitemap_xml,
    write_sitemap,
)


class TestCollectSitemapUrls:
    """Test the collect_sitemap_urls function."""

    def test_collects_html_files(self, tmp_path: Path) -> None:
        """Test that HTML files are collected."""
        (tmp_path / "index.html").write_text("<html/>")
        (tmp_path / "archive.html").write_text("<html/>")

        urls = collect_sitemap_urls(tmp_path, "https://example.com")

        assert "https://example.com/index.html" in urls
        assert "https://example.com/archive.html" in urls

    def test_excludes_search_html(self, tmp_path: Path) -> None:
        """Test that search.html is excluded."""
        (tmp_path / "index.html").write_text("<html/>")
        (tmp_path / "search.html").write_text("<html/>")

        urls = collect_sitemap_urls(tmp_path, "https://example.com")

        assert "https://example.com/search.html" not in urls
        assert "https://example.com/index.html" in urls

    def test_collects_nested_html_files(self, tmp_path: Path) -> None:
        """Test that nested HTML files are collected."""
        post_dir = tmp_path / "2024" / "01" / "15"
        post_dir.mkdir(parents=True)
        (post_dir / "my-post.html").write_text("<html/>")

        urls = collect_sitemap_urls(tmp_path, "https://example.com")

        assert "https://example.com/2024/01/15/my-post.html" in urls

    def test_uses_fallback_url_when_site_url_empty(self, tmp_path: Path) -> None:
        """Test that fallback URL is used when site_url is empty."""
        (tmp_path / "index.html").write_text("<html/>")

        urls = collect_sitemap_urls(tmp_path, "")

        assert any(url.startswith("https://example.com/") for url in urls)

    def test_normalizes_trailing_slash_in_site_url(self, tmp_path: Path) -> None:
        """Test that trailing slash is removed from site_url."""
        (tmp_path / "index.html").write_text("<html/>")

        urls = collect_sitemap_urls(tmp_path, "https://example.com/")

        assert "https://example.com/index.html" in urls
        assert "https://example.com//index.html" not in urls

    def test_returns_sorted_urls(self, tmp_path: Path) -> None:
        """Test that returned URLs are sorted."""
        (tmp_path / "zzz.html").write_text("<html/>")
        (tmp_path / "aaa.html").write_text("<html/>")
        (tmp_path / "mmm.html").write_text("<html/>")

        urls = collect_sitemap_urls(tmp_path, "https://example.com")

        assert urls == sorted(urls)

    def test_empty_output_dir(self, tmp_path: Path) -> None:
        """Test with an empty output directory returns empty list."""
        urls = collect_sitemap_urls(tmp_path, "https://example.com")

        assert urls == []

    def test_non_html_files_excluded(self, tmp_path: Path) -> None:
        """Test that non-HTML files are not collected."""
        (tmp_path / "feed.xml").write_text("<rss/>")
        (tmp_path / "search_index.json").write_text("{}")
        (tmp_path / "style.css").write_text("body {}")
        (tmp_path / "index.html").write_text("<html/>")

        urls = collect_sitemap_urls(tmp_path, "https://example.com")

        assert len(urls) == 1
        assert "https://example.com/index.html" in urls

    def test_all_excluded_pages_constants(self) -> None:
        """Test that the EXCLUDED_PAGES constant contains search.html."""
        assert "search.html" in EXCLUDED_PAGES


class TestGenerateSitemapXml:
    """Test the generate_sitemap_xml function."""

    def test_generates_valid_xml_declaration(self) -> None:
        """Test that the XML declaration is present."""
        xml = generate_sitemap_xml([])

        assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    def test_contains_urlset_element(self) -> None:
        """Test that the urlset element is present with correct namespace."""
        xml = generate_sitemap_xml([])

        assert "urlset" in xml
        assert SITEMAP_XMLNS in xml

    def test_includes_url_entries(self) -> None:
        """Test that URL entries are included."""
        urls = [
            "https://example.com/index.html",
            "https://example.com/archive.html",
        ]

        xml = generate_sitemap_xml(urls)

        assert "https://example.com/index.html" in xml
        assert "https://example.com/archive.html" in xml

    def test_url_wrapped_in_loc(self) -> None:
        """Test that URLs are wrapped in <loc> elements."""
        xml = generate_sitemap_xml(["https://example.com/index.html"])

        assert "<loc>https://example.com/index.html</loc>" in xml

    def test_empty_urls_produces_valid_xml(self) -> None:
        """Test that empty URL list produces valid XML with empty urlset."""
        xml = generate_sitemap_xml([])

        assert "urlset" in xml
        assert "<url>" not in xml

    def test_xml_escaping_in_urls(self) -> None:
        """Test that special characters in URLs are properly escaped."""
        # URLs with & (e.g. query strings) should be escaped to &amp;
        xml = generate_sitemap_xml(["https://example.com/page.html?a=1&b=2"])

        assert "&amp;" in xml
        assert "https://example.com/page.html?a=1" in xml


class TestWriteSitemap:
    """Test the write_sitemap function."""

    def test_creates_sitemap_file(self, tmp_path: Path) -> None:
        """Test that sitemap.xml is created."""
        (tmp_path / "index.html").write_text("<html/>")

        write_sitemap(tmp_path, "https://example.com")

        assert (tmp_path / SITEMAP_FILENAME).exists()

    def test_sitemap_contains_page_urls(self, tmp_path: Path) -> None:
        """Test that the sitemap contains URLs for all pages."""
        (tmp_path / "index.html").write_text("<html/>")
        (tmp_path / "archive.html").write_text("<html/>")

        write_sitemap(tmp_path, "https://example.com")

        content = (tmp_path / SITEMAP_FILENAME).read_text()
        assert "https://example.com/index.html" in content
        assert "https://example.com/archive.html" in content

    def test_sitemap_excludes_search_html(self, tmp_path: Path) -> None:
        """Test that search.html is excluded from the sitemap."""
        (tmp_path / "index.html").write_text("<html/>")
        (tmp_path / "search.html").write_text("<html/>")

        write_sitemap(tmp_path, "https://example.com")

        content = (tmp_path / SITEMAP_FILENAME).read_text()
        assert "search.html" not in content
        assert "https://example.com/index.html" in content

    def test_sitemap_written_to_output_root(self, tmp_path: Path) -> None:
        """Test that sitemap.xml is written to the root of the output directory."""
        write_sitemap(tmp_path, "https://example.com")

        sitemap_path = tmp_path / "sitemap.xml"
        assert sitemap_path.exists()

    def test_sitemap_is_utf8_encoded(self, tmp_path: Path) -> None:
        """Test that the sitemap file is UTF-8 encoded."""
        (tmp_path / "index.html").write_text("<html/>")

        write_sitemap(tmp_path, "https://example.com")

        # Reading as UTF-8 should not raise an error
        content = (tmp_path / SITEMAP_FILENAME).read_text(encoding="utf-8")
        assert content


class TestSitemapIntegrationWithGenerator:
    """Integration tests for sitemap generation via SiteGenerator."""

    def test_sitemap_not_generated_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that sitemap.xml is not generated when with_sitemap is False."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_url="https://example.com",
            with_sitemap=False,
        )
        generator.generate(include_drafts=False)

        assert not (temp_output_dir / "sitemap.xml").exists()

    def test_sitemap_generated_when_enabled(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that sitemap.xml is generated when with_sitemap is True."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_url="https://example.com",
            with_sitemap=True,
        )
        generator.generate(include_drafts=False)

        assert (temp_output_dir / "sitemap.xml").exists()

    def test_sitemap_contains_post_urls(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the sitemap contains post URLs."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_url="https://example.com",
            with_sitemap=True,
        )
        generator.generate(include_drafts=False)

        content = (temp_output_dir / "sitemap.xml").read_text()
        # The fixture has a post dated 2024-01-15
        assert "https://example.com/2024/01/15/first-post.html" in content

    def test_sitemap_excludes_search_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that search.html is excluded from the sitemap."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_url="https://example.com",
            with_sitemap=True,
            with_search=True,
        )
        generator.generate(include_drafts=False)

        content = (temp_output_dir / "sitemap.xml").read_text()
        assert "search.html" not in content

    def test_sitemap_contains_index_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the sitemap contains the index page."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_url="https://example.com",
            with_sitemap=True,
        )
        generator.generate(include_drafts=False)

        content = (temp_output_dir / "sitemap.xml").read_text()
        assert "https://example.com/index.html" in content
