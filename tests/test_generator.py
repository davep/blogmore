"""Unit tests for the generator module."""

import re
import shutil
import time
from pathlib import Path

import pytest

from blogmore.generator import (
    ARCHIVE_CSS_FILENAME,
    SEARCH_CSS_FILENAME,
    STATS_CSS_FILENAME,
    TAG_CLOUD_CSS_FILENAME,
    SiteGenerator,
    minified_filename,
    paginate_posts,
    sanitize_for_url,
)
from blogmore.parser import CUSTOM_404_HTML, CUSTOM_404_MARKDOWN, Page, Post
from blogmore.site_config import SiteConfig


class TestSanitizeForUrl:
    """Test the sanitize_for_url function."""

    def test_sanitize_basic(self) -> None:
        """Test basic string sanitization."""
        assert sanitize_for_url("Hello World") == "hello-world"

    def test_sanitize_special_chars(self) -> None:
        """Test sanitizing special characters."""
        assert sanitize_for_url("C++ & Java") == "c-java"

    def test_sanitize_empty(self) -> None:
        """Test empty string returns 'unnamed'."""
        assert sanitize_for_url("") == "unnamed"


class TestMinifiedFilename:
    """Test the minified_filename utility function."""

    def test_css_extension_becomes_min_css(self) -> None:
        """Test that a .css extension is replaced with .min.css."""
        assert minified_filename("style.css") == "style.min.css"

    def test_js_extension_becomes_min_js(self) -> None:
        """Test that a .js extension is replaced with .min.js."""
        assert minified_filename("theme.js") == "theme.min.js"

    def test_hyphenated_css_filename(self) -> None:
        """Test that a hyphenated CSS filename is handled correctly."""
        assert minified_filename("tag-cloud.css") == "tag-cloud.min.css"

    def test_hyphenated_js_filename(self) -> None:
        """Test that a hyphenated JS filename is handled correctly."""
        assert minified_filename("search.js") == "search.min.js"

    def test_unsupported_extension_raises(self) -> None:
        """Test that an unsupported extension raises ValueError."""
        import pytest

        with pytest.raises(ValueError, match="Unsupported file extension"):
            minified_filename("style.txt")


class TestPaginatePosts:
    """Test the paginate_posts function."""

    def test_paginate_empty_list(self) -> None:
        """Test paginating empty list."""
        assert paginate_posts([], 10) == []

    def test_paginate_single_page(self, sample_post: Post) -> None:
        """Test paginating when all posts fit on one page."""
        posts = [sample_post] * 5
        pages = paginate_posts(posts, 10)

        assert len(pages) == 1
        assert len(pages[0]) == 5

    def test_paginate_multiple_pages(self, sample_post: Post) -> None:
        """Test paginating across multiple pages."""
        posts = [sample_post] * 25
        pages = paginate_posts(posts, 10)

        assert len(pages) == 3
        assert len(pages[0]) == 10
        assert len(pages[1]) == 10
        assert len(pages[2]) == 5

    def test_paginate_exact_fit(self, sample_post: Post) -> None:
        """Test paginating when posts exactly fit pages."""
        posts = [sample_post] * 20
        pages = paginate_posts(posts, 10)

        assert len(pages) == 2
        assert len(pages[0]) == 10
        assert len(pages[1]) == 10

    def test_paginate_zero_per_page(self, sample_post: Post) -> None:
        """Test paginating with zero posts per page returns all posts."""
        posts = [sample_post] * 5
        pages = paginate_posts(posts, 0)

        assert len(pages) == 1
        assert len(pages[0]) == 5

    def test_paginate_negative_per_page(self, sample_post: Post) -> None:
        """Test paginating with negative posts per page returns all posts."""
        posts = [sample_post] * 5
        pages = paginate_posts(posts, -1)

        assert len(pages) == 1
        assert len(pages[0]) == 5


