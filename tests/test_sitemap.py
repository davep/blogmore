"""Unit tests for the sitemap module."""

from pathlib import Path

from blogmore.parser import CUSTOM_404_HTML, CUSTOM_404_MARKDOWN
from blogmore.site_config import SiteConfig
from blogmore.sitemap import (
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

    def test_clean_urls_strips_index_html_from_nested_paths(
        self, tmp_path: Path
    ) -> None:
        """When clean_urls is True, index.html is stripped from nested paths."""
        post_dir = tmp_path / "posts" / "my-post"
        post_dir.mkdir(parents=True)
        (post_dir / "index.html").write_text("<html/>")

        urls = collect_sitemap_urls(tmp_path, "https://example.com", clean_urls=True)

        assert "https://example.com/posts/my-post/" in urls
        assert "https://example.com/posts/my-post/index.html" not in urls

    def test_clean_urls_false_keeps_index_html_in_nested_paths(
        self, tmp_path: Path
    ) -> None:
        """When clean_urls is False, index.html is kept in nested paths."""
        post_dir = tmp_path / "posts" / "my-post"
        post_dir.mkdir(parents=True)
        (post_dir / "index.html").write_text("<html/>")

        urls = collect_sitemap_urls(tmp_path, "https://example.com", clean_urls=False)

        assert "https://example.com/posts/my-post/index.html" in urls
        assert "https://example.com/posts/my-post/" not in urls

    def test_clean_urls_strips_index_html_from_root(self, tmp_path: Path) -> None:
        """When clean_urls is True, index.html at root becomes trailing slash."""
        (tmp_path / "index.html").write_text("<html/>")

        urls = collect_sitemap_urls(tmp_path, "https://example.com", clean_urls=True)

        # /index.html → / (but it's still included)
        assert "https://example.com/" in urls
        assert "https://example.com/index.html" not in urls

    def test_clean_urls_does_not_affect_non_index_html_files(
        self, tmp_path: Path
    ) -> None:
        """When clean_urls is True, non-index.html files are unaffected."""
        (tmp_path / "archive.html").write_text("<html/>")
        post_dir = tmp_path / "2024" / "01" / "15"
        post_dir.mkdir(parents=True)
        (post_dir / "my-post.html").write_text("<html/>")

        urls = collect_sitemap_urls(tmp_path, "https://example.com", clean_urls=True)

        assert "https://example.com/archive.html" in urls
        assert "https://example.com/2024/01/15/my-post.html" in urls

    def test_excludes_custom_search_path(self, tmp_path: Path) -> None:
        """Test that a custom search_path is excluded from the sitemap."""
        (tmp_path / "index.html").write_text("<html/>")
        custom_dir = tmp_path / "find"
        custom_dir.mkdir()
        (custom_dir / "index.html").write_text("<html/>")

        urls = collect_sitemap_urls(
            tmp_path, "https://example.com", search_path="find/index.html"
        )

        assert "https://example.com/index.html" in urls
        assert "https://example.com/find/index.html" not in urls

    def test_excludes_search_in_subdirectory(self, tmp_path: Path) -> None:
        """Test that a search page in a subdirectory is excluded."""
        (tmp_path / "index.html").write_text("<html/>")
        search_dir = tmp_path / "search"
        search_dir.mkdir()
        (search_dir / "index.html").write_text("<html/>")

        urls = collect_sitemap_urls(
            tmp_path, "https://example.com", search_path="search/index.html"
        )

        assert "https://example.com/index.html" in urls
        assert "https://example.com/search/index.html" not in urls
        assert "https://example.com/search/" not in urls

    def test_excludes_404_html(self, tmp_path: Path) -> None:
        """Test that 404.html is excluded from the sitemap."""
        (tmp_path / "index.html").write_text("<html/>")
        (tmp_path / CUSTOM_404_HTML).write_text("<html/>")

        urls = collect_sitemap_urls(tmp_path, "https://example.com")

        assert f"https://example.com/{CUSTOM_404_HTML}" not in urls
        assert "https://example.com/index.html" in urls

    def test_extra_excluded_paths_excludes_specified_html(
        self, tmp_path: Path
    ) -> None:
        """Test that HTML files in extra_excluded_paths are excluded."""
        (tmp_path / "index.html").write_text("<html/>")
        (tmp_path / "google287c4cf252478b0c.html").write_text("<html/>")

        urls = collect_sitemap_urls(
            tmp_path,
            "https://example.com",
            extra_excluded_paths=frozenset({"google287c4cf252478b0c.html"}),
        )

        assert "https://example.com/google287c4cf252478b0c.html" not in urls
        assert "https://example.com/index.html" in urls

    def test_extra_excluded_paths_excludes_nested_html(self, tmp_path: Path) -> None:
        """Test that nested HTML files in extra_excluded_paths are excluded."""
        (tmp_path / "index.html").write_text("<html/>")
        verify_dir = tmp_path / "verify"
        verify_dir.mkdir()
        (verify_dir / "token.html").write_text("<html/>")

        urls = collect_sitemap_urls(
            tmp_path,
            "https://example.com",
            extra_excluded_paths=frozenset({"verify/token.html"}),
        )

        assert "https://example.com/verify/token.html" not in urls
        assert "https://example.com/index.html" in urls

    def test_extra_excluded_paths_empty_frozenset_has_no_effect(
        self, tmp_path: Path
    ) -> None:
        """Test that an empty extra_excluded_paths has no effect."""
        (tmp_path / "index.html").write_text("<html/>")
        (tmp_path / "archive.html").write_text("<html/>")

        urls = collect_sitemap_urls(
            tmp_path,
            "https://example.com",
            extra_excluded_paths=frozenset(),
        )

        assert "https://example.com/index.html" in urls
        assert "https://example.com/archive.html" in urls

    def test_extra_urls_are_appended(self, tmp_path: Path) -> None:
        """Test that extra_urls are appended to the collected URLs."""
        (tmp_path / "index.html").write_text("<html/>")

        urls = collect_sitemap_urls(
            tmp_path,
            "https://example.com",
            extra_urls=["/some/path/", "/some/file.html"],
        )

        assert "https://example.com/index.html" in urls
        assert "https://example.com/some/path/" in urls
        assert "https://example.com/some/file.html" in urls

    def test_extra_urls_none_has_no_effect(self, tmp_path: Path) -> None:
        """Test that extra_urls=None does not add any extra URLs."""
        (tmp_path / "index.html").write_text("<html/>")

        urls_without = collect_sitemap_urls(tmp_path, "https://example.com")
        urls_with_none = collect_sitemap_urls(
            tmp_path, "https://example.com", extra_urls=None
        )

        assert urls_without == urls_with_none

    def test_extra_urls_empty_list_has_no_effect(self, tmp_path: Path) -> None:
        """Test that extra_urls=[] does not add any extra URLs."""
        (tmp_path / "index.html").write_text("<html/>")

        urls_without = collect_sitemap_urls(tmp_path, "https://example.com")
        urls_with_empty = collect_sitemap_urls(
            tmp_path, "https://example.com", extra_urls=[]
        )

        assert urls_without == urls_with_empty

    def test_extra_urls_without_leading_slash_are_normalised(
        self, tmp_path: Path
    ) -> None:
        """Test that extra_urls without a leading slash are normalised correctly."""
        (tmp_path / "index.html").write_text("<html/>")

        urls = collect_sitemap_urls(
            tmp_path,
            "https://example.com",
            extra_urls=["some/path/"],
        )

        assert "https://example.com/some/path/" in urls

    def test_extra_urls_included_in_sorted_output(self, tmp_path: Path) -> None:
        """Test that the final URL list (including extras) is sorted."""
        (tmp_path / "zzz.html").write_text("<html/>")

        urls = collect_sitemap_urls(
            tmp_path,
            "https://example.com",
            extra_urls=["/aaa/path/"],
        )

        assert urls == sorted(urls)


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

    def test_write_sitemap_clean_urls_strips_index_html(self, tmp_path: Path) -> None:
        """When clean_urls is True, write_sitemap produces clean URLs."""
        post_dir = tmp_path / "posts" / "my-post"
        post_dir.mkdir(parents=True)
        (post_dir / "index.html").write_text("<html/>")

        write_sitemap(tmp_path, "https://example.com", clean_urls=True)

        content = (tmp_path / SITEMAP_FILENAME).read_text()
        assert "https://example.com/posts/my-post/" in content
        assert "https://example.com/posts/my-post/index.html" not in content

    def test_write_sitemap_extra_urls_are_included(self, tmp_path: Path) -> None:
        """Test that extra_urls are included in the written sitemap."""
        (tmp_path / "index.html").write_text("<html/>")

        write_sitemap(
            tmp_path,
            "https://example.com",
            extra_urls=["/some/path/", "/some/file.html"],
        )

        content = (tmp_path / SITEMAP_FILENAME).read_text()
        assert "https://example.com/some/path/" in content
        assert "https://example.com/some/file.html" in content

    def test_write_sitemap_without_extra_urls(self, tmp_path: Path) -> None:
        """Test that omitting extra_urls does not add any extra URLs to the sitemap."""
        (tmp_path / "index.html").write_text("<html/>")

        write_sitemap(tmp_path, "https://example.com", extra_urls=None)

        content = (tmp_path / SITEMAP_FILENAME).read_text()
        assert content.count("<url>") == 1


class TestSitemapIntegrationWithGenerator:
    """Integration tests for sitemap generation via SiteGenerator."""

    def test_sitemap_not_generated_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that sitemap.xml is not generated when with_sitemap is False."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                with_sitemap=False,
            )
        )
        generator.generate()

        assert not (temp_output_dir / "sitemap.xml").exists()

    def test_sitemap_generated_when_enabled(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that sitemap.xml is generated when with_sitemap is True."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                with_sitemap=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "sitemap.xml").exists()

    def test_sitemap_contains_post_urls(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the sitemap contains post URLs."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                with_sitemap=True,
            )
        )
        generator.generate()

        content = (temp_output_dir / "sitemap.xml").read_text()
        # The fixture has a post dated 2024-01-15
        assert "https://example.com/2024/01/15/first-post.html" in content

    def test_sitemap_excludes_search_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that search.html is excluded from the sitemap."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                with_sitemap=True,
                with_search=True,
            )
        )
        generator.generate()

        content = (temp_output_dir / "sitemap.xml").read_text()
        assert "search.html" not in content

    def test_sitemap_contains_index_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the sitemap contains the index page."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                with_sitemap=True,
            )
        )
        generator.generate()

        content = (temp_output_dir / "sitemap.xml").read_text()
        assert "https://example.com/index.html" in content

    def test_sitemap_excludes_404_html(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that 404.html is excluded from the sitemap."""
        from blogmore.generator import SiteGenerator

        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_dir = content_dir / "pages"
        pages_dir.mkdir()
        (pages_dir / CUSTOM_404_MARKDOWN).write_text(
            "---\ntitle: Page Not Found\n---\n\nSorry, page not found."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                with_sitemap=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / CUSTOM_404_HTML).exists()
        content = (temp_output_dir / "sitemap.xml").read_text()
        assert CUSTOM_404_HTML not in content

    def test_sitemap_excludes_custom_search_path(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that a custom search_path is excluded from the sitemap."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                with_sitemap=True,
                with_search=True,
                search_path="find/index.html",
            )
        )
        generator.generate()

        content = (temp_output_dir / "sitemap.xml").read_text()
        assert "find/index.html" not in content
        assert "find/" not in content

    def test_sitemap_excludes_html_from_extras(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that HTML files copied from extras are excluded from the sitemap."""
        from blogmore.generator import SiteGenerator

        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        (extras_dir / "google287c4cf252478b0c.html").write_text(
            "google-site-verification: google287c4cf252478b0c.html"
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                with_sitemap=True,
            )
        )
        generator.generate()

        # The extras HTML file should be present in the output but absent from the sitemap
        assert (temp_output_dir / "google287c4cf252478b0c.html").exists()
        content = (temp_output_dir / "sitemap.xml").read_text()
        assert "google287c4cf252478b0c.html" not in content

    def test_sitemap_excludes_nested_html_from_extras(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that nested HTML files in extras are excluded from the sitemap."""
        from blogmore.generator import SiteGenerator

        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        verify_dir = extras_dir / "verify"
        verify_dir.mkdir()
        (verify_dir / "token.html").write_text("<html>verification</html>")

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                with_sitemap=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "verify" / "token.html").exists()
        content = (temp_output_dir / "sitemap.xml").read_text()
        assert "verify/token.html" not in content

    def test_sitemap_includes_non_html_extras_normally(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that non-HTML extras files do not affect the sitemap."""
        from blogmore.generator import SiteGenerator

        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        (extras_dir / "robots.txt").write_text("User-agent: *\nDisallow:")

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                with_sitemap=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "robots.txt").exists()
        content = (temp_output_dir / "sitemap.xml").read_text()
        assert "robots.txt" not in content

    def test_sitemap_includes_sitemap_extras(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that sitemap_extras URLs are included in the sitemap."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                with_sitemap=True,
                sitemap_extras=["/some/path/", "/some/file.html"],
            )
        )
        generator.generate()

        content = (temp_output_dir / "sitemap.xml").read_text()
        assert "https://example.com/some/path/" in content
        assert "https://example.com/some/file.html" in content

    def test_sitemap_extras_none_does_not_add_extra_urls(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that sitemap_extras=None does not add unexpected URLs."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                with_sitemap=True,
                sitemap_extras=None,
            )
        )
        generator.generate()

        content = (temp_output_dir / "sitemap.xml").read_text()
        assert "/some/path/" not in content
        assert "/some/file.html" not in content