class TestSiteGenerator:
    """Test the SiteGenerator class."""

    def test_resolve_sidebar_pages_no_config(
        self, sample_page: Page, temp_output_dir: Path
    ) -> None:
        """Test _resolve_sidebar_pages returns all pages when sidebar_pages is None."""
        page2 = Page(
            path=Path("tools.md"),
            title="My Tools",
            content="Tools content.",
            html_content="<p>Tools content.</p>",
        )
        pages = [sample_page, page2]

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=temp_output_dir,
                output_dir=temp_output_dir,
                sidebar_pages=None,
            )
        )

        result = generator._resolve_sidebar_pages(pages)
        assert result == pages

    def test_resolve_sidebar_pages_empty_list(
        self, sample_page: Page, temp_output_dir: Path
    ) -> None:
        """Test _resolve_sidebar_pages returns all pages when sidebar_pages is empty."""
        pages = [sample_page]

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=temp_output_dir,
                output_dir=temp_output_dir,
                sidebar_pages=[],
            )
        )

        result = generator._resolve_sidebar_pages(pages)
        assert result == pages

    def test_resolve_sidebar_pages_filters_to_listed_slugs(
        self, sample_page: Page, temp_output_dir: Path
    ) -> None:
        """Test _resolve_sidebar_pages keeps only pages with matching slugs."""
        page2 = Page(
            path=Path("tools.md"),
            title="My Tools",
            content="Tools content.",
            html_content="<p>Tools content.</p>",
        )
        pages = [sample_page, page2]  # slugs: "about", "tools"

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=temp_output_dir,
                output_dir=temp_output_dir,
                sidebar_pages=["tools"],
            )
        )

        result = generator._resolve_sidebar_pages(pages)
        assert result == [page2]

    def test_resolve_sidebar_pages_respects_order(
        self, sample_page: Page, temp_output_dir: Path
    ) -> None:
        """Test _resolve_sidebar_pages returns pages in the order of sidebar_pages."""
        page2 = Page(
            path=Path("tools.md"),
            title="My Tools",
            content="Tools content.",
            html_content="<p>Tools content.</p>",
        )
        pages = [sample_page, page2]  # slugs: "about", "tools"

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=temp_output_dir,
                output_dir=temp_output_dir,
                sidebar_pages=["tools", "about"],
            )
        )

        result = generator._resolve_sidebar_pages(pages)
        assert result == [page2, sample_page]

    def test_resolve_sidebar_pages_ignores_unknown_slugs(
        self, sample_page: Page, temp_output_dir: Path
    ) -> None:
        """Test _resolve_sidebar_pages silently ignores unknown slugs."""
        pages = [sample_page]  # slug: "about"

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=temp_output_dir,
                output_dir=temp_output_dir,
                sidebar_pages=["about", "does-not-exist"],
            )
        )

        result = generator._resolve_sidebar_pages(pages)
        assert result == [sample_page]

    def test_init(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test initializing SiteGenerator."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_title="Test Blog",
                site_url="https://example.com",
            )
        )

        assert generator.site_config.content_dir == posts_dir
        assert generator.site_config.output_dir == temp_output_dir
        assert generator.site_config.site_title == "Test Blog"
        assert generator.site_config.site_url == "https://example.com"

    def test_init_normalizes_trailing_slash(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that SiteGenerator normalizes site_url with trailing slash."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_title="Test Blog",
                site_url="https://example.com/",
            )
        )

        # Trailing slash should be removed
        assert generator.site_config.site_url == "https://example.com"

    def test_init_with_custom_templates(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test initializing with custom templates directory."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                templates_dir=templates_dir,
                output_dir=temp_output_dir,
            )
        )

        assert generator.site_config.templates_dir == templates_dir

    def test_generate_basic(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test basic site generation."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_title="Test Blog",
                site_url="https://example.com",
            )
        )

        generator.generate()

        # Check that output directory has expected structure
        assert temp_output_dir.exists()
        assert (temp_output_dir / "index.html").exists()
        assert (temp_output_dir / "static").exists()
        assert (temp_output_dir / "static" / "style.css").exists()

    def test_generate_with_relative_output_dir(
        self, posts_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that generation works correctly when output_dir is a relative path.

        Regression test for the bug where using a relative output directory
        caused a ValueError from Path.relative_to() because compute_output_path
        returns an absolute path while output_dir remained relative.
        """
        monkeypatch.chdir(tmp_path)
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=Path("site"),
            )
        )
        # This must not raise a ValueError about relative_to()
        generator.generate()

        absolute_output = tmp_path / "site"
        assert absolute_output.exists()
        assert (absolute_output / "index.html").exists()

    def test_generate_with_drafts(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test generating site including drafts."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=temp_output_dir, include_drafts=True
            )
        )

        generator.generate()

        # Should generate successfully with drafts
        assert (temp_output_dir / "index.html").exists()

    def test_generate_creates_post_files(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that individual post HTML files are created."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        # Check that post files exist with date-based structure
        # The first-post.md has date 2024-01-15
        post_file = temp_output_dir / "2024" / "01" / "15" / "first-post.html"
        assert post_file.exists()

        # Check content
        content = post_file.read_text()
        assert "My First Post" in content

    def test_generate_creates_archive(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that archive page is created."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        assert (temp_output_dir / "archive.html").exists()

    def test_generate_creates_tag_pages(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that tag pages are created."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        # Check for tag directory
        tag_dir = temp_output_dir / "tag"
        assert tag_dir.exists()

        # Check for specific tag pages (python tag exists in fixtures)
        assert (tag_dir / "python" / "index.html").exists()

    def test_generate_creates_category_pages(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that category pages are created."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        # Check for category directory
        category_dir = temp_output_dir / "category"
        assert category_dir.exists()

        # Check for specific category pages (python category exists in fixtures)
        assert (category_dir / "python" / "index.html").exists()

    def test_generate_creates_feeds(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that RSS and Atom feeds are created."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
            )
        )

        generator.generate()

        # Check for main feed
        assert (temp_output_dir / "feed.xml").exists()

        # Check for atom feed
        assert (temp_output_dir / "feeds" / "all.atom.xml").exists()

    def test_generate_copies_static_files(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that static files are copied."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        # Check that static directory exists with CSS
        assert (temp_output_dir / "static" / "style.css").exists()

    def test_generate_with_pages(
        self, posts_dir: Path, pages_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test generating site with static pages."""
        # Create a content directory with both posts and pages
        import shutil

        content_dir = temp_output_dir.parent / "content"
        content_dir.mkdir(exist_ok=True)

        # Copy posts
        posts_dest = content_dir / "posts"
        if posts_dest.exists():
            shutil.rmtree(posts_dest)
        shutil.copytree(posts_dir, posts_dest)

        # Copy pages
        pages_dest = content_dir / "pages"
        if pages_dest.exists():
            shutil.rmtree(pages_dest)
        shutil.copytree(pages_dir, pages_dest)

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        # Check that page was generated
        assert (temp_output_dir / "about.html").exists()

        # Check that pages are not included in the main post listing.
        # Pages appear in sidebar navigation (expected), but must NOT be rendered
        # as post articles in index or archive views.
        # The posts fixture has 7 non-draft posts; the 2 pages in pages_dir
        # must not inflate this count to 9.
        index_content = (temp_output_dir / "index.html").read_text()
        assert index_content.count('<article class="post-summary">') == 7

    def test_generate_with_sidebar_pages_filter(
        self, posts_dir: Path, pages_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that sidebar_pages limits which pages appear in the sidebar."""
        content_dir = temp_output_dir.parent / "content_sb"
        content_dir.mkdir(exist_ok=True)

        # Copy posts
        posts_dest = content_dir / "posts"
        if posts_dest.exists():
            shutil.rmtree(posts_dest)
        shutil.copytree(posts_dir, posts_dest)

        # Copy pages
        pages_dest = content_dir / "pages"
        if pages_dest.exists():
            shutil.rmtree(pages_dest)
        shutil.copytree(pages_dir, pages_dest)

        # Only show "about" in the sidebar (not "seo-test-page")
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                sidebar_pages=["about"],
            )
        )

        generator.generate()

        # Both pages must still be generated as HTML files.
        assert (temp_output_dir / "about.html").exists()
        assert (temp_output_dir / "seo-test-page.html").exists()

        # Only the listed page appears in the sidebar of the index.
        index_content = (temp_output_dir / "index.html").read_text()
        assert "About Me" in index_content
        assert "SEO Test Page" not in index_content

    def test_generate_with_sidebar_pages_order(
        self, posts_dir: Path, pages_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that sidebar_pages controls the order of pages in the sidebar."""
        content_dir = temp_output_dir.parent / "content_order"
        content_dir.mkdir(exist_ok=True)

        posts_dest = content_dir / "posts"
        if posts_dest.exists():
            shutil.rmtree(posts_dest)
        shutil.copytree(posts_dir, posts_dest)

        pages_dest = content_dir / "pages"
        if pages_dest.exists():
            shutil.rmtree(pages_dest)
        shutil.copytree(pages_dir, pages_dest)

        # Request "seo-test-page" before "about"
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                sidebar_pages=["seo-test-page", "about"],
            )
        )

        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        seo_pos = index_content.find("SEO Test Page")
        about_pos = index_content.find("About Me")
        assert seo_pos != -1
        assert about_pos != -1
        assert seo_pos < about_pos, (
            "SEO Test Page should appear before About Me in the sidebar"
        )

    def test_generate_with_sidebar_pages_unknown_slug_ignored(
        self, posts_dir: Path, pages_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that unknown slugs in sidebar_pages are silently ignored."""
        content_dir = temp_output_dir.parent / "content_unk"
        content_dir.mkdir(exist_ok=True)

        posts_dest = content_dir / "posts"
        if posts_dest.exists():
            shutil.rmtree(posts_dest)
        shutil.copytree(posts_dir, posts_dest)

        pages_dest = content_dir / "pages"
        if pages_dest.exists():
            shutil.rmtree(pages_dest)
        shutil.copytree(pages_dir, pages_dest)

        # Include a slug that does not exist; the generator must not raise.
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                sidebar_pages=["about", "nonexistent-page"],
            )
        )

        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert "About Me" in index_content

    def test_generate_excludes_drafts_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that drafts are excluded by default."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        # Check that draft post is NOT in index
        index_content = (temp_output_dir / "index.html").read_text()
        assert "Draft Post" not in index_content

    def test_generate_with_extra_stylesheets(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test generating with extra stylesheets."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                extra_stylesheets=["https://example.com/custom.css"],
            )
        )

        generator.generate()

        # Check that extra stylesheet is in generated HTML
        index_content = (temp_output_dir / "index.html").read_text()
        assert "https://example.com/custom.css" in index_content

    def test_generate_with_custom_posts_per_feed(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test generating with custom posts_per_feed setting."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=temp_output_dir, posts_per_feed=5
            )
        )

        generator.generate()

        # Should generate feeds successfully
        assert (temp_output_dir / "feed.xml").exists()

    def test_generate_preserves_unrelated_files(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that generate preserves unrelated files in output directory."""
        # Create a file in output directory
        old_file = temp_output_dir / "old_file.txt"
        old_file.write_text("This should be preserved")

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        # Old file should be preserved (generator doesn't clear the directory)
        assert old_file.exists()

    def test_generate_with_no_posts(
        self, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test generating with an empty content directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=empty_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        # Should still generate basic structure
        assert (temp_output_dir / "index.html").exists()
        assert (temp_output_dir / "static" / "style.css").exists()

    def test_generate_tags_overview_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that tags overview page is created."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        # Check for tags overview page
        assert (temp_output_dir / "tags.html").exists()

        # Check content has multiple tags
        content = (temp_output_dir / "tags.html").read_text()
        assert "python" in content.lower()

    def test_generate_categories_overview_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that categories overview page is created."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        # Check for categories overview page
        assert (temp_output_dir / "categories.html").exists()

        # Check content
        content = (temp_output_dir / "categories.html").read_text()
        assert "python" in content.lower()

    def test_generate_with_default_author(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that default_author is applied to posts without author."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                default_author="Default Author Name",
            )
        )

        generator.generate()

        # The first-post.md fixture doesn't have an author, so it should get the default
        post_file = temp_output_dir / "2024" / "01" / "15" / "first-post.html"
        assert post_file.exists()

        # Check that the author meta tag is present with default author
        content = post_file.read_text()
        assert '<meta name="author" content="Default Author Name">' in content

    def test_generate_without_default_author(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that posts without author remain without author when no default is set."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        # The first-post.md fixture doesn't have an author
        post_file = temp_output_dir / "2024" / "01" / "15" / "first-post.html"
        assert post_file.exists()

        # Check that no author meta tag is present
        content = post_file.read_text()
        assert '<meta name="author"' not in content

    def test_default_author_does_not_override_existing(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that default_author doesn't override existing author in post."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                default_author="Default Author Name",
            )
        )

        generator.generate()

        # The seo-test-post.md fixture has an existing author "John Doe"
        post_file = temp_output_dir / "2024" / "03" / "01" / "seo-test-post.html"
        assert post_file.exists()

        # Check that the original author is preserved
        content = post_file.read_text()
        assert '<meta name="author" content="John Doe">' in content
        assert "Default Author Name" not in content

    def test_default_author_with_empty_metadata(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that default_author works with posts that have empty metadata dict."""

        # Create a temporary content directory
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create a markdown file
        post_file = content_dir / "test.md"
        post_file.write_text("---\ntitle: Test\ndate: 2024-01-01\n---\n\nContent")

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                default_author="Default Author",
            )
        )

        # Generate and verify
        generator.generate()

        # Check that the post got the default author
        output_file = temp_output_dir / "2024" / "01" / "01" / "test.html"
        assert output_file.exists()
        content = output_file.read_text()
        assert '<meta name="author" content="Default Author">' in content

    def test_default_author_on_index_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that default_author appears in the author meta tag on the index page."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                default_author="Site Author",
            )
        )

        generator.generate()

        index_file = temp_output_dir / "index.html"
        assert index_file.exists()

        content = index_file.read_text()
        assert '<meta name="author" content="Site Author">' in content

    def test_no_author_on_index_page_without_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that no author meta tag appears on the index page when default_author is not set."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        index_file = temp_output_dir / "index.html"
        assert index_file.exists()

        content = index_file.read_text()
        assert '<meta name="author"' not in content

    def test_detect_favicon_ico(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test detecting favicon.ico file."""
        # Create a content directory with extras/favicon.ico
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        favicon_file = extras_dir / "favicon.ico"
        favicon_file.write_text("fake favicon content")

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )

        # Test the _detect_favicon method
        assert generator._detect_favicon() == "/favicon.ico"

    def test_detect_favicon_png(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test detecting favicon.png file."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        favicon_file = extras_dir / "favicon.png"
        favicon_file.write_text("fake favicon content")

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )

        assert generator._detect_favicon() == "/favicon.png"

    def test_detect_favicon_svg(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test detecting favicon.svg file."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        favicon_file = extras_dir / "favicon.svg"
        favicon_file.write_text("fake favicon content")

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )

        assert generator._detect_favicon() == "/favicon.svg"

    def test_detect_favicon_no_extras_dir(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that None is returned when extras directory doesn't exist."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )

        assert generator._detect_favicon() is None

    def test_detect_favicon_no_favicon_file(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that None is returned when no favicon file exists."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        # Create a different file
        (extras_dir / "robots.txt").write_text("User-agent: *")

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )

        assert generator._detect_favicon() is None

    def test_detect_favicon_priority(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that .ico is preferred when multiple favicon files exist."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        # Create multiple favicon files
        (extras_dir / "favicon.ico").write_text("ico")
        (extras_dir / "favicon.png").write_text("png")

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )

        # .ico should be preferred (first in list)
        assert generator._detect_favicon() == "/favicon.ico"

    def test_favicon_in_generated_html(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that favicon link is included in generated HTML."""
        # Create a content directory with extras/favicon.ico and a post
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        favicon_file = extras_dir / "favicon.ico"
        favicon_file.write_text("fake favicon content")

        # Create a post
        post_file = content_dir / "test-post.md"
        post_file.write_text(
            "---\ntitle: Test Post\ndate: 2024-01-01\n---\n\nTest content"
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        # Check that the index page has the favicon link
        index_file = temp_output_dir / "index.html"
        assert index_file.exists()
        content = index_file.read_text()
        assert '<link rel="icon" href="/favicon.ico">' in content

    def test_no_favicon_in_generated_html_when_missing(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that no favicon link is included when no favicon exists."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create a post but no favicon
        post_file = content_dir / "test-post.md"
        post_file.write_text(
            "---\ntitle: Test Post\ndate: 2024-01-01\n---\n\nTest content"
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        # Check that the index page does not have a favicon link
        index_file = temp_output_dir / "index.html"
        assert index_file.exists()
        content = index_file.read_text()
        assert '<link rel="icon"' not in content

    def test_generate_icons_copies_favicon_to_root(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that _generate_icons copies favicon.ico to the root output directory."""
        from PIL import Image

        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()

        # Create a real source icon image
        source_icon = extras_dir / "icon.png"
        img = Image.new("RGBA", (64, 64), (255, 0, 0, 255))
        img.save(source_icon)

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )

        generator._generate_icons()

        # favicon.ico should exist in the icons subdirectory
        assert (temp_output_dir / "icons" / "favicon.ico").is_file()

        # favicon.ico should also exist in the root output directory
        assert (temp_output_dir / "favicon.ico").is_file()

    def test_shortcut_icon_in_generated_html_with_platform_icons(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that shortcut icon link is included when platform icons exist."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create a post
        post_file = content_dir / "test-post.md"
        post_file.write_text(
            "---\ntitle: Test Post\ndate: 2024-01-01\n---\n\nTest content"
        )

        # Manually create icons to simulate generated platform icons
        icons_dir = temp_output_dir / "icons"
        icons_dir.mkdir(parents=True)
        (icons_dir / "favicon.ico").write_bytes(b"fake ico")
        (icons_dir / "apple-touch-icon.png").write_bytes(b"fake png")
        (temp_output_dir / "favicon.ico").write_bytes(b"fake ico")

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        index_file = temp_output_dir / "index.html"
        assert index_file.exists()
        html_content = index_file.read_text()
        assert '<link rel="shortcut icon" href="/favicon.ico">' in html_content

    def test_clean_first_removes_output_directory(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that clean_first removes the output directory before generation."""
        # Create output directory with some existing files
        temp_output_dir.mkdir(parents=True, exist_ok=True)
        old_file = temp_output_dir / "old_file.html"
        old_file.write_text("<html>Old content</html>")

        # Generate with clean_first=True
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=temp_output_dir, clean_first=True
            )
        )

        generator.generate()

        # The old file should not exist
        assert not old_file.exists()

        # But the new generated files should exist
        assert (temp_output_dir / "index.html").exists()

    def test_clean_first_false_preserves_existing_files(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that clean_first=False preserves existing files in output directory."""
        # Create output directory with some existing files
        temp_output_dir.mkdir(parents=True, exist_ok=True)
        old_file = temp_output_dir / "old_file.html"
        old_file.write_text("<html>Old content</html>")

        # Generate with clean_first=False (default)
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=temp_output_dir, clean_first=False
            )
        )

        generator.generate()

        # The old file should still exist
        assert old_file.exists()
        assert old_file.read_text() == "<html>Old content</html>"

        # And the new generated files should also exist
        assert (temp_output_dir / "index.html").exists()

    def test_clean_first_with_nonexistent_output(
        self, posts_dir: Path, tmp_path: Path
    ) -> None:
        """Test that clean_first works correctly when output directory doesn't exist."""
        output_dir = tmp_path / "nonexistent_output"

        # Generate with clean_first=True on non-existent directory
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=output_dir, clean_first=True
            )
        )

        # Should not raise an error
        generator.generate()

        # The output directory should be created with generated files
        assert output_dir.exists()
        assert (output_dir / "index.html").exists()

    def test_clean_first_retries_on_oserror(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that clean_first retries rmtree when an OSError occurs on first attempt."""
        import shutil
        from unittest.mock import patch

        temp_output_dir.mkdir(parents=True, exist_ok=True)

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=temp_output_dir, clean_first=True
            )
        )

        original_rmtree = shutil.rmtree
        call_count = 0

        def rmtree_fail_first_attempt(path: object, **kwargs: object) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1 and not kwargs.get("ignore_errors"):
                raise OSError("Directory not empty")
            original_rmtree(path, **kwargs)  # type: ignore[arg-type]

        with (
            patch(
                "blogmore.generator.shutil.rmtree",
                side_effect=rmtree_fail_first_attempt,
            ),
            patch("blogmore.generator.time.sleep"),
        ):
            generator.generate()

        # rmtree was called at least twice (once failing, once succeeding)
        assert call_count >= 2
        # Generation should have completed successfully despite the initial error
        assert temp_output_dir.exists()
        assert (temp_output_dir / "index.html").exists()

    def test_copy_extras_copies_flat_files(
        self, tmp_path: Path, temp_output_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that _copy_extras copies flat files from extras to output root."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        (extras_dir / "robots.txt").write_text("User-agent: *\nDisallow:")
        (extras_dir / "humans.txt").write_text("Team: The Developers")

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
            )
        )
        generator._copy_extras()

        assert (
            temp_output_dir / "robots.txt"
        ).read_text() == "User-agent: *\nDisallow:"
        assert (temp_output_dir / "humans.txt").read_text() == "Team: The Developers"
        captured = capsys.readouterr()
        assert "Copied 2 extra file(s)" in captured.out

    def test_copy_extras_preserves_subdirectories(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that _copy_extras recursively copies subdirectories."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()

        (extras_dir / "robots.txt").write_text("User-agent: *\nDisallow:")
        images_dir = extras_dir / "images"
        images_dir.mkdir()
        (images_dir / "splash.png").write_bytes(b"\x89PNG")
        thumbnails_dir = images_dir / "thumbnails"
        thumbnails_dir.mkdir()
        (thumbnails_dir / "tn1.jpeg").write_bytes(b"\xff\xd8\xff")
        (thumbnails_dir / "tn2.jpeg").write_bytes(b"\xff\xd8\xff")

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
            )
        )
        generator._copy_extras()

        assert (temp_output_dir / "robots.txt").exists()
        assert (temp_output_dir / "images" / "splash.png").read_bytes() == b"\x89PNG"
        assert (
            temp_output_dir / "images" / "thumbnails" / "tn1.jpeg"
        ).read_bytes() == b"\xff\xd8\xff"
        assert (
            temp_output_dir / "images" / "thumbnails" / "tn2.jpeg"
        ).read_bytes() == b"\xff\xd8\xff"

    def test_copy_extras_no_extras_dir(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that _copy_extras handles missing extras directory gracefully."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
            )
        )
        # Should not raise
        generator._copy_extras()

    def test_copy_extras_overriding_existing_file(
        self, tmp_path: Path, temp_output_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that _copy_extras overwrites existing files and prints a message."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        (extras_dir / "robots.txt").write_text("New content")
        (temp_output_dir / "robots.txt").write_text("Old content")

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
            )
        )
        generator._copy_extras()

        assert (temp_output_dir / "robots.txt").read_text() == "New content"
        captured = capsys.readouterr()
        assert "Overriding existing file" in captured.out

    def test_global_context_includes_version(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the global context includes the blogmore version."""
        from blogmore import __version__

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_title="Test Blog",
            )
        )

        context = generator._get_global_context()

        assert "blogmore_version" in context
        assert context["blogmore_version"] == __version__

    def test_global_context_includes_with_advert_true_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the global context includes with_advert as True by default."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )

        context = generator._get_global_context()

        assert "with_advert" in context
        assert context["with_advert"] is True

    def test_global_context_with_advert_false(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the global context reflects with_advert=False when configured."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_advert=False,
            )
        )

        context = generator._get_global_context()

        assert context["with_advert"] is False

    def test_site_description_in_global_context(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_description is included in the global context."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_description="A great blog about things",
            )
        )

        context = generator._get_global_context()

        assert context["site_description"] == "A great blog about things"

    def test_site_description_default_is_empty(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_description defaults to an empty string."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        assert generator.site_config.site_description == ""

    def test_site_description_in_index_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_description appears in the index page meta tags."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_description="My site description",
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="description" content="My site description">' in content
        assert (
            '<meta property="og:description" content="My site description">' in content
        )

    def test_no_description_meta_in_index_without_site_description(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that no description meta tag appears in index when site_description is empty."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="description"' not in content

    def test_site_description_in_archive_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_description appears in the archive page meta tags."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_description="My site description",
            )
        )

        generator.generate()

        content = (temp_output_dir / "archive.html").read_text()
        assert '<meta name="description" content="My site description">' in content

    def test_site_description_in_tags_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_description appears in the tags page meta tags."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_description="My site description",
            )
        )

        generator.generate()

        content = (temp_output_dir / "tags.html").read_text()
        assert '<meta name="description" content="My site description">' in content

    def test_site_description_in_categories_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_description appears in the categories page meta tags."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_description="My site description",
            )
        )

        generator.generate()

        content = (temp_output_dir / "categories.html").read_text()
        assert '<meta name="description" content="My site description">' in content

    def test_site_description_fallback_on_post_without_description(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_description is used as fallback for posts with no text content."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create a post whose content is only an image, so no text description
        # can be auto-extracted.  The site_description should be used as fallback.
        post_file = content_dir / "image-only.md"
        post_file.write_text(
            "---\ntitle: Image Only Post\ndate: 2024-06-01\n---\n\n"
            "![A photo](photo.jpg)\n"
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_description="Default site description",
            )
        )

        generator.generate()

        post_file_out = temp_output_dir / "2024" / "06" / "01" / "image-only.html"
        assert post_file_out.exists()
        content = post_file_out.read_text()
        assert '<meta name="description" content="Default site description">' in content

    def test_site_description_not_used_when_post_has_description(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that a post's own description takes precedence over site_description."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_description="Default site description",
            )
        )

        generator.generate()

        # seo-test-post.md has its own description
        post_file = temp_output_dir / "2024" / "03" / "01" / "seo-test-post.html"
        assert post_file.exists()
        content = post_file.read_text()
        # Own description should be used
        assert "This is a test post with SEO and social media meta tags" in content
        # site_description should NOT be used
        assert "Default site description" not in content

    def test_site_keywords_in_index_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_keywords appear in the index page meta tags."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_keywords=["python", "web", "programming"],
            )
        )

        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert (
            '<meta name="keywords" content="python, web, programming">' in index_content
        )

    def test_site_keywords_in_archive_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_keywords appear in the archive page meta tags."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_keywords=["python", "web"],
            )
        )

        generator.generate()

        archive_content = (temp_output_dir / "archive.html").read_text()
        assert '<meta name="keywords" content="python, web">' in archive_content

    def test_site_keywords_in_tag_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_keywords appear in tag pages."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_keywords=["blog", "posts"],
            )
        )

        generator.generate()

        tag_content = (temp_output_dir / "tag" / "python" / "index.html").read_text()
        assert '<meta name="keywords" content="blog, posts">' in tag_content

    def test_site_keywords_not_shown_when_not_configured(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that no keywords meta tag appears when site_keywords is not set."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="keywords"' not in index_content

    def test_post_tags_take_precedence_over_site_keywords(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that a post's own tags are used as keywords, not site_keywords."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_keywords=["site-wide-keyword"],
            )
        )

        generator.generate()

        # The seo-test-post has its own tags (e.g., "python", "web")
        post_file = temp_output_dir / "2024" / "03" / "01" / "seo-test-post.html"
        assert post_file.exists()
        content = post_file.read_text()
        # Post's own tags should be used as keywords
        assert '<meta name="keywords" content="' in content
        assert "site-wide-keyword" not in content

    def test_site_keywords_used_for_post_without_tags(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_keywords are used for posts with no tags."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        post_file = content_dir / "no-tags.md"
        post_file.write_text(
            "---\ntitle: No Tags Post\ndate: 2024-06-01\n---\n\nPost with no tags.\n"
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_keywords=["fallback", "keyword"],
            )
        )

        generator.generate()

        post_file_out = temp_output_dir / "2024" / "06" / "01" / "no-tags.html"
        assert post_file_out.exists()
        content = post_file_out.read_text()
        assert '<meta name="keywords" content="fallback, keyword">' in content

    def test_site_keywords_in_global_context(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_keywords is included in the global template context."""
        keywords = ["python", "web"]
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_keywords=keywords,
            )
        )

        context = generator._get_global_context()
        assert context["site_keywords"] == keywords

    def test_site_keywords_none_in_global_context(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_keywords is None in global context when not set."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        context = generator._get_global_context()
        assert context["site_keywords"] is None

    def test_index_page_og_type_is_website(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the index page has og:type set to website."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta property="og:type" content="website">' in content

    def test_index_page_og_url(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test that the index page has og:url set to the site root URL."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta property="og:url" content="https://example.com/">' in content

    def test_index_page_og_site_name(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the index page has og:site_name set to the site title."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_title="My Awesome Blog",
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta property="og:site_name" content="My Awesome Blog">' in content

    def test_index_page_twitter_card_summary_without_image(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that index page has twitter:card set to summary when no image is available."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="twitter:card" content="summary">' in content

    def test_index_page_twitter_card_summary_large_image_with_site_logo(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that index page uses summary_large_image twitter:card when site_logo is set."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                sidebar_config={"site_logo": "/images/logo.png"},
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="twitter:card" content="summary_large_image">' in content

    def test_index_page_twitter_title(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the index page has twitter:title set to the site title."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=temp_output_dir, site_title="My Blog"
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="twitter:title" content="My Blog">' in content

    def test_index_page_twitter_title_with_subtitle(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that twitter:title includes subtitle when site_subtitle is set."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_title="My Blog",
                site_subtitle="Thoughts and ideas",
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert (
            '<meta name="twitter:title" content="My Blog - Thoughts and ideas">'
            in content
        )

    def test_index_page_og_image_with_site_logo_absolute_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that og:image uses site_logo when it is an absolute URL."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                sidebar_config={"site_logo": "https://cdn.example.com/logo.png"},
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert (
            '<meta property="og:image" content="https://cdn.example.com/logo.png">'
            in content
        )
        assert (
            '<meta name="twitter:image" content="https://cdn.example.com/logo.png">'
            in content
        )

    def test_index_page_og_image_with_site_logo_relative_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that og:image prepends site_url when site_logo is a root-relative URL."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                sidebar_config={"site_logo": "/images/logo.png"},
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert (
            '<meta property="og:image" content="https://example.com/images/logo.png">'
            in content
        )
        assert (
            '<meta name="twitter:image" content="https://example.com/images/logo.png">'
            in content
        )

    def test_index_page_og_image_with_site_logo_bare_relative_path(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that og:image prepends site_url with slash when site_logo is a bare relative path."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                sidebar_config={"site_logo": "images/logo.png"},
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert (
            '<meta property="og:image" content="https://example.com/images/logo.png">'
            in content
        )
        assert (
            '<meta name="twitter:image" content="https://example.com/images/logo.png">'
            in content
        )

    def test_index_page_og_image_with_platform_icons_when_no_site_logo(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that og:image uses the 512px platform icon when has_platform_icons is true."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        post_file = content_dir / "test-post.md"
        post_file.write_text(
            "---\ntitle: Test Post\ndate: 2024-01-01\n---\n\nTest content"
        )

        # Manually create icons to simulate generated platform icons
        icons_dir = temp_output_dir / "icons"
        icons_dir.mkdir(parents=True)
        (icons_dir / "apple-touch-icon.png").write_bytes(b"fake png")
        (icons_dir / "android-chrome-512x512.png").write_bytes(b"fake png")

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert (
            '<meta property="og:image" content="https://example.com/icons/android-chrome-512x512.png">'
            in content
        )
        assert (
            '<meta name="twitter:image" content="https://example.com/icons/android-chrome-512x512.png">'
            in content
        )
        assert '<meta name="twitter:card" content="summary_large_image">' in content

    def test_index_page_og_image_platform_icons_take_priority_over_site_logo(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that platform icons take priority over site_logo for og:image."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        post_file = content_dir / "test-post.md"
        post_file.write_text(
            "---\ntitle: Test Post\ndate: 2024-01-01\n---\n\nTest content"
        )

        # Manually create icons to simulate generated platform icons
        icons_dir = temp_output_dir / "icons"
        icons_dir.mkdir(parents=True)
        (icons_dir / "apple-touch-icon.png").write_bytes(b"fake png")
        (icons_dir / "android-chrome-512x512.png").write_bytes(b"fake png")

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                sidebar_config={"site_logo": "/images/logo.png"},
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert (
            '<meta property="og:image" content="https://example.com/icons/android-chrome-512x512.png">'
            in content
        )
        assert (
            '<meta name="twitter:image" content="https://example.com/icons/android-chrome-512x512.png">'
            in content
        )

    def test_index_page_no_og_image_without_logo_or_icons(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that no og:image appears when site_logo is not set and no platform icons exist."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta property="og:image"' not in content
        assert '<meta name="twitter:image"' not in content


class TestMinifyCss:
    """Test the minify_css feature."""

    def test_minify_css_false_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that CSS is not minified by default."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        assert (temp_output_dir / "static" / "style.css").exists()
        assert not (
            temp_output_dir / "static" / minified_filename("style.css")
        ).exists()

    def test_minify_css_generates_min_css(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that minify_css generates style.min.css and not style.css."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=temp_output_dir, minify_css=True
            )
        )

        generator.generate()

        assert (temp_output_dir / "static" / minified_filename("style.css")).exists()
        assert not (temp_output_dir / "static" / "style.css").exists()

    def test_minify_css_produces_smaller_file(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that the minified CSS file is smaller than the original."""
        normal_output = tmp_path / "normal"
        minified_output = tmp_path / "minified"

        normal_generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=normal_output)
        )
        normal_generator.generate()

        minified_generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=minified_output, minify_css=True
            )
        )
        minified_generator.generate()

        normal_size = (normal_output / "static" / "style.css").stat().st_size
        minified_size = (
            (minified_output / "static" / minified_filename("style.css")).stat().st_size
        )
        assert minified_size < normal_size

    def test_minify_css_url_in_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that pages reference style.min.css when minify_css is enabled."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=temp_output_dir, minify_css=True
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert "/static/style.min.css" in content
        assert "/static/style.css" not in content

    def test_normal_css_url_in_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that pages reference style.css when minify_css is disabled."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert "/static/style.css" in content
        assert "/static/style.min.css" not in content

    def test_minify_css_with_custom_templates(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that a custom style.css is minified when minify_css is enabled."""
        templates_dir = tmp_path / "templates"
        static_dir = templates_dir / "static"
        static_dir.mkdir(parents=True)
        custom_css = static_dir / "style.css"
        custom_css.write_text("body  {  color:  red;  }", encoding="utf-8")

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                templates_dir=templates_dir,
                output_dir=temp_output_dir,
                minify_css=True,
            )
        )

        generator.generate()

        assert (temp_output_dir / "static" / minified_filename("style.css")).exists()
        assert not (temp_output_dir / "static" / "style.css").exists()
        minified_content = (
            temp_output_dir / "static" / minified_filename("style.css")
        ).read_text(encoding="utf-8")
        assert "body" in minified_content
        assert "color" in minified_content


class TestPageSpecificCss:
    """Test that page-specific CSS files are generated and linked correctly."""

    def test_page_specific_css_files_exist(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that all page-specific CSS source files are present in the output."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
                with_stats=True,
            )
        )

        generator.generate()

        assert (temp_output_dir / "static" / SEARCH_CSS_FILENAME).exists()
        assert (temp_output_dir / "static" / STATS_CSS_FILENAME).exists()
        assert (temp_output_dir / "static" / ARCHIVE_CSS_FILENAME).exists()
        assert (temp_output_dir / "static" / TAG_CLOUD_CSS_FILENAME).exists()

    def test_page_specific_css_minified_files_exist(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that minified page-specific CSS files exist when minify_css is enabled."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                minify_css=True,
                with_search=True,
                with_stats=True,
            )
        )

        generator.generate()

        assert (
            temp_output_dir / "static" / minified_filename(SEARCH_CSS_FILENAME)
        ).exists()
        assert (
            temp_output_dir / "static" / minified_filename(STATS_CSS_FILENAME)
        ).exists()
        assert (
            temp_output_dir / "static" / minified_filename(ARCHIVE_CSS_FILENAME)
        ).exists()
        assert (
            temp_output_dir / "static" / minified_filename(TAG_CLOUD_CSS_FILENAME)
        ).exists()

    def test_page_specific_css_source_not_present_when_minifying(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that source CSS files are absent when minify_css is enabled."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                minify_css=True,
                with_search=True,
                with_stats=True,
            )
        )

        generator.generate()

        assert not (temp_output_dir / "static" / SEARCH_CSS_FILENAME).exists()
        assert not (temp_output_dir / "static" / STATS_CSS_FILENAME).exists()
        assert not (temp_output_dir / "static" / ARCHIVE_CSS_FILENAME).exists()
        assert not (temp_output_dir / "static" / TAG_CLOUD_CSS_FILENAME).exists()

    def test_search_page_links_search_css(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the search page includes the search-specific CSS file."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
            )
        )

        generator.generate()

        search_html = (temp_output_dir / "search.html").read_text()
        assert f"/static/{SEARCH_CSS_FILENAME}" in search_html

    def test_stats_page_links_stats_css(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the stats page includes the stats-specific CSS file."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
            )
        )

        generator.generate()

        stats_html = (temp_output_dir / "stats.html").read_text()
        assert f"/static/{STATS_CSS_FILENAME}" in stats_html

    def test_archive_page_links_archive_css(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the archive page includes the archive-specific CSS file."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )

        generator.generate()

        archive_html = (temp_output_dir / "archive.html").read_text()
        assert f"/static/{ARCHIVE_CSS_FILENAME}" in archive_html

    def test_tags_page_links_tag_cloud_css(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the tags overview page includes the tag-cloud CSS file."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )

        generator.generate()

        tags_html = (temp_output_dir / "tags.html").read_text()
        assert f"/static/{TAG_CLOUD_CSS_FILENAME}" in tags_html

    def test_categories_page_links_tag_cloud_css(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the categories overview page includes the tag-cloud CSS file."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )

        generator.generate()

        categories_html = (temp_output_dir / "categories.html").read_text()
        assert f"/static/{TAG_CLOUD_CSS_FILENAME}" in categories_html

    def test_index_page_does_not_link_page_specific_css(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the main index page does not include page-specific CSS files."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
                with_stats=True,
            )
        )

        generator.generate()

        index_html = (temp_output_dir / "index.html").read_text()
        assert SEARCH_CSS_FILENAME not in index_html
        assert STATS_CSS_FILENAME not in index_html
        assert ARCHIVE_CSS_FILENAME not in index_html
        assert TAG_CLOUD_CSS_FILENAME not in index_html

    def test_search_css_has_cache_bust_token(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the search CSS URL contains a cache-busting token."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
            )
        )

        generator.generate()

        search_html = (temp_output_dir / "search.html").read_text()
        assert f"/static/{SEARCH_CSS_FILENAME}?v=" in search_html

    def test_minified_page_specific_css_urls_in_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that minified CSS filenames appear in pages when minify_css is enabled."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                minify_css=True,
                with_search=True,
                with_stats=True,
            )
        )

        generator.generate()

        search_html = (temp_output_dir / "search.html").read_text()
        assert f"/static/{minified_filename(SEARCH_CSS_FILENAME)}" in search_html

        stats_html = (temp_output_dir / "stats.html").read_text()
        assert f"/static/{minified_filename(STATS_CSS_FILENAME)}" in stats_html

        archive_html = (temp_output_dir / "archive.html").read_text()
        assert f"/static/{minified_filename(ARCHIVE_CSS_FILENAME)}" in archive_html

        tags_html = (temp_output_dir / "tags.html").read_text()
        assert f"/static/{minified_filename(TAG_CLOUD_CSS_FILENAME)}" in tags_html


class TestMinifyJs:
    """Test the minify_js feature."""

    def test_minify_js_false_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that JavaScript is not minified by default."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        assert (temp_output_dir / "static" / "theme.js").exists()
        assert not (temp_output_dir / "static" / "theme.min.js").exists()

    def test_minify_js_generates_min_js(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that minify_js generates theme.min.js and not theme.js."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=temp_output_dir, minify_js=True
            )
        )

        generator.generate()

        assert (temp_output_dir / "static" / "theme.min.js").exists()
        assert not (temp_output_dir / "static" / "theme.js").exists()

    def test_minify_js_produces_smaller_file(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that the minified JS file is smaller than the original."""
        normal_output = tmp_path / "normal"
        minified_output = tmp_path / "minified"

        normal_generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=normal_output)
        )
        normal_generator.generate()

        minified_generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=minified_output, minify_js=True
            )
        )
        minified_generator.generate()

        normal_size = (normal_output / "static" / "theme.js").stat().st_size
        minified_size = (minified_output / "static" / "theme.min.js").stat().st_size
        assert minified_size < normal_size

    def test_minify_js_url_in_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that pages reference theme.min.js when minify_js is enabled."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=temp_output_dir, minify_js=True
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert "/static/theme.min.js" in content
        assert "/static/theme.js" not in content

    def test_normal_js_url_in_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that pages reference theme.js when minify_js is disabled."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert "/static/theme.js" in content
        assert "/static/theme.min.js" not in content

    def test_minify_js_search_without_search_enabled(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that search.min.js is not generated when search is disabled."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                minify_js=True,
                with_search=False,
            )
        )

        generator.generate()

        assert not (temp_output_dir / "static" / "search.min.js").exists()
        assert not (temp_output_dir / "static" / "search.js").exists()

    def test_minify_js_with_search_generates_min_search_js(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that search.min.js is generated when both minify_js and with_search are enabled."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                minify_js=True,
                with_search=True,
            )
        )

        generator.generate()

        assert (temp_output_dir / "static" / "search.min.js").exists()
        assert not (temp_output_dir / "static" / "search.js").exists()

    def test_minify_js_search_url_in_search_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that search page references search.min.js when minify_js is enabled."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                minify_js=True,
                with_search=True,
            )
        )

        generator.generate()

        content = (temp_output_dir / "search.html").read_text()
        assert "/static/search.min.js" in content
        assert "/static/search.js" not in content

    def test_minify_js_with_custom_templates(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that a custom theme.js is minified when minify_js is enabled."""
        templates_dir = tmp_path / "templates"
        static_dir = templates_dir / "static"
        static_dir.mkdir(parents=True)
        custom_js = static_dir / "theme.js"
        custom_js.write_text(
            "/* comment */ function hello() { return 'world'; }",
            encoding="utf-8",
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                templates_dir=templates_dir,
                output_dir=temp_output_dir,
                minify_js=True,
            )
        )

        generator.generate()

        assert (temp_output_dir / "static" / "theme.min.js").exists()
        assert not (temp_output_dir / "static" / "theme.js").exists()
        minified_content = (temp_output_dir / "static" / "theme.min.js").read_text(
            encoding="utf-8"
        )
        assert "hello" in minified_content
        assert "world" in minified_content


class TestMinifyHtml:
    """Test the minify_html feature."""

    def test_minify_html_false_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that HTML is not minified by default."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text(encoding="utf-8")
        # Unminified HTML will contain newlines and indentation
        assert "\n" in content

    def test_minify_html_produces_smaller_output(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that minify_html produces smaller HTML files than the default."""
        normal_output = tmp_path / "normal"
        minified_output = tmp_path / "minified"

        normal_generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=normal_output,
            )
        )
        normal_generator.generate()

        minified_generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=minified_output,
                minify_html=True,
            )
        )
        minified_generator.generate()

        normal_size = (normal_output / "index.html").stat().st_size
        minified_size = (minified_output / "index.html").stat().st_size
        assert minified_size < normal_size

    def test_minify_html_filename_unchanged(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that HTML filenames are not changed when minify_html is enabled."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                minify_html=True,
            )
        )

        generator.generate()

        # index.html is still called index.html, not index.min.html
        assert (temp_output_dir / "index.html").exists()
        assert not (temp_output_dir / "index.min.html").exists()

    def test_minify_html_valid_html_output(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that minified HTML output still contains expected content."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                minify_html=True,
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text(encoding="utf-8")
        # Minified HTML should still have essential structure
        assert "<!doctype html>" in content.lower()
        assert "<html" in content

    def test_minify_html_applied_to_all_pages(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that minify_html is applied to all generated HTML files."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                minify_html=True,
            )
        )

        generator.generate()

        html_files = list(temp_output_dir.rglob("*.html"))
        assert len(html_files) > 0

        for html_file in html_files:
            content = html_file.read_text(encoding="utf-8")
            # Each file should still have valid HTML structure
            assert "<html" in content or "<!doctype" in content.lower()


class TestPrevNextHeadLinkTags:
    """Test that prev/next link tags are correctly added to the head of post pages."""

    def test_post_with_prev_and_next_has_head_link_tags(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that a post with both prev and next navigation has link tags in head."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create three posts so the middle one has both prev and next
        (content_dir / "2024-01-01-oldest.md").write_text(
            "---\ntitle: Oldest Post\ndate: 2024-01-01\n---\n\nOldest content."
        )
        (content_dir / "2024-01-15-middle.md").write_text(
            "---\ntitle: Middle Post\ndate: 2024-01-15\n---\n\nMiddle content."
        )
        (content_dir / "2024-02-01-newest.md").write_text(
            "---\ntitle: Newest Post\ndate: 2024-02-01\n---\n\nNewest content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        middle_post_file = temp_output_dir / "2024" / "01" / "15" / "middle.html"
        assert middle_post_file.exists()
        content = middle_post_file.read_text()

        # Middle post should have both prev (older) and next (newer) link tags in head
        assert '<link rel="prev" href="/2024/01/01/oldest.html">' in content
        assert '<link rel="next" href="/2024/02/01/newest.html">' in content

    def test_oldest_post_has_only_next_head_link_tag(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the oldest post has only a next link tag in head (no prev)."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-01-oldest.md").write_text(
            "---\ntitle: Oldest Post\ndate: 2024-01-01\n---\n\nOldest content."
        )
        (content_dir / "2024-02-01-newest.md").write_text(
            "---\ntitle: Newest Post\ndate: 2024-02-01\n---\n\nNewest content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        oldest_post_file = temp_output_dir / "2024" / "01" / "01" / "oldest.html"
        assert oldest_post_file.exists()
        content = oldest_post_file.read_text()

        # Oldest post has no previous post, only a next link
        assert 'rel="prev"' not in content
        assert '<link rel="next" href="/2024/02/01/newest.html">' in content

    def test_newest_post_has_only_prev_head_link_tag(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the newest post has only a prev link tag in head (no next)."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-01-oldest.md").write_text(
            "---\ntitle: Oldest Post\ndate: 2024-01-01\n---\n\nOldest content."
        )
        (content_dir / "2024-02-01-newest.md").write_text(
            "---\ntitle: Newest Post\ndate: 2024-02-01\n---\n\nNewest content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        newest_post_file = temp_output_dir / "2024" / "02" / "01" / "newest.html"
        assert newest_post_file.exists()
        content = newest_post_file.read_text()

        # Newest post has no next post, only a prev link
        assert '<link rel="prev" href="/2024/01/01/oldest.html">' in content
        assert 'rel="next"' not in content

    def test_single_post_has_no_head_link_tags(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that a lone post with no navigation has no prev/next link tags in head."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-01-only.md").write_text(
            "---\ntitle: Only Post\ndate: 2024-01-01\n---\n\nOnly content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        only_post_file = temp_output_dir / "2024" / "01" / "01" / "only.html"
        assert only_post_file.exists()
        content = only_post_file.read_text()

        assert 'rel="prev"' not in content
        assert 'rel="next"' not in content


class TestPaginationHeadLinkTags:
    """Test that prev/next link tags are added to the head of paginated listing pages."""

    def test_index_page_2_has_prev_link_tag(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that index page 2 has a prev link pointing to page 1."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create 11 posts to trigger a second index page
        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\n---\n\nContent {i}."
            )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        page2_file = temp_output_dir / "page" / "2.html"
        assert page2_file.exists()
        content = page2_file.read_text()

        assert '<link rel="prev" href="/index.html">' in content
        assert 'rel="next"' not in content

    def test_index_page_1_has_next_link_tag(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that index page 1 has a next link pointing to page 2 when there are multiple pages."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\n---\n\nContent {i}."
            )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        index_file = temp_output_dir / "index.html"
        assert index_file.exists()
        content = index_file.read_text()

        assert 'rel="prev"' not in content
        assert '<link rel="next" href="/page/2.html">' in content

    def test_index_middle_page_has_both_link_tags(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that an index middle page has both prev and next link tags."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create 21 posts to trigger three index pages
        for i in range(1, 22):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\n---\n\nContent {i}."
            )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        page2_file = temp_output_dir / "page" / "2.html"
        assert page2_file.exists()
        content = page2_file.read_text()

        assert '<link rel="prev" href="/index.html">' in content
        assert '<link rel="next" href="/page/3.html">' in content

    def test_tag_page_2_has_prev_link_tag(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that tag page 2 has a prev link pointing to tag page 1."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\ntags: [python]\n---\n\nContent {i}."
            )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        tag_page2_file = temp_output_dir / "tag" / "python" / "page" / "2.html"
        assert tag_page2_file.exists()
        content = tag_page2_file.read_text()

        assert '<link rel="prev" href="/tag/python/index.html">' in content
        assert 'rel="next"' not in content

    def test_tag_page_1_has_next_link_tag(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that tag page 1 has a next link when there are multiple pages."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\ntags: [python]\n---\n\nContent {i}."
            )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        tag_page1_file = temp_output_dir / "tag" / "python" / "index.html"
        assert tag_page1_file.exists()
        content = tag_page1_file.read_text()

        assert 'rel="prev"' not in content
        assert '<link rel="next" href="/tag/python/page/2.html">' in content

    def test_category_page_2_has_prev_link_tag(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that category page 2 has a prev link pointing to category page 1."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\ncategory: Tech\n---\n\nContent {i}."
            )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        cat_page2_file = temp_output_dir / "category" / "tech" / "page" / "2.html"
        assert cat_page2_file.exists()
        content = cat_page2_file.read_text()

        assert '<link rel="prev" href="/category/tech/index.html">' in content
        assert 'rel="next"' not in content

    def test_category_page_1_has_next_link_tag(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that category page 1 has a next link when there are multiple pages."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\ncategory: Tech\n---\n\nContent {i}."
            )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        cat_page1_file = temp_output_dir / "category" / "tech" / "index.html"
        assert cat_page1_file.exists()
        content = cat_page1_file.read_text()

        assert 'rel="prev"' not in content
        assert '<link rel="next" href="/category/tech/page/2.html">' in content

    def test_year_archive_page_2_has_prev_link_tag(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that year archive page 2 has a prev link pointing to page 1."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create 11 posts all in the same year to trigger pagination
        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\n---\n\nContent {i}."
            )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        year_page2_file = temp_output_dir / "2024" / "page" / "2.html"
        assert year_page2_file.exists()
        content = year_page2_file.read_text()

        assert '<link rel="prev" href="/2024/index.html">' in content
        assert 'rel="next"' not in content

    def test_single_page_listing_has_no_pagination_link_tags(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that a single-page listing has no prev/next link tags in head."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-01-only.md").write_text(
            "---\ntitle: Only Post\ndate: 2024-01-01\ntags: [python]\ncategory: Tech\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        index_file = temp_output_dir / "index.html"
        tag_page = temp_output_dir / "tag" / "python" / "index.html"
        cat_page = temp_output_dir / "category" / "tech" / "index.html"

        for page_file in (index_file, tag_page, cat_page):
            assert page_file.exists()
            content = page_file.read_text()
            assert 'rel="prev"' not in content
            assert 'rel="next"' not in content


class TestCanonicalLinkTags:
    """Test that canonical link tags are correctly added to the head of all pages."""

    def test_post_page_has_canonical_link(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that a post page includes the correct canonical link tag."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-my-post.md").write_text(
            "---\ntitle: My Post\ndate: 2024-01-15\n---\n\nPost content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
            )
        )
        generator.generate()

        post_file = temp_output_dir / "2024" / "01" / "15" / "my-post.html"
        assert post_file.exists()
        content = post_file.read_text()

        assert (
            '<link rel="canonical" href="https://example.com/2024/01/15/my-post.html">'
            in content
        )

    def test_static_page_has_canonical_link(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that a static page includes the correct canonical link tag."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_dir = content_dir / "pages"
        pages_dir.mkdir()

        (pages_dir / "about.md").write_text("---\ntitle: About\n---\n\nAbout content.")

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
            )
        )
        generator.generate()

        page_file = temp_output_dir / "about.html"
        assert page_file.exists()
        content = page_file.read_text()

        assert '<link rel="canonical" href="https://example.com/about.html">' in content

    def test_index_page_has_canonical_link(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the index page includes the correct canonical link tag."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
            )
        )
        generator.generate()

        index_file = temp_output_dir / "index.html"
        assert index_file.exists()
        content = index_file.read_text()

        assert '<link rel="canonical" href="https://example.com/index.html">' in content

    def test_archive_page_has_canonical_link(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the archive page includes the correct canonical link tag."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
            )
        )
        generator.generate()

        archive_file = temp_output_dir / "archive.html"
        assert archive_file.exists()
        content = archive_file.read_text()

        assert (
            '<link rel="canonical" href="https://example.com/archive.html">' in content
        )

    def test_tags_page_has_canonical_link(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the tags overview page includes the correct canonical link tag."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-15\ntags: [python]\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
            )
        )
        generator.generate()

        tags_file = temp_output_dir / "tags.html"
        assert tags_file.exists()
        content = tags_file.read_text()

        assert '<link rel="canonical" href="https://example.com/tags.html">' in content

    def test_tag_page_has_canonical_link(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that an individual tag page includes the correct canonical link tag."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-15\ntags: [python]\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
            )
        )
        generator.generate()

        tag_file = temp_output_dir / "tag" / "python" / "index.html"
        assert tag_file.exists()
        content = tag_file.read_text()

        assert (
            '<link rel="canonical" href="https://example.com/tag/python/index.html">'
            in content
        )

    def test_categories_page_has_canonical_link(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the categories overview page includes the correct canonical link tag."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-15\ncategory: Python\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
            )
        )
        generator.generate()

        categories_file = temp_output_dir / "categories.html"
        assert categories_file.exists()
        content = categories_file.read_text()

        assert (
            '<link rel="canonical" href="https://example.com/categories.html">'
            in content
        )

    def test_category_page_has_canonical_link(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that an individual category page includes the correct canonical link tag."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-15\ncategory: Python\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
            )
        )
        generator.generate()

        category_file = temp_output_dir / "category" / "python" / "index.html"
        assert category_file.exists()
        content = category_file.read_text()

        assert (
            '<link rel="canonical" href="https://example.com/category/python/index.html">'
            in content
        )

    def test_date_archive_page_has_canonical_link(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that a date-based archive page includes the correct canonical link tag."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
            )
        )
        generator.generate()

        year_archive_file = temp_output_dir / "2024" / "index.html"
        assert year_archive_file.exists()
        content = year_archive_file.read_text()

        assert (
            '<link rel="canonical" href="https://example.com/2024/index.html">'
            in content
        )

    def test_category_page_canonical_link_uses_clean_url(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that a category page canonical link respects clean_urls."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-15\ncategory: Coding\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                clean_urls=True,
            )
        )
        generator.generate()

        category_file = temp_output_dir / "category" / "coding" / "index.html"
        assert category_file.exists()
        content = category_file.read_text()

        assert (
            '<link rel="canonical" href="https://example.com/category/coding/">'
            in content
        )

    def test_tag_page_canonical_link_uses_clean_url(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that a tag page canonical link respects clean_urls."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-15\ntags: [python]\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                clean_urls=True,
            )
        )
        generator.generate()

        tag_file = temp_output_dir / "tag" / "python" / "index.html"
        assert tag_file.exists()
        content = tag_file.read_text()

        assert (
            '<link rel="canonical" href="https://example.com/tag/python/">' in content
        )

    def test_index_page_canonical_link_uses_clean_url(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the main index page canonical link respects clean_urls."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                clean_urls=True,
            )
        )
        generator.generate()

        index_file = temp_output_dir / "index.html"
        assert index_file.exists()
        content = index_file.read_text()

        assert '<link rel="canonical" href="https://example.com/">' in content

    def test_date_archive_canonical_link_uses_clean_url(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that a date-based archive canonical link respects clean_urls."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                clean_urls=True,
            )
        )
        generator.generate()

        year_archive_file = temp_output_dir / "2024" / "index.html"
        assert year_archive_file.exists()
        content = year_archive_file.read_text()

        assert '<link rel="canonical" href="https://example.com/2024/">' in content

    def test_paginated_category_page_canonical_link_uses_clean_url(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that paginated category pages have clean canonical links."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        for day in range(1, 12):
            (content_dir / f"2024-01-{day:02d}-post{day}.md").write_text(
                f"---\ntitle: Post {day}\ndate: 2024-01-{day:02d}\ncategory: Coding\n---\n\nContent."
            )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                clean_urls=True,
                page_n_path="page/{page}/index.html",
            )
        )
        generator.generate()

        category_page2 = (
            temp_output_dir / "category" / "coding" / "page" / "2" / "index.html"
        )
        assert category_page2.exists()
        content = category_page2.read_text()

        assert (
            '<link rel="canonical" href="https://example.com/category/coding/page/2/">'
            in content
        )

    """Test custom 404 page generation."""

    def test_generate_creates_404_html_when_404_md_exists(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that 404.html is generated when 404.md exists in pages/."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_dir = content_dir / "pages"
        pages_dir.mkdir()
        (pages_dir / CUSTOM_404_MARKDOWN).write_text(
            "---\ntitle: Page Not Found\n---\n\nSorry, page not found."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        assert (temp_output_dir / CUSTOM_404_HTML).exists()
        content = (temp_output_dir / CUSTOM_404_HTML).read_text()
        assert "Page Not Found" in content

    def test_generate_does_not_create_404_html_when_no_404_md(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that 404.html is not generated when 404.md is absent."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        assert not (temp_output_dir / CUSTOM_404_HTML).exists()

    def test_404_md_not_included_in_sidebar_pages(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that 404.md does not appear as a navigation page."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_dir = content_dir / "pages"
        pages_dir.mkdir()
        (pages_dir / "about.md").write_text("---\ntitle: About\n---\n\nAbout page.")
        (pages_dir / CUSTOM_404_MARKDOWN).write_text(
            "---\ntitle: Page Not Found\n---\n\nSorry, page not found."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        # The about page should appear in navigation
        assert "About" in index_content
        # 404.html should not appear as a nav link alongside regular pages
        assert CUSTOM_404_HTML not in index_content

    def test_404_html_generated_in_root_output_directory(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that 404.html is placed in the root of the output directory."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_dir = content_dir / "pages"
        pages_dir.mkdir()
        (pages_dir / CUSTOM_404_MARKDOWN).write_text(
            "---\ntitle: Not Found\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        assert (temp_output_dir / CUSTOM_404_HTML).exists()
        # Should be in root, not in a subdirectory
        assert not (temp_output_dir / "pages" / CUSTOM_404_HTML).exists()


class TestWithReadTime:
    """Test the with_read_time feature for showing estimated reading time on posts."""

    def test_reading_time_not_shown_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that reading time is not shown when with_read_time is False (default)."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert "min read" not in index_content

    def test_reading_time_shown_when_enabled(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that reading time is shown when with_read_time is True."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=temp_output_dir, with_read_time=True
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert "min read" in index_content

    def test_reading_time_not_shown_on_post_page_by_default(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that reading time is not shown on individual post pages by default."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-01-hello.md").write_text(
            "---\ntitle: Hello\ndate: 2024-01-01\n---\n\nHello world content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        post_file = temp_output_dir / "2024" / "01" / "01" / "hello.html"
        assert post_file.exists()
        content = post_file.read_text()
        assert "min read" not in content

    def test_reading_time_shown_on_post_page_when_enabled(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that reading time is shown on individual post pages when with_read_time is True."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-01-hello.md").write_text(
            "---\ntitle: Hello\ndate: 2024-01-01\n---\n\nHello world content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir, output_dir=temp_output_dir, with_read_time=True
            )
        )
        generator.generate()

        post_file = temp_output_dir / "2024" / "01" / "01" / "hello.html"
        assert post_file.exists()
        content = post_file.read_text()
        assert "min read" in content

    def test_reading_time_not_shown_on_category_page_by_default(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that reading time is not shown on category pages by default."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-01-hello.md").write_text(
            "---\ntitle: Hello\ndate: 2024-01-01\ncategory: Tech\n---\n\nHello world."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        category_file = temp_output_dir / "category" / "tech" / "index.html"
        assert category_file.exists()
        content = category_file.read_text()
        assert "min read" not in content

    def test_reading_time_shown_on_category_page_when_enabled(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that reading time is shown on category pages when with_read_time is True."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-01-hello.md").write_text(
            "---\ntitle: Hello\ndate: 2024-01-01\ncategory: Tech\n---\n\nHello world."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir, output_dir=temp_output_dir, with_read_time=True
            )
        )
        generator.generate()

        category_file = temp_output_dir / "category" / "tech" / "index.html"
        assert category_file.exists()
        content = category_file.read_text()
        assert "min read" in content

    def test_reading_time_not_shown_on_tag_page_by_default(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that reading time is not shown on tag pages by default."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-01-hello.md").write_text(
            "---\ntitle: Hello\ndate: 2024-01-01\ntags: [python]\n---\n\nHello world."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        tag_file = temp_output_dir / "tag" / "python" / "index.html"
        assert tag_file.exists()
        content = tag_file.read_text()
        assert "min read" not in content

    def test_reading_time_shown_on_tag_page_when_enabled(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that reading time is shown on tag pages when with_read_time is True."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-01-hello.md").write_text(
            "---\ntitle: Hello\ndate: 2024-01-01\ntags: [python]\n---\n\nHello world."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir, output_dir=temp_output_dir, with_read_time=True
            )
        )
        generator.generate()

        tag_file = temp_output_dir / "tag" / "python" / "index.html"
        assert tag_file.exists()
        content = tag_file.read_text()
        assert "min read" in content

    def test_with_read_time_default_is_false(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that with_read_time defaults to False."""
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
        )
        assert generator.site_config.with_read_time is False

    def test_with_read_time_in_global_context(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that with_read_time is included in the global template context."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=temp_output_dir, with_read_time=True
            )
        )
        context = generator._get_global_context()
        assert context["with_read_time"] is True

    def test_with_read_time_false_in_global_context(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that with_read_time=False is included in the global template context."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir, output_dir=temp_output_dir, with_read_time=False
            )
        )
        context = generator._get_global_context()
        assert context["with_read_time"] is False

    def test_archive_page_has_table_of_contents_sidebar(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the main archive page includes the TOC sidebar navigation."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post-a.md").write_text(
            "---\ntitle: January Post\ndate: 2024-01-15\n---\n\nContent."
        )
        (content_dir / "2024-03-10-post-b.md").write_text(
            "---\ntitle: March Post\ndate: 2024-03-10\n---\n\nContent."
        )
        (content_dir / "2023-11-05-post-c.md").write_text(
            "---\ntitle: November Post\ndate: 2023-11-05\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        content = (temp_output_dir / "archive.html").read_text()

        assert 'class="archive-toc"' in content
        assert 'aria-label="Archive table of contents"' in content

    def test_archive_page_table_of_contents_has_year_anchors(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the main archive page has anchor IDs on year sections and TOC year links."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-03-10-post.md").write_text(
            "---\ntitle: A Post\ndate: 2024-03-10\n---\n\nContent."
        )
        (content_dir / "2023-07-20-post.md").write_text(
            "---\ntitle: Another Post\ndate: 2023-07-20\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        content = (temp_output_dir / "archive.html").read_text()

        assert 'id="archive-2024"' in content
        assert 'id="archive-2023"' in content
        assert 'href="#archive-2024"' in content
        assert 'href="#archive-2023"' in content

    def test_archive_page_table_of_contents_has_month_anchors(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the main archive page has anchor IDs on month sections and TOC month links."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: January Post\ndate: 2024-01-15\n---\n\nContent."
        )
        (content_dir / "2024-03-10-post.md").write_text(
            "---\ntitle: March Post\ndate: 2024-03-10\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        content = (temp_output_dir / "archive.html").read_text()

        assert 'id="archive-2024-01"' in content
        assert 'id="archive-2024-03"' in content
        assert 'href="#archive-2024-01"' in content
        assert 'href="#archive-2024-03"' in content

    def test_archive_page_table_of_contents_not_shown_on_date_archive(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the TOC sidebar is not shown on date-based archive pages."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: January Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        year_archive = (temp_output_dir / "2024" / "index.html").read_text()
        assert 'class="archive-toc"' not in year_archive

        month_archive = (temp_output_dir / "2024" / "01" / "index.html").read_text()
        assert 'class="archive-toc"' not in month_archive

    def test_archive_page_table_of_contents_months_in_correct_order(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the TOC months appear in descending order (newest first)."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post.md").write_text(
            "---\ntitle: January Post\ndate: 2024-01-15\n---\n\nContent."
        )
        (content_dir / "2024-06-20-post.md").write_text(
            "---\ntitle: June Post\ndate: 2024-06-20\n---\n\nContent."
        )
        (content_dir / "2024-12-01-post.md").write_text(
            "---\ntitle: December Post\ndate: 2024-12-01\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        content = (temp_output_dir / "archive.html").read_text()

        december_pos = content.find('href="#archive-2024-12"')
        june_pos = content.find('href="#archive-2024-06"')
        january_pos = content.find('href="#archive-2024-01"')

        assert december_pos < june_pos < january_pos

    def test_archive_page_heading_shows_total_post_count(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the Archive h1 heading shows the total count of all posts."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post-a.md").write_text(
            "---\ntitle: January Post\ndate: 2024-01-15\n---\n\nContent."
        )
        (content_dir / "2024-03-10-post-b.md").write_text(
            "---\ntitle: March Post\ndate: 2024-03-10\n---\n\nContent."
        )
        (content_dir / "2023-11-05-post-c.md").write_text(
            "---\ntitle: November Post\ndate: 2023-11-05\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        content = (temp_output_dir / "archive.html").read_text()

        assert (
            '<h1>Archive <span class="archive-post-count">(3 posts)</span></h1>'
            in content
        )

    def test_archive_page_heading_singular_post_count(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the Archive h1 heading uses singular 'post' for a single post."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-only-post.md").write_text(
            "---\ntitle: Only Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        content = (temp_output_dir / "archive.html").read_text()

        assert (
            '<h1>Archive <span class="archive-post-count">(1 post)</span></h1>'
            in content
        )

    def test_archive_page_year_headings_show_post_counts(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that each year heading in the archive shows the post count for that year."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post-a.md").write_text(
            "---\ntitle: January Post\ndate: 2024-01-15\n---\n\nContent."
        )
        (content_dir / "2024-03-10-post-b.md").write_text(
            "---\ntitle: March Post\ndate: 2024-03-10\n---\n\nContent."
        )
        (content_dir / "2023-11-05-post-c.md").write_text(
            "---\ntitle: November Post\ndate: 2023-11-05\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        content = (temp_output_dir / "archive.html").read_text()

        assert 'class="archive-post-count">(2 posts)</span>' in content
        assert 'class="archive-post-count">(1 post)</span>' in content

    def test_archive_page_month_headings_show_post_counts(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that each month heading in the archive shows the post count for that month."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post-a.md").write_text(
            "---\ntitle: January Post A\ndate: 2024-01-15\n---\n\nContent."
        )
        (content_dir / "2024-01-20-post-b.md").write_text(
            "---\ntitle: January Post B\ndate: 2024-01-20\n---\n\nContent."
        )
        (content_dir / "2024-03-10-post-c.md").write_text(
            "---\ntitle: March Post\ndate: 2024-03-10\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        content = (temp_output_dir / "archive.html").read_text()

        assert 'class="archive-post-count">(2 posts)</span>' in content
        assert 'class="archive-post-count">(1 post)</span>' in content

    def test_archive_toc_shows_year_counts(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the archive TOC shows numeric post counts for each year."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post-a.md").write_text(
            "---\ntitle: Post A\ndate: 2024-01-15\n---\n\nContent."
        )
        (content_dir / "2024-03-10-post-b.md").write_text(
            "---\ntitle: Post B\ndate: 2024-03-10\n---\n\nContent."
        )
        (content_dir / "2023-06-20-post-c.md").write_text(
            "---\ntitle: Post C\ndate: 2023-06-20\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        content = (temp_output_dir / "archive.html").read_text()

        assert 'class="archive-toc-count">(2)</span>' in content
        assert 'class="archive-toc-count">(1)</span>' in content

    def test_archive_toc_shows_month_counts(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that the archive TOC shows numeric post counts for each month."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-15-post-a.md").write_text(
            "---\ntitle: Post A\ndate: 2024-01-15\n---\n\nContent."
        )
        (content_dir / "2024-01-20-post-b.md").write_text(
            "---\ntitle: Post B\ndate: 2024-01-20\n---\n\nContent."
        )
        (content_dir / "2024-03-10-post-c.md").write_text(
            "---\ntitle: Post C\ndate: 2024-03-10\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()

        content = (temp_output_dir / "archive.html").read_text()

        assert 'January <span class="archive-toc-count">(2)</span>' in content
        assert 'March <span class="archive-toc-count">(1)</span>' in content


class TestPostPathConfiguration:
    """Tests for the configurable post_path feature."""

    def test_default_post_path_produces_date_based_structure(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The default post_path generates the historical year/month/day/slug.html layout."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )
        generator.generate()

        # first-post.md has date 2024-01-15 and no date prefix in slug.
        post_file = temp_output_dir / "2024" / "01" / "15" / "first-post.html"
        assert post_file.exists()

    def test_custom_post_path_slug_only(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """A slug-only post_path places all posts flat in the output directory."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                post_path="{slug}.html",
            )
        )
        generator.generate()

        # With {slug}.html, first-post.html should be directly in output_dir.
        post_file = temp_output_dir / "first-post.html"
        assert post_file.exists()
        content = post_file.read_text()
        assert "My First Post" in content

    def test_custom_post_path_per_post_directory(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """A template ending in index.html gives every post its own directory."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                post_path="{year}/{month}/{day}/{slug}/index.html",
            )
        )
        generator.generate()

        post_file = temp_output_dir / "2024" / "01" / "15" / "first-post" / "index.html"
        assert post_file.exists()

    def test_post_url_reflects_configured_post_path(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Post URLs in generated HTML reflect the configured post_path scheme."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                post_path="posts/{slug}.html",
            )
        )
        generator.generate()

        # The index page lists posts with links; the URL should use the new scheme.
        index_content = (temp_output_dir / "index.html").read_text()
        assert "/posts/first-post.html" in index_content

    def test_post_url_property_set_after_generation(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """After _resolve_post_output_paths the post url_path is set."""
        from blogmore.parser import post_sort_key

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                post_path="posts/{slug}.html",
            )
        )
        parser = generator.parser
        posts = parser.parse_directory(posts_dir)
        posts.sort(key=post_sort_key, reverse=True)

        generator._resolve_post_output_paths(posts)

        dated = [p for p in posts if p.date is not None]
        assert dated, "Test requires at least one dated post in fixtures"

        for post in dated:
            assert post.url_path is not None
            assert post.url_path.startswith("/posts/")

    def test_post_path_clash_warning_emitted(
        self, tmp_path: Path, temp_output_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When two posts would share the same output path a WARNING is printed."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Both posts have different dates but the slug-only template means
        # they would clash only if the slugs are the same.  Use identical slugs.
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: Post A\ndate: 2024-01-01\n---\n\nContent A."
        )
        (content_dir / "2024-06-01-post.md").write_text(
            "---\ntitle: Post B\ndate: 2024-06-01\n---\n\nContent B."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                # slug-only: both "post.md" files resolve to "post.html"
                post_path="{slug}.html",
            )
        )
        generator.generate()

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "clash" in captured.out.lower()

    def test_post_path_clash_newest_wins(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """When two posts clash, the newest post's content is in the output file."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: Older Post\ndate: 2024-01-01\n---\n\nThis is the older content."
        )
        (content_dir / "2024-06-01-post.md").write_text(
            "---\ntitle: Newer Post\ndate: 2024-06-01\n---\n\nThis is the newer content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                post_path="{slug}.html",
            )
        )
        generator.generate()

        output_file = temp_output_dir / "post.html"
        assert output_file.exists()
        content = output_file.read_text()
        assert "Newer Post" in content
        # The older post's body content must not appear in the winning file.
        assert "This is the older content." not in content

    def test_post_path_no_clash_when_unique(
        self, posts_dir: Path, temp_output_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """No WARNING is printed when all posts produce unique output paths."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )
        generator.generate()

        captured = capsys.readouterr()
        assert "WARNING" not in captured.out


class TestCleanUrls:
    """Tests for the clean_urls feature."""

    def test_clean_urls_default_is_false(self) -> None:
        """The clean_urls setting defaults to False."""
        config = SiteConfig(output_dir=Path("output"))
        assert config.clean_urls is False

    def test_clean_urls_disabled_keeps_index_html_in_url(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls is False, post URLs ending in index.html are unchanged."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-15-my-post.md").write_text(
            "---\ntitle: My Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                post_path="posts/{slug}/index.html",
                clean_urls=False,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert "/posts/my-post/index.html" in index_content
        assert "/posts/my-post/" in index_content  # the index.html version contains "/"

    def test_clean_urls_enabled_strips_index_html_from_post_url(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls is True, index.html is stripped from post URLs."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-15-my-post.md").write_text(
            "---\ntitle: My Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                post_path="posts/{slug}/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert "/posts/my-post/" in index_content
        assert "/posts/my-post/index.html" not in index_content

    def test_clean_urls_does_not_affect_non_index_html_paths(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls is True, post URLs not ending in index.html are unchanged."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-15-my-post.md").write_text(
            "---\ntitle: My Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                post_path="posts/{slug}.html",
                clean_urls=True,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert "/posts/my-post.html" in index_content

    def test_clean_urls_post_file_still_written_as_index_html(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """The output file is still index.html on disk even with clean_urls enabled."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-15-my-post.md").write_text(
            "---\ntitle: My Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                post_path="posts/{slug}/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        # The physical file still exists at the index.html path
        assert (temp_output_dir / "posts" / "my-post" / "index.html").exists()

    def test_clean_urls_canonical_url_is_clean(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls is True, canonical URL in post page has no index.html."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-15-my-post.md").write_text(
            "---\ntitle: My Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                post_path="posts/{slug}/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        post_content = (
            temp_output_dir / "posts" / "my-post" / "index.html"
        ).read_text()
        assert "https://example.com/posts/my-post/" in post_content
        assert "https://example.com/posts/my-post/index.html" not in post_content

    def test_clean_urls_feed_uses_clean_url(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls is True, the RSS/Atom feed uses clean post URLs."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-15-my-post.md").write_text(
            "---\ntitle: My Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                post_path="posts/{slug}/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        feed_content = (temp_output_dir / "feed.xml").read_text()
        assert "https://example.com/posts/my-post/" in feed_content
        assert "https://example.com/posts/my-post/index.html" not in feed_content

    def test_clean_urls_sitemap_uses_clean_url(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls and with_sitemap are both True, sitemap uses clean URLs."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-15-my-post.md").write_text(
            "---\ntitle: My Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                post_path="posts/{slug}/index.html",
                clean_urls=True,
                with_sitemap=True,
            )
        )
        generator.generate()

        sitemap_content = (temp_output_dir / "sitemap.xml").read_text()
        assert "https://example.com/posts/my-post/" in sitemap_content
        assert "https://example.com/posts/my-post/index.html" not in sitemap_content

    def test_clean_urls_prev_next_navigation_uses_clean_url(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls is True, prev/next post navigation uses clean URLs."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-15-first-post.md").write_text(
            "---\ntitle: First Post\ndate: 2024-01-15\n---\n\nContent A."
        )
        (content_dir / "2024-02-20-second-post.md").write_text(
            "---\ntitle: Second Post\ndate: 2024-02-20\n---\n\nContent B."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                post_path="posts/{slug}/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        # The first post's page should link to second post with a clean URL
        first_post_content = (
            temp_output_dir / "posts" / "first-post" / "index.html"
        ).read_text()
        assert "/posts/second-post/" in first_post_content
        assert "/posts/second-post/index.html" not in first_post_content


class TestPagePathConfiguration:
    """Tests for the configurable page_path feature."""

    def test_default_page_path_produces_flat_slug_html(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """The default page_path generates {slug}.html flat in the output directory."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_subdir = content_dir / "pages"
        pages_subdir.mkdir()
        (pages_subdir / "about.md").write_text(
            "---\ntitle: About Me\n---\n\nAbout content."
        )
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: A Post\ndate: 2024-01-01\n---\n\nPost content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
            )
        )
        generator.generate()

        # about.md should produce about.html at the root of the output directory
        about_file = temp_output_dir / "about.html"
        assert about_file.exists()
        assert "About Me" in about_file.read_text()

    def test_custom_page_path_nested_directory(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """A page_path with a subdirectory places pages in that subdirectory."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_subdir = content_dir / "pages"
        pages_subdir.mkdir()
        (pages_subdir / "about.md").write_text(
            "---\ntitle: About Me\n---\n\nAbout content."
        )
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: A Post\ndate: 2024-01-01\n---\n\nPost content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_path="pages/{slug}.html",
            )
        )
        generator.generate()

        page_file = temp_output_dir / "pages" / "about.html"
        assert page_file.exists()
        assert "About Me" in page_file.read_text()

    def test_custom_page_path_per_page_directory(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """A page_path ending in index.html gives every page its own directory."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_subdir = content_dir / "pages"
        pages_subdir.mkdir()
        (pages_subdir / "about.md").write_text(
            "---\ntitle: About Me\n---\n\nAbout content."
        )
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: A Post\ndate: 2024-01-01\n---\n\nPost content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_path="{slug}/index.html",
            )
        )
        generator.generate()

        page_file = temp_output_dir / "about" / "index.html"
        assert page_file.exists()
        assert "About Me" in page_file.read_text()

    def test_page_url_reflects_configured_page_path(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Page URLs in generated HTML (sidebar) reflect the configured page_path."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_subdir = content_dir / "pages"
        pages_subdir.mkdir()
        (pages_subdir / "about.md").write_text(
            "---\ntitle: About Me\n---\n\nAbout content."
        )
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: A Post\ndate: 2024-01-01\n---\n\nPost content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_path="pages/{slug}.html",
            )
        )
        generator.generate()

        # The index page includes sidebar page links; the URL should use the new scheme.
        index_content = (temp_output_dir / "index.html").read_text()
        assert "/pages/about.html" in index_content

    def test_page_path_deep_subdirectory_created(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """When page_path uses deeply nested directories, they are created automatically."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_subdir = content_dir / "pages"
        pages_subdir.mkdir()
        (pages_subdir / "about.md").write_text(
            "---\ntitle: About Me\n---\n\nAbout content."
        )
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: A Post\ndate: 2024-01-01\n---\n\nPost content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_path="site/pages/{slug}/index.html",
            )
        )
        generator.generate()

        page_file = temp_output_dir / "site" / "pages" / "about" / "index.html"
        assert page_file.exists()

    def test_page_clean_urls_strips_index_html(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls is True, page URLs ending in index.html are stripped."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_subdir = content_dir / "pages"
        pages_subdir.mkdir()
        (pages_subdir / "about.md").write_text(
            "---\ntitle: About Me\n---\n\nAbout content."
        )
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: A Post\ndate: 2024-01-01\n---\n\nPost content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_path="pages/{slug}/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert "/pages/about/" in index_content
        assert "/pages/about/index.html" not in index_content

    def test_page_clean_urls_disabled_keeps_index_html(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls is False, page URLs ending in index.html are unchanged."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_subdir = content_dir / "pages"
        pages_subdir.mkdir()
        (pages_subdir / "about.md").write_text(
            "---\ntitle: About Me\n---\n\nAbout content."
        )
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: A Post\ndate: 2024-01-01\n---\n\nPost content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_path="pages/{slug}/index.html",
                clean_urls=False,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert "/pages/about/index.html" in index_content

    def test_page_path_default_value(self) -> None:
        """The page_path setting defaults to {slug}.html."""
        from blogmore.page_path import DEFAULT_PAGE_PATH

        config = SiteConfig(output_dir=Path("output"))
        assert config.page_path == DEFAULT_PAGE_PATH
        assert config.page_path == "{slug}.html"

    def test_post_page_sidebar_uses_correct_page_url_with_clean_urls(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Sidebar page links on individual post pages use the configured page URL.

        Regression test: when page_path and clean_urls are configured, the page
        URLs shown in the sidebar of an individual post page must reflect those
        settings, not fall back to the default /{slug}.html scheme.
        """
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        pages_subdir = content_dir / "pages"
        pages_subdir.mkdir()
        (pages_subdir / "dotfiles.md").write_text(
            "---\ntitle: Dotfiles\n---\n\nDotfiles content."
        )
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: A Post\ndate: 2024-01-01\n---\n\nPost content."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_path="{slug}/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        # Find the generated post page and check its sidebar link for the page.
        post_file = temp_output_dir / "2024" / "01" / "01" / "post.html"
        assert post_file.exists(), f"Expected post file at {post_file}"
        post_content = post_file.read_text()
        # The sidebar link must use the clean URL scheme, not the default /{slug}.html.
        assert "/dotfiles/" in post_content, (
            "Expected clean URL /dotfiles/ in sidebar of post page"
        )
        assert "/dotfiles.html" not in post_content, (
            "Unexpected default URL /dotfiles.html found in sidebar of post page"
        )


class TestCacheBusting:
    """Test that stylesheets are served with generation-specific cache-busting tokens."""

    def test_main_stylesheet_has_cache_bust_token(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the main stylesheet URL contains a cache-busting token."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert "/static/style.css?v=" in content

    def test_minified_stylesheet_has_cache_bust_token(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the minified stylesheet URL contains a cache-busting token."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                minify_css=True,
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert "/static/style.min.css?v=" in content

    def test_cache_bust_token_is_numeric(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the cache-busting token is a numeric unix timestamp."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        match = re.search(r"/static/style\.css\?v=(\d+)", content)
        assert match is not None
        token = match.group(1)
        assert token.isdigit()

    def test_cache_bust_token_consistent_across_pages(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the same cache-busting token appears on every page."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )

        generator.generate()

        # Collect token from index page
        index_content = (temp_output_dir / "index.html").read_text()
        match = re.search(r"/static/style\.css\?v=(\d+)", index_content)
        assert match is not None
        token = match.group(1)

        # Every generated HTML file should use the same token
        for html_file in temp_output_dir.rglob("*.html"):
            page_content = html_file.read_text()
            if "/static/style.css" in page_content:
                assert f"/static/style.css?v={token}" in page_content, (
                    f"File {html_file} uses a different cache-busting token"
                )

    def test_new_generation_produces_different_token(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that successive generate() calls produce different cache-bust tokens."""
        first_output = tmp_path / "first"
        second_output = tmp_path / "second"

        first_generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=first_output,
            )
        )
        first_generator.generate()

        # Small delay to ensure timestamps differ
        time.sleep(1.1)

        second_generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=second_output,
            )
        )
        second_generator.generate()

        first_content = (first_output / "index.html").read_text()
        second_content = (second_output / "index.html").read_text()

        first_match = re.search(r"/static/style\.css\?v=(\d+)", first_content)
        second_match = re.search(r"/static/style\.css\?v=(\d+)", second_content)

        assert first_match is not None
        assert second_match is not None
        assert first_match.group(1) != second_match.group(1)

    def test_local_extra_stylesheet_has_cache_bust_token(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that local extra stylesheets are served with a cache-busting token."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                extra_stylesheets=["/custom.css"],
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert "/custom.css?v=" in content

    def test_external_extra_stylesheet_not_cache_busted(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that external extra stylesheets are not modified with cache-busting."""
        external_url = "https://example.com/custom.css"
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                extra_stylesheets=[external_url],
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert external_url in content
        assert f"{external_url}?v=" not in content


class TestHeadTags:
    """Tests for the extra head tags feature."""

    def test_head_default_is_empty_list(self) -> None:
        """The head setting defaults to an empty list."""
        config = SiteConfig(output_dir=Path("output"))
        assert config.head == []

    def test_head_in_global_context(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The extra_head_tags key is present in the global template context."""
        head = [{"link": {"rel": "author", "href": "/humans.txt"}}]
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                head=head,
            )
        )

        context = generator._get_global_context()

        assert "extra_head_tags" in context
        assert context["extra_head_tags"] == head

    def test_head_empty_in_global_context(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When head is empty, extra_head_tags is an empty list in the context."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )

        context = generator._get_global_context()

        assert context["extra_head_tags"] == []

    def test_head_tags_rendered_in_index_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Extra head tags are rendered into the index page."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                head=[
                    {"link": {"rel": "author", "href": "/humans.txt"}},
                    {"meta": {"name": "theme-color", "content": "#ffffff"}},
                ],
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert '<link rel="author" href="/humans.txt">' in content
        assert '<meta name="theme-color" content="#ffffff">' in content

    def test_head_tags_rendered_in_post_page(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Extra head tags are rendered into individual post pages."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-15-my-post.md").write_text(
            "---\ntitle: My Post\ndate: 2024-01-15\n---\n\nContent."
        )

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                head=[{"link": {"rel": "human-json", "href": "/human.json"}}],
            )
        )

        generator.generate()

        post_content = (
            temp_output_dir / "2024" / "01" / "15" / "my-post.html"
        ).read_text()
        assert '<link rel="human-json" href="/human.json">' in post_content

    def test_head_tags_attribute_values_quoted(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Head tag attribute values are always emitted in double quotes."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                head=[{"meta": {"name": "robots", "content": "index, follow"}}],
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="robots" content="index, follow">' in content

    def test_head_tag_integer_attribute_value_is_stringified(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Integer attribute values are converted to strings in the output."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                head=[{"meta": {"http-equiv": "refresh", "content": 30}}],
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta http-equiv="refresh" content="30">' in content

    def test_no_head_tags_no_extra_markup(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When head is empty, no extra markup is injected into the head."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        # Ensure the extra_head_tags block does not appear
        assert "extra_head_tags" not in content

    def test_multiple_head_tags_all_rendered(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Multiple head tags are all rendered in the output."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                head=[
                    {"link": {"rel": "human-json", "href": "/human.json"}},
                    {"meta": {"name": "example", "content": "wibble"}},
                    {
                        "link": {
                            "type": "text/plain",
                            "rel": "author",
                            "href": "/humans.txt",
                        }
                    },
                ],
            )
        )

        generator.generate()

        content = (temp_output_dir / "index.html").read_text()
        assert '<link rel="human-json" href="/human.json">' in content
        assert '<meta name="example" content="wibble">' in content
        assert '<link type="text/plain" rel="author" href="/humans.txt">' in content


class TestSearchPathConfiguration:
    """Tests for the configurable search_path feature."""

    def test_default_search_path_generates_search_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The default search_path generates search.html at the output root."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "search.html").exists()

    def test_custom_search_path_generates_file_at_configured_location(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """A custom search_path generates the search page at the specified path."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
                search_path="find/search.html",
            )
        )
        generator.generate()

        assert (temp_output_dir / "find" / "search.html").exists()
        assert not (temp_output_dir / "search.html").exists()

    def test_custom_search_path_creates_intermediate_directories(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Intermediate directories are created when search_path uses subdirectories."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
                search_path="a/b/c/search.html",
            )
        )
        generator.generate()

        assert (temp_output_dir / "a" / "b" / "c" / "search.html").exists()

    def test_search_url_in_nav_reflects_custom_search_path(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Search link in the navigation bar uses the configured search_path URL."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
                search_path="find/search.html",
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/find/search.html"' in index_content
        assert 'href="/search.html"' not in index_content

    def test_search_form_action_reflects_custom_search_path(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The search form action attribute uses the configured search_path URL."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
                search_path="find/search.html",
            )
        )
        generator.generate()

        search_content = (temp_output_dir / "find" / "search.html").read_text()
        assert 'action="/find/search.html"' in search_content

    def test_search_path_index_html_with_clean_urls_strips_filename(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When search_path ends in index.html and clean_urls is True, the URL is cleaned."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
                search_path="search/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        # File is still written to the full path
        assert (temp_output_dir / "search" / "index.html").exists()

        # Navigation link uses the clean URL
        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/search/"' in index_content
        assert 'href="/search/index.html"' not in index_content

    def test_search_path_index_html_clean_urls_form_action_is_clean(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls is True and search_path ends in index.html, form action is clean."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
                search_path="search/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        search_content = (temp_output_dir / "search" / "index.html").read_text()
        assert 'action="/search/"' in search_content
        assert 'action="/search/index.html"' not in search_content

    def test_search_path_clean_urls_disabled_keeps_index_html_in_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls is False, search URL with index.html suffix is unchanged."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
                search_path="search/index.html",
                clean_urls=False,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/search/index.html"' in index_content

    def test_search_path_default_value(self) -> None:
        """The search_path setting defaults to search.html."""
        from blogmore.site_config import DEFAULT_SEARCH_PATH

        config = SiteConfig(output_dir=Path("output"))
        assert config.search_path == DEFAULT_SEARCH_PATH
        assert config.search_path == "search.html"

    def test_stale_search_page_removed_at_custom_path_when_search_disabled(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Stale search page at the configured path is removed when search is disabled."""
        # Build with custom search_path
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
                search_path="find/search.html",
            )
        )
        generator.generate()
        assert (temp_output_dir / "find" / "search.html").exists()

        # Rebuild with search disabled (same search_path)
        generator2 = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=False,
                search_path="find/search.html",
            )
        )
        generator2.generate()
        assert not (temp_output_dir / "find" / "search.html").exists()

    def test_search_index_json_stays_in_root(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The search index JSON is always written to the output root, regardless of search_path."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
                search_path="find/search.html",
            )
        )
        generator.generate()

        assert (temp_output_dir / "search_index.json").exists()
        assert not (temp_output_dir / "find" / "search_index.json").exists()

    def test_search_path_with_leading_slash_is_treated_as_relative(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """A search_path with a leading slash is treated as relative to the output dir."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
                search_path="/search/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        # File is written under the output dir, not at the filesystem root.
        assert (temp_output_dir / "search" / "index.html").exists()

        # Navigation link uses the clean URL.
        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/search/"' in index_content


class TestArchivePathConfiguration:
    """Tests for the configurable archive_path feature."""

    def test_default_archive_path_generates_archive_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The default archive_path generates archive.html at the output root."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )
        generator.generate()

        assert (temp_output_dir / "archive.html").exists()

    def test_custom_archive_path_generates_file_at_configured_location(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """A custom archive_path generates the archive page at the specified path."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                archive_path="blog/archive.html",
            )
        )
        generator.generate()

        assert (temp_output_dir / "blog" / "archive.html").exists()
        assert not (temp_output_dir / "archive.html").exists()

    def test_custom_archive_path_creates_intermediate_directories(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Intermediate directories are created when archive_path uses subdirectories."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                archive_path="a/b/c/archive.html",
            )
        )
        generator.generate()

        assert (temp_output_dir / "a" / "b" / "c" / "archive.html").exists()

    def test_archive_url_in_nav_reflects_custom_archive_path(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Archive link in the navigation bar uses the configured archive_path URL."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                archive_path="blog/archive.html",
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/blog/archive.html"' in index_content
        assert 'href="/archive.html"' not in index_content

    def test_archive_path_index_html_with_clean_urls_strips_filename(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When archive_path ends in index.html and clean_urls is True, the URL is cleaned."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                archive_path="archive/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        # File is still written to the full path.
        assert (temp_output_dir / "archive" / "index.html").exists()

        # Navigation link uses the clean URL.
        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/archive/"' in index_content
        assert 'href="/archive/index.html"' not in index_content

    def test_archive_path_clean_urls_disabled_keeps_index_html_in_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls is False, archive URL with index.html suffix is unchanged."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                archive_path="archive/index.html",
                clean_urls=False,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/archive/index.html"' in index_content

    def test_archive_path_default_value(self) -> None:
        """The archive_path setting defaults to archive.html."""
        from blogmore.site_config import DEFAULT_ARCHIVE_PATH

        config = SiteConfig(output_dir=Path("output"))
        assert config.archive_path == DEFAULT_ARCHIVE_PATH
        assert config.archive_path == "archive.html"

    def test_archive_path_with_leading_slash_is_treated_as_relative(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """A archive_path with a leading slash is treated as relative to the output dir."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                archive_path="/archive/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "archive" / "index.html").exists()

        # Navigation link uses the clean URL.
        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/archive/"' in index_content

    def test_archive_path_canonical_url_with_site_url_and_clean_urls(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Canonical URL on the archive page uses site_url + clean URL when clean_urls is on."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                archive_path="archive/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        archive_content = (temp_output_dir / "archive" / "index.html").read_text()
        assert (
            '<link rel="canonical" href="https://example.com/archive/">'
            in archive_content
        )


class TestPaginationPathConfiguration:
    """Tests for the configurable page_1_path and page_n_path features."""

    def test_default_page_1_path_is_index_html(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """With default settings, page 1 of the main index is index.html."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-01\n---\n\nContent."
        )
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()
        assert (temp_output_dir / "index.html").exists()

    def test_default_page_n_path_uses_page_dir(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """With default settings, page 2+ of the main index uses page/{page}.html."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\n---\n\nContent {i}."
            )
        generator = SiteGenerator(
            site_config=SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)
        )
        generator.generate()
        assert (temp_output_dir / "page" / "2.html").exists()

    def test_custom_page_1_path_changes_main_index_output(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """page_1_path does NOT change the main index; it always stays at index.html."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-01\n---\n\nContent."
        )
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_1_path="start.html",
            )
        )
        generator.generate()
        # Main index is always index.html regardless of page_1_path.
        assert (temp_output_dir / "index.html").exists()
        assert not (temp_output_dir / "start.html").exists()

    def test_custom_page_n_path_changes_subsequent_page_output(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """A custom page_n_path changes where pages 2+ of the main index are written."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\n---\n\nContent {i}."
            )
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_n_path="p{page}.html",
            )
        )
        generator.generate()
        assert (temp_output_dir / "p2.html").exists()
        assert not (temp_output_dir / "page" / "2.html").exists()

    def test_custom_page_1_path_subdirectory(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """A page_1_path with a subdirectory is applied to archive pages (not main index)."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        for i in range(1, 5):
            (content_dir / f"2024-01-{i:02d}-post.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\n---\n\nContent."
            )
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_1_path="posts/index.html",
            )
        )
        generator.generate()
        # Main index is always index.html.
        assert (temp_output_dir / "index.html").exists()
        # Year archive page 1 uses page_1_path.
        assert (temp_output_dir / "2024" / "posts" / "index.html").exists()

    def test_page_1_path_with_page_placeholder(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """The {page} placeholder works in page_1_path for archive/tag pages (not main index)."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        for i in range(1, 5):
            (content_dir / f"2024-01-{i:02d}-post.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\n---\n\nContent."
            )
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_1_path="page-{page}.html",
            )
        )
        generator.generate()
        # Main index is always index.html regardless of page_1_path.
        assert (temp_output_dir / "index.html").exists()
        assert not (temp_output_dir / "page-1.html").exists()
        # Year archive page 1 uses page_1_path → page-1.html.
        assert (temp_output_dir / "2024" / "page-1.html").exists()

    def test_custom_paths_apply_to_year_archive(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Custom page_1_path and page_n_path apply to year archive pages."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\n---\n\nContent {i}."
            )
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_1_path="all.html",
                page_n_path="p{page}.html",
            )
        )
        generator.generate()
        year_dir = temp_output_dir / "2024"
        assert (year_dir / "all.html").exists()
        assert (year_dir / "p2.html").exists()

    def test_custom_paths_apply_to_tag_pages(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Custom page_1_path and page_n_path apply to tag listing pages."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\ntags: [python]\n---\n\nContent {i}."
            )
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_1_path="first.html",
                page_n_path="p{page}.html",
            )
        )
        generator.generate()
        tag_base_dir = temp_output_dir / "tag" / "python"
        assert (tag_base_dir / "first.html").exists()
        assert (tag_base_dir / "p2.html").exists()

    def test_custom_paths_apply_to_category_pages(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Custom page_1_path and page_n_path apply to category listing pages."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\ncategory: Tech\n---\n\nContent {i}."
            )
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_1_path="first.html",
                page_n_path="p{page}.html",
            )
        )
        generator.generate()
        cat_base_dir = temp_output_dir / "category" / "tech"
        assert (cat_base_dir / "first.html").exists()
        assert (cat_base_dir / "p2.html").exists()

    def test_pagination_page_urls_in_context_match_page_1_path(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Main index page 1 is always /index.html; page 2's prev link points to /index.html."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\n---\n\nContent {i}."
            )
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_1_path="start.html",
                page_n_path="p{page}.html",
            )
        )
        generator.generate()

        # Main index page 1 is always index.html regardless of page_1_path.
        assert (temp_output_dir / "index.html").exists()
        # Page 2 of the main index should link back to /index.html (not /start.html).
        page2_content = (temp_output_dir / "p2.html").read_text()
        assert 'href="/index.html"' in page2_content

    def test_pagination_page_urls_in_context_match_page_n_path(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Pagination links in rendered HTML reflect the configured page_n_path."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\n---\n\nContent {i}."
            )
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                page_1_path="index.html",
                page_n_path="p{page}.html",
            )
        )
        generator.generate()

        # Page 1 should link to p2.html as next
        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/p2.html"' in index_content

    def test_clean_urls_applied_to_page_1_path(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """With clean_urls enabled, page_1_path index.html links use trailing slash."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        for i in range(1, 12):
            (content_dir / f"2024-01-{i:02d}-post-{i}.md").write_text(
                f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\n---\n\nContent {i}."
            )
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                clean_urls=True,
            )
        )
        generator.generate()

        # Page 2 should link back to / (clean URL for /index.html) as prev
        page2_content = (temp_output_dir / "page" / "2.html").read_text()
        assert 'href="/"' in page2_content

    def test_pagination_page1_suffix_in_tag_links(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Tag links in post summaries use the resolved page_1_path suffix."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-01\ntags: [python]\n---\n\nContent."
        )
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
            )
        )
        generator.generate()

        # Default page_1_path = "index.html", so tag links on index should use /tag/python/index.html
        index_content = (temp_output_dir / "index.html").read_text()
        assert "/tag/python/index.html" in index_content

    def test_pagination_page1_suffix_with_clean_urls(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """With clean_urls, tag links in post summaries use trailing slash form."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "2024-01-01-post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-01\ntags: [python]\n---\n\nContent."
        )
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=content_dir,
                output_dir=temp_output_dir,
                clean_urls=True,
            )
        )
        generator.generate()

        # With clean_urls, tag links should use /tag/python/ (trailing slash)
        index_content = (temp_output_dir / "index.html").read_text()
        assert "/tag/python/" in index_content
        assert "/tag/python/index.html" not in index_content


class TestTagsPathConfiguration:
    """Tests for the configurable tags_path feature."""

    def test_default_tags_path_generates_tags_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The default tags_path generates tags.html at the output root."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )
        generator.generate()

        assert (temp_output_dir / "tags.html").exists()

    def test_custom_tags_path_generates_file_at_configured_location(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """A custom tags_path generates the tags page at the specified path."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                tags_path="blog/tags.html",
            )
        )
        generator.generate()

        assert (temp_output_dir / "blog" / "tags.html").exists()
        assert not (temp_output_dir / "tags.html").exists()

    def test_custom_tags_path_creates_intermediate_directories(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Intermediate directories are created when tags_path uses subdirectories."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                tags_path="a/b/c/tags.html",
            )
        )
        generator.generate()

        assert (temp_output_dir / "a" / "b" / "c" / "tags.html").exists()

    def test_tags_url_in_nav_reflects_custom_tags_path(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Tags link in the navigation bar uses the configured tags_path URL."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                tags_path="blog/tags.html",
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/blog/tags.html"' in index_content
        assert 'href="/tags.html"' not in index_content

    def test_tags_path_index_html_with_clean_urls_strips_filename(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When tags_path ends in index.html and clean_urls is True, the URL is cleaned."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                tags_path="tags/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        # File is still written to the full path.
        assert (temp_output_dir / "tags" / "index.html").exists()

        # Navigation link uses the clean URL.
        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/tags/"' in index_content
        assert 'href="/tags/index.html"' not in index_content

    def test_tags_path_clean_urls_disabled_keeps_index_html_in_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls is False, tags URL with index.html suffix is unchanged."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                tags_path="tags/index.html",
                clean_urls=False,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/tags/index.html"' in index_content

    def test_tags_path_default_value(self) -> None:
        """The tags_path setting defaults to tags.html."""
        from blogmore.site_config import DEFAULT_TAGS_PATH

        config = SiteConfig(output_dir=Path("output"))
        assert config.tags_path == DEFAULT_TAGS_PATH
        assert config.tags_path == "tags.html"

    def test_tags_path_with_leading_slash_is_treated_as_relative(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """A tags_path with a leading slash is treated as relative to the output dir."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                tags_path="/tags/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "tags" / "index.html").exists()

        # Navigation link uses the clean URL.
        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/tags/"' in index_content

    def test_tags_path_canonical_url_with_site_url_and_clean_urls(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Canonical URL on the tags page uses site_url + clean URL when clean_urls is on."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                tags_path="tags/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        tags_content = (temp_output_dir / "tags" / "index.html").read_text()
        assert '<link rel="canonical" href="https://example.com/tags/">' in tags_content


class TestCategoriesPathConfiguration:
    """Tests for the configurable categories_path feature."""

    def test_default_categories_path_generates_categories_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The default categories_path generates categories.html at the output root."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )
        generator.generate()

        assert (temp_output_dir / "categories.html").exists()

    def test_custom_categories_path_generates_file_at_configured_location(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """A custom categories_path generates the categories page at the specified path."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                categories_path="blog/categories.html",
            )
        )
        generator.generate()

        assert (temp_output_dir / "blog" / "categories.html").exists()
        assert not (temp_output_dir / "categories.html").exists()

    def test_custom_categories_path_creates_intermediate_directories(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Intermediate directories are created when categories_path uses subdirectories."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                categories_path="a/b/c/categories.html",
            )
        )
        generator.generate()

        assert (temp_output_dir / "a" / "b" / "c" / "categories.html").exists()

    def test_categories_url_in_nav_reflects_custom_categories_path(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Categories link in the navigation bar uses the configured categories_path URL."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                categories_path="blog/categories.html",
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/blog/categories.html"' in index_content
        assert 'href="/categories.html"' not in index_content

    def test_categories_path_index_html_with_clean_urls_strips_filename(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When categories_path ends in index.html and clean_urls is True, the URL is cleaned."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                categories_path="categories/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        # File is still written to the full path.
        assert (temp_output_dir / "categories" / "index.html").exists()

        # Navigation link uses the clean URL.
        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/categories/"' in index_content
        assert 'href="/categories/index.html"' not in index_content

    def test_categories_path_clean_urls_disabled_keeps_index_html_in_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls is False, categories URL with index.html suffix is unchanged."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                categories_path="categories/index.html",
                clean_urls=False,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/categories/index.html"' in index_content

    def test_categories_path_default_value(self) -> None:
        """The categories_path setting defaults to categories.html."""
        from blogmore.site_config import DEFAULT_CATEGORIES_PATH

        config = SiteConfig(output_dir=Path("output"))
        assert config.categories_path == DEFAULT_CATEGORIES_PATH
        assert config.categories_path == "categories.html"

    def test_categories_path_with_leading_slash_is_treated_as_relative(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """A categories_path with a leading slash is treated as relative to the output dir."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                categories_path="/categories/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "categories" / "index.html").exists()

        # Navigation link uses the clean URL.
        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/categories/"' in index_content

    def test_categories_path_canonical_url_with_site_url_and_clean_urls(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Canonical URL on the categories page uses site_url + clean URL when clean_urls is on."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                categories_path="categories/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        categories_content = (temp_output_dir / "categories" / "index.html").read_text()
        assert (
            '<link rel="canonical" href="https://example.com/categories/">'
            in categories_content
        )


class TestStatsPageGeneration:
    """Tests for the stats page (with_stats) feature."""

    def test_stats_disabled_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """stats.html is NOT generated when with_stats is False (the default)."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )
        generator.generate()

        assert not (temp_output_dir / "stats.html").exists()

    def test_stats_enabled_generates_stats_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """stats.html is generated when with_stats=True."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "stats.html").exists()

    def test_stats_nav_link_absent_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Stats nav link does not appear when with_stats is False."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert "/stats.html" not in index_content

    def test_stats_nav_link_present_when_enabled(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Stats nav link appears in the navigation when with_stats=True."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/stats.html"' in index_content

    def test_stats_nav_link_appears_after_search_before_rss(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Stats link comes after Search and before the RSS link in the nav."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_search=True,
                with_stats=True,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        # Isolate just the <nav> element to avoid matching feed links in <head>.
        nav_start = index_content.find("<nav>")
        nav_end = index_content.find("</nav>", nav_start) + len("</nav>")
        nav_content = index_content[nav_start:nav_end]

        search_pos = nav_content.find('href="/search.html"')
        stats_pos = nav_content.find('href="/stats.html"')
        rss_pos = nav_content.find('href="/feed.xml"')

        assert search_pos != -1
        assert stats_pos != -1
        assert rss_pos != -1
        assert search_pos < stats_pos < rss_pos

    def test_stats_page_contains_histogram_sections(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The generated stats page contains the expected histogram section headers."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
            )
        )
        generator.generate()

        stats_content = (temp_output_dir / "stats.html").read_text()
        assert "Posts by Hour of Day" in stats_content
        assert "Posts by Day of Week" in stats_content
        assert "Posts by Month of Year" in stats_content

    def test_stats_page_contains_word_count_section(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The stats page includes the word count detail section."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
            )
        )
        generator.generate()

        stats_content = (temp_output_dir / "stats.html").read_text()
        assert "Word Count" in stats_content

    def test_stats_page_contains_reading_time_section(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The stats page includes the reading time detail section when with_read_time is True."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
                with_read_time=True,
            )
        )
        generator.generate()

        stats_content = (temp_output_dir / "stats.html").read_text()
        assert "Reading Time" in stats_content

    def test_stats_page_omits_reading_time_section_when_with_read_time_disabled(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The stats page omits the reading time section when with_read_time is False."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
                with_read_time=False,
            )
        )
        generator.generate()

        stats_content = (temp_output_dir / "stats.html").read_text()
        assert "Reading Time" not in stats_content

    def test_stats_page_contains_content_overview_section(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The stats page includes the content overview section."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
            )
        )
        generator.generate()

        stats_content = (temp_output_dir / "stats.html").read_text()
        assert "Content Overview" in stats_content

    def test_custom_stats_path(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """A custom stats_path generates the stats page at the specified location."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
                stats_path="data/blog-stats.html",
            )
        )
        generator.generate()

        assert (temp_output_dir / "data" / "blog-stats.html").exists()
        assert not (temp_output_dir / "stats.html").exists()

    def test_custom_stats_path_nav_link_uses_configured_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Stats nav link uses the custom stats_path URL."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
                stats_path="data/blog-stats.html",
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/data/blog-stats.html"' in index_content
        assert 'href="/stats.html"' not in index_content

    def test_stats_path_clean_urls_strips_index_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """With clean_urls enabled and stats_path ending in index.html, the nav link is clean."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
                stats_path="stats/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "stats" / "index.html").exists()
        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/stats/"' in index_content

    def test_stats_path_default_value(self) -> None:
        """The stats_path setting defaults to stats.html."""
        from blogmore.site_config import DEFAULT_STATS_PATH

        config = SiteConfig(output_dir=Path("output"))
        assert config.stats_path == DEFAULT_STATS_PATH
        assert config.stats_path == "stats.html"

    def test_stats_canonical_url_with_site_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The stats page canonical URL includes the site_url."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
                site_url="https://example.com",
            )
        )
        generator.generate()

        stats_content = (temp_output_dir / "stats.html").read_text()
        assert (
            '<link rel="canonical" href="https://example.com/stats.html">'
            in stats_content
        )

    def test_stats_canonical_url_clean_url_with_site_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Canonical URL on stats page uses site_url + clean URL when clean_urls is on."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
                site_url="https://example.com",
                stats_path="stats/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        stats_content = (temp_output_dir / "stats" / "index.html").read_text()
        assert (
            '<link rel="canonical" href="https://example.com/stats/">' in stats_content
        )

    def test_stats_page_does_not_have_noindex(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The stats page must not carry a noindex robots directive."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_stats=True,
            )
        )
        generator.generate()

        stats_content = (temp_output_dir / "stats.html").read_text()
        assert "noindex" not in stats_content

    def test_stats_page_included_in_sitemap(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The stats page must be present in the sitemap when with_sitemap is enabled."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                site_url="https://example.com",
                with_stats=True,
                with_sitemap=True,
            )
        )
        generator.generate()

        sitemap_content = (temp_output_dir / "sitemap.xml").read_text()
        assert "stats.html" in sitemap_content


class TestCalendarPageGeneration:
    """Tests for the calendar page (with_calendar) feature."""

    def test_calendar_disabled_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """calendar.html is NOT generated when with_calendar is False (the default)."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )
        generator.generate()

        assert not (temp_output_dir / "calendar.html").exists()

    def test_calendar_enabled_generates_calendar_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """calendar.html is generated when with_calendar=True."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_calendar=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "calendar.html").exists()

    def test_calendar_nav_link_absent_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Calendar nav link does not appear when with_calendar is False."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert "/calendar.html" not in index_content

    def test_calendar_nav_link_present_when_enabled(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Calendar nav link appears in the navigation when with_calendar=True."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_calendar=True,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/calendar.html"' in index_content

    def test_calendar_page_links_calendar_css(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The calendar page includes the calendar-specific CSS file."""
        from blogmore.generator import CALENDAR_CSS_FILENAME

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_calendar=True,
            )
        )
        generator.generate()

        calendar_content = (temp_output_dir / "calendar.html").read_text()
        assert f"/static/{CALENDAR_CSS_FILENAME}" in calendar_content

    def test_calendar_page_contains_year_labels(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The calendar page contains year section labels from the posts."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_calendar=True,
            )
        )
        generator.generate()

        calendar_content = (temp_output_dir / "calendar.html").read_text()
        assert "calendar-year-label" in calendar_content

    def test_custom_calendar_path(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """A custom calendar_path generates the calendar page at the specified location."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_calendar=True,
                calendar_path="blog/history.html",
            )
        )
        generator.generate()

        assert (temp_output_dir / "blog" / "history.html").exists()
        assert not (temp_output_dir / "calendar.html").exists()

    def test_custom_calendar_path_nav_link_uses_configured_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Calendar nav link uses the custom calendar_path URL."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_calendar=True,
                calendar_path="blog/history.html",
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/blog/history.html"' in index_content
        assert 'href="/calendar.html"' not in index_content

    def test_calendar_path_clean_urls_strips_index_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """With clean_urls enabled and calendar_path ending in index.html, the nav link is clean."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_calendar=True,
                calendar_path="calendar/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "calendar" / "index.html").exists()
        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/calendar/"' in index_content

    def test_calendar_path_default_value(self) -> None:
        """The calendar_path setting defaults to calendar.html."""
        from blogmore.site_config import DEFAULT_CALENDAR_PATH

        config = SiteConfig(output_dir=Path("output"))
        assert config.calendar_path == DEFAULT_CALENDAR_PATH
        assert config.calendar_path == "calendar.html"

    def test_calendar_canonical_url_with_site_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The calendar page canonical URL includes the site_url."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_calendar=True,
                site_url="https://example.com",
            )
        )
        generator.generate()

        calendar_content = (temp_output_dir / "calendar.html").read_text()
        assert (
            '<link rel="canonical" href="https://example.com/calendar.html">'
            in calendar_content
        )

    def test_forward_calendar_default_is_false(self) -> None:
        """forward_calendar defaults to False on SiteConfig."""
        config = SiteConfig(output_dir=Path("output"))
        assert config.forward_calendar is False

    def test_forward_calendar_generates_monday_first_headers(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When forward_calendar=True the template renders M T W T F S S headers."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_calendar=True,
                forward_calendar=True,
            )
        )
        generator.generate()

        calendar_content = (temp_output_dir / "calendar.html").read_text()
        # The DOW header row for a forward calendar should start with M (Monday).
        # We look for the sequential M T W T pattern (Monday-Tuesday-Wednesday-Thursday).
        assert "calendar-dow" in calendar_content
        # Find the section containing the day-of-week headers; Monday should appear
        # before Sunday in forward mode.
        first_m_pos = calendar_content.find(">M<")
        first_s_pos = calendar_content.find(">S<")
        assert first_m_pos < first_s_pos

    def test_calendar_clean_urls_strips_index_html_from_year_links(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls=True, year archive links in the calendar omit index.html."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_calendar=True,
                clean_urls=True,
            )
        )
        generator.generate()

        calendar_content = (temp_output_dir / "calendar.html").read_text()
        # Clean URLs: year links should end with a trailing slash, not /index.html.
        assert 'href="/2024/index.html"' not in calendar_content
        assert 'href="/2024/"' in calendar_content

    def test_calendar_clean_urls_strips_index_html_from_month_links(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls=True, month archive links in the calendar omit index.html."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_calendar=True,
                clean_urls=True,
            )
        )
        generator.generate()

        calendar_content = (temp_output_dir / "calendar.html").read_text()
        # Clean URLs: month links should end with a trailing slash, not /index.html.
        assert 'href="/2024/01/index.html"' not in calendar_content
        assert 'href="/2024/01/"' in calendar_content

    def test_calendar_clean_urls_strips_index_html_from_day_links(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls=True, day archive links in the calendar omit index.html."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_calendar=True,
                clean_urls=True,
            )
        )
        generator.generate()

        calendar_content = (temp_output_dir / "calendar.html").read_text()
        # Clean URLs: day links should end with a trailing slash, not /index.html.
        # The fixtures include a post on 2024-01-10 and 2024-01-15.
        assert 'href="/2024/01/10/index.html"' not in calendar_content
        assert 'href="/2024/01/10/"' in calendar_content

    def test_calendar_without_clean_urls_keeps_index_html_in_archive_links(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """When clean_urls=False, calendar archive links retain the index.html suffix."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_calendar=True,
                clean_urls=False,
            )
        )
        generator.generate()

        calendar_content = (temp_output_dir / "calendar.html").read_text()
        # Without clean URLs: links include the full index.html suffix.
        assert 'href="/2024/index.html"' in calendar_content
        assert 'href="/2024/01/index.html"' in calendar_content
        assert 'href="/2024/01/10/index.html"' in calendar_content


class TestGraphPageGeneration:
    """Tests for the graph page (with_graph) feature."""

    def test_graph_disabled_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """graph.html is NOT generated when with_graph is False (the default)."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )
        generator.generate()

        assert not (temp_output_dir / "graph.html").exists()

    def test_graph_enabled_generates_graph_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """graph.html is generated when with_graph=True."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_graph=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "graph.html").exists()

    def test_graph_nav_link_absent_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Graph nav link does not appear when with_graph is False."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert "/graph.html" not in index_content

    def test_graph_nav_link_present_when_enabled(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Graph nav link appears in the navigation when with_graph=True."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_graph=True,
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/graph.html"' in index_content

    def test_graph_page_links_graph_css(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The graph page includes the graph-specific CSS file."""
        from blogmore.generator import GRAPH_CSS_FILENAME

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_graph=True,
            )
        )
        generator.generate()

        graph_content = (temp_output_dir / "graph.html").read_text()
        assert f"/static/{GRAPH_CSS_FILENAME}" in graph_content

    def test_graph_page_contains_force_graph_cdn(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The graph JS file loads the force-graph library from CDN."""
        from blogmore.generator import GRAPH_JS_FILENAME

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_graph=True,
            )
        )
        generator.generate()

        graph_js_content = (temp_output_dir / "static" / GRAPH_JS_FILENAME).read_text()
        assert "force-graph" in graph_js_content

    def test_graph_page_contains_graph_data(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The graph page embeds graph data JSON."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_graph=True,
            )
        )
        generator.generate()

        graph_content = (temp_output_dir / "graph.html").read_text()
        assert '"nodes"' in graph_content
        assert '"links"' in graph_content

    def test_custom_graph_path(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """A custom graph_path generates the graph page at the specified location."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_graph=True,
                graph_path="blog/graph.html",
            )
        )
        generator.generate()

        assert (temp_output_dir / "blog" / "graph.html").exists()
        assert not (temp_output_dir / "graph.html").exists()

    def test_custom_graph_path_nav_link_uses_configured_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The Graph nav link uses the custom graph_path URL."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_graph=True,
                graph_path="blog/graph.html",
            )
        )
        generator.generate()

        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/blog/graph.html"' in index_content
        assert 'href="/graph.html"' not in index_content

    def test_graph_path_clean_urls_strips_index_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """With clean_urls enabled and graph_path ending in index.html, the nav link is clean."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_graph=True,
                graph_path="graph/index.html",
                clean_urls=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "graph" / "index.html").exists()
        index_content = (temp_output_dir / "index.html").read_text()
        assert 'href="/graph/"' in index_content

    def test_graph_path_default_value(self) -> None:
        """The graph_path setting defaults to graph.html."""
        from blogmore.site_config import DEFAULT_GRAPH_PATH

        config = SiteConfig(output_dir=Path("output"))
        assert config.graph_path == DEFAULT_GRAPH_PATH
        assert config.graph_path == "graph.html"

    def test_with_graph_default_is_false(self) -> None:
        """with_graph defaults to False on SiteConfig."""
        config = SiteConfig(output_dir=Path("output"))
        assert config.with_graph is False

    def test_graph_canonical_url_with_site_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The graph page canonical URL includes the site_url."""
        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_graph=True,
                site_url="https://example.com",
            )
        )
        generator.generate()

        graph_content = (temp_output_dir / "graph.html").read_text()
        assert (
            '<link rel="canonical" href="https://example.com/graph.html">'
            in graph_content
        )

    def test_graph_js_generated_when_graph_enabled(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """graph.js is written to the static directory when with_graph=True."""
        from blogmore.generator import GRAPH_JS_FILENAME

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_graph=True,
            )
        )
        generator.generate()

        assert (temp_output_dir / "static" / GRAPH_JS_FILENAME).exists()

    def test_graph_js_not_generated_when_graph_disabled(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """graph.js is NOT written to the static directory when with_graph=False."""
        from blogmore.generator import GRAPH_JS_FILENAME

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_graph=False,
            )
        )
        generator.generate()

        assert not (temp_output_dir / "static" / GRAPH_JS_FILENAME).exists()

    def test_graph_js_minified_when_minify_js_enabled(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """graph.min.js is written and graph.js is absent when minify_js=True."""
        from blogmore.generator import GRAPH_JS_FILENAME, minified_filename

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_graph=True,
                minify_js=True,
            )
        )
        generator.generate()

        assert (
            temp_output_dir / "static" / minified_filename(GRAPH_JS_FILENAME)
        ).exists()
        assert not (temp_output_dir / "static" / GRAPH_JS_FILENAME).exists()

    def test_graph_page_references_graph_js(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """The graph page HTML references graph.js."""
        from blogmore.generator import GRAPH_JS_FILENAME

        generator = SiteGenerator(
            site_config=SiteConfig(
                content_dir=posts_dir,
                output_dir=temp_output_dir,
                with_graph=True,
            )
        )
        generator.generate()

        graph_content = (temp_output_dir / "graph.html").read_text()
        assert f"/static/{GRAPH_JS_FILENAME}" in graph_content
