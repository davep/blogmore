"""Unit tests for the generator module."""

from pathlib import Path

import pytest

from blogmore.generator import SiteGenerator, paginate_posts, sanitize_for_url
from blogmore.parser import Post


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

    def test_init(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test initializing SiteGenerator."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_title="Test Blog",
            site_url="https://example.com",
        )

        assert generator.content_dir == posts_dir
        assert generator.output_dir == temp_output_dir
        assert generator.site_title == "Test Blog"
        assert generator.site_url == "https://example.com"

    def test_init_normalizes_trailing_slash(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that SiteGenerator normalizes site_url with trailing slash."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_title="Test Blog",
            site_url="https://example.com/",
        )

        # Trailing slash should be removed
        assert generator.site_url == "https://example.com"

    def test_init_with_custom_templates(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test initializing with custom templates directory."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=templates_dir,
            output_dir=temp_output_dir,
        )

        assert generator.templates_dir == templates_dir

    def test_generate_basic(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test basic site generation."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_title="Test Blog",
            site_url="https://example.com",
        )

        generator.generate(include_drafts=False)

        # Check that output directory has expected structure
        assert temp_output_dir.exists()
        assert (temp_output_dir / "index.html").exists()
        assert (temp_output_dir / "static").exists()
        assert (temp_output_dir / "static" / "style.css").exists()

    def test_generate_with_drafts(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test generating site including drafts."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=True)

        # Should generate successfully with drafts
        assert (temp_output_dir / "index.html").exists()

    def test_generate_creates_post_files(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that individual post HTML files are created."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        assert (temp_output_dir / "archive.html").exists()

    def test_generate_creates_tag_pages(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that tag pages are created."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        # Check for tag directory
        tag_dir = temp_output_dir / "tag"
        assert tag_dir.exists()

        # Check for specific tag pages (python tag exists in fixtures)
        assert (tag_dir / "python.html").exists()

    def test_generate_creates_category_pages(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that category pages are created."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        # Check for category directory
        category_dir = temp_output_dir / "category"
        assert category_dir.exists()

        # Check for specific category pages (python category exists in fixtures)
        assert (category_dir / "python.html").exists()

    def test_generate_creates_feeds(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that RSS and Atom feeds are created."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_url="https://example.com",
        )

        generator.generate(include_drafts=False)

        # Check for main feed
        assert (temp_output_dir / "feed.xml").exists()

        # Check for atom feed
        assert (temp_output_dir / "feeds" / "all.atom.xml").exists()

    def test_generate_copies_static_files(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that static files are copied."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        # Check that page was generated
        assert (temp_output_dir / "about.html").exists()

    def test_generate_excludes_drafts_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that drafts are excluded by default."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        # Check that draft post is NOT in index
        index_content = (temp_output_dir / "index.html").read_text()
        assert "Draft Post" not in index_content

    def test_generate_with_extra_stylesheets(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test generating with extra stylesheets."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            extra_stylesheets=["https://example.com/custom.css"],
        )

        generator.generate(include_drafts=False)

        # Check that extra stylesheet is in generated HTML
        index_content = (temp_output_dir / "index.html").read_text()
        assert "https://example.com/custom.css" in index_content

    def test_generate_with_custom_posts_per_feed(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test generating with custom posts_per_feed setting."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            posts_per_feed=5,
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        # Old file should be preserved (generator doesn't clear the directory)
        assert old_file.exists()

    def test_generate_with_no_posts(
        self, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test generating with an empty content directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        generator = SiteGenerator(
            content_dir=empty_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        # Should still generate basic structure
        assert (temp_output_dir / "index.html").exists()
        assert (temp_output_dir / "static" / "style.css").exists()

    def test_generate_tags_overview_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that tags overview page is created."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            default_author="Default Author Name",
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            default_author="Default Author Name",
        )

        generator.generate(include_drafts=False)

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
        import datetime as dt

        from blogmore.parser import Post

        # Create a temporary content directory
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create a markdown file
        post_file = content_dir / "test.md"
        post_file.write_text(
            "---\ntitle: Test\ndate: 2024-01-01\n---\n\nContent"
        )

        generator = SiteGenerator(
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            default_author="Default Author",
        )

        # Generate and verify
        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            default_author="Site Author",
        )

        generator.generate(include_drafts=False)

        index_file = temp_output_dir / "index.html"
        assert index_file.exists()

        content = index_file.read_text()
        assert '<meta name="author" content="Site Author">' in content

    def test_no_author_on_index_page_without_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that no author meta tag appears on the index page when default_author is not set."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        assert generator._detect_favicon() == "/favicon.svg"

    def test_detect_favicon_no_extras_dir(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that None is returned when extras directory doesn't exist."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        generator = SiteGenerator(
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            clean_first=True,
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            clean_first=False,
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=output_dir,
            clean_first=True,
        )

        # Should not raise an error
        generator.generate(include_drafts=False)

        # The output directory should be created with generated files
        assert output_dir.exists()
        assert (output_dir / "index.html").exists()

    def test_global_context_includes_version(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the global context includes the blogmore version."""
        from blogmore import __version__

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_title="Test Blog",
        )

        context = generator._get_global_context()

        assert "blogmore_version" in context
        assert context["blogmore_version"] == __version__

    def test_site_description_in_global_context(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_description is included in the global context."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_description="A great blog about things",
        )

        context = generator._get_global_context()

        assert context["site_description"] == "A great blog about things"

    def test_site_description_default_is_empty(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_description defaults to an empty string."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        assert generator.site_description == ""

    def test_site_description_in_index_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_description appears in the index page meta tags."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_description="My site description",
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="description" content="My site description">' in content
        assert '<meta property="og:description" content="My site description">' in content

    def test_no_description_meta_in_index_without_site_description(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that no description meta tag appears in index when site_description is empty."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="description"' not in content

    def test_site_description_in_archive_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_description appears in the archive page meta tags."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_description="My site description",
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "archive.html").read_text()
        assert '<meta name="description" content="My site description">' in content

    def test_site_description_in_tags_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_description appears in the tags page meta tags."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_description="My site description",
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "tags.html").read_text()
        assert '<meta name="description" content="My site description">' in content

    def test_site_description_in_categories_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_description appears in the categories page meta tags."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_description="My site description",
        )

        generator.generate(include_drafts=False)

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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_description="Default site description",
        )

        generator.generate(include_drafts=False)

        post_file_out = temp_output_dir / "2024" / "06" / "01" / "image-only.html"
        assert post_file_out.exists()
        content = post_file_out.read_text()
        assert '<meta name="description" content="Default site description">' in content

    def test_site_description_not_used_when_post_has_description(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that a post's own description takes precedence over site_description."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_description="Default site description",
        )

        generator.generate(include_drafts=False)

        # seo-test-post.md has its own description
        post_file = temp_output_dir / "2024" / "03" / "01" / "seo-test-post.html"
        assert post_file.exists()
        content = post_file.read_text()
        # Own description should be used
        assert (
            "This is a test post with SEO and social media meta tags" in content
        )
        # site_description should NOT be used
        assert "Default site description" not in content

    def test_site_keywords_in_index_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_keywords appear in the index page meta tags."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_keywords=["python", "web", "programming"],
        )

        generator.generate(include_drafts=False)

        index_content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="keywords" content="python, web, programming">' in index_content

    def test_site_keywords_in_archive_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_keywords appear in the archive page meta tags."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_keywords=["python", "web"],
        )

        generator.generate(include_drafts=False)

        archive_content = (temp_output_dir / "archive.html").read_text()
        assert '<meta name="keywords" content="python, web">' in archive_content

    def test_site_keywords_in_tag_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_keywords appear in tag pages."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_keywords=["blog", "posts"],
        )

        generator.generate(include_drafts=False)

        tag_content = (temp_output_dir / "tag" / "python.html").read_text()
        assert '<meta name="keywords" content="blog, posts">' in tag_content

    def test_site_keywords_not_shown_when_not_configured(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that no keywords meta tag appears when site_keywords is not set."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        index_content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="keywords"' not in index_content

    def test_post_tags_take_precedence_over_site_keywords(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that a post's own tags are used as keywords, not site_keywords."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_keywords=["site-wide-keyword"],
        )

        generator.generate(include_drafts=False)

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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_keywords=["fallback", "keyword"],
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_keywords=keywords,
        )

        context = generator._get_global_context()
        assert context["site_keywords"] == keywords

    def test_site_keywords_none_in_global_context(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site_keywords is None in global context when not set."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        context = generator._get_global_context()
        assert context["site_keywords"] is None

    def test_index_page_og_type_is_website(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the index page has og:type set to website."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta property="og:type" content="website">' in content

    def test_index_page_og_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the index page has og:url set to the site root URL."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_url="https://example.com",
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta property="og:url" content="https://example.com/">' in content

    def test_index_page_og_site_name(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the index page has og:site_name set to the site title."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_title="My Awesome Blog",
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta property="og:site_name" content="My Awesome Blog">' in content

    def test_index_page_twitter_card_summary_without_image(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that index page has twitter:card set to summary when no image is available."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="twitter:card" content="summary">' in content

    def test_index_page_twitter_card_summary_large_image_with_site_logo(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that index page uses summary_large_image twitter:card when site_logo is set."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            sidebar_config={"site_logo": "/images/logo.png"},
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="twitter:card" content="summary_large_image">' in content

    def test_index_page_twitter_title(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that the index page has twitter:title set to the site title."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_title="My Blog",
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "index.html").read_text()
        assert '<meta name="twitter:title" content="My Blog">' in content

    def test_index_page_twitter_title_with_subtitle(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that twitter:title includes subtitle when site_subtitle is set."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_title="My Blog",
            site_subtitle="Thoughts and ideas",
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            sidebar_config={"site_logo": "https://cdn.example.com/logo.png"},
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_url="https://example.com",
            sidebar_config={"site_logo": "/images/logo.png"},
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_url="https://example.com",
            sidebar_config={"site_logo": "images/logo.png"},
        )

        generator.generate(include_drafts=False)

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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_url="https://example.com",
        )

        generator.generate(include_drafts=False)

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
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_url="https://example.com",
            sidebar_config={"site_logo": "/images/logo.png"},
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        assert (temp_output_dir / "static" / "style.css").exists()
        assert not (temp_output_dir / "static" / "styles.min.css").exists()

    def test_minify_css_generates_min_css(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that minify_css generates styles.min.css and not style.css."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            minify_css=True,
        )

        generator.generate(include_drafts=False)

        assert (temp_output_dir / "static" / "styles.min.css").exists()
        assert not (temp_output_dir / "static" / "style.css").exists()

    def test_minify_css_produces_smaller_file(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that the minified CSS file is smaller than the original."""
        normal_output = tmp_path / "normal"
        minified_output = tmp_path / "minified"

        normal_generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=normal_output,
        )
        normal_generator.generate(include_drafts=False)

        minified_generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=minified_output,
            minify_css=True,
        )
        minified_generator.generate(include_drafts=False)

        normal_size = (normal_output / "static" / "style.css").stat().st_size
        minified_size = (minified_output / "static" / "styles.min.css").stat().st_size
        assert minified_size < normal_size

    def test_minify_css_url_in_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that pages reference styles.min.css when minify_css is enabled."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            minify_css=True,
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "index.html").read_text()
        assert "/static/styles.min.css" in content
        assert "/static/style.css" not in content

    def test_normal_css_url_in_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that pages reference style.css when minify_css is disabled."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "index.html").read_text()
        assert "/static/style.css" in content
        assert "/static/styles.min.css" not in content

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
            content_dir=posts_dir,
            templates_dir=templates_dir,
            output_dir=temp_output_dir,
            minify_css=True,
        )

        generator.generate(include_drafts=False)

        assert (temp_output_dir / "static" / "styles.min.css").exists()
        assert not (temp_output_dir / "static" / "style.css").exists()
        minified_content = (
            temp_output_dir / "static" / "styles.min.css"
        ).read_text(encoding="utf-8")
        assert "body" in minified_content
        assert "color" in minified_content


class TestMinifyJs:
    """Test the minify_js feature."""

    def test_minify_js_false_by_default(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that JavaScript is not minified by default."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        assert (temp_output_dir / "static" / "theme.js").exists()
        assert not (temp_output_dir / "static" / "theme.min.js").exists()

    def test_minify_js_generates_min_js(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that minify_js generates theme.min.js and not theme.js."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            minify_js=True,
        )

        generator.generate(include_drafts=False)

        assert (temp_output_dir / "static" / "theme.min.js").exists()
        assert not (temp_output_dir / "static" / "theme.js").exists()

    def test_minify_js_produces_smaller_file(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test that the minified JS file is smaller than the original."""
        normal_output = tmp_path / "normal"
        minified_output = tmp_path / "minified"

        normal_generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=normal_output,
        )
        normal_generator.generate(include_drafts=False)

        minified_generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=minified_output,
            minify_js=True,
        )
        minified_generator.generate(include_drafts=False)

        normal_size = (normal_output / "static" / "theme.js").stat().st_size
        minified_size = (minified_output / "static" / "theme.min.js").stat().st_size
        assert minified_size < normal_size

    def test_minify_js_url_in_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that pages reference theme.min.js when minify_js is enabled."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            minify_js=True,
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "index.html").read_text()
        assert "/static/theme.min.js" in content
        assert "/static/theme.js" not in content

    def test_normal_js_url_in_html(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that pages reference theme.js when minify_js is disabled."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        content = (temp_output_dir / "index.html").read_text()
        assert "/static/theme.js" in content
        assert "/static/theme.min.js" not in content

    def test_minify_js_search_without_search_enabled(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that search.min.js is not generated when search is disabled."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            minify_js=True,
            with_search=False,
        )

        generator.generate(include_drafts=False)

        assert not (temp_output_dir / "static" / "search.min.js").exists()
        assert not (temp_output_dir / "static" / "search.js").exists()

    def test_minify_js_with_search_generates_min_search_js(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that search.min.js is generated when both minify_js and with_search are enabled."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            minify_js=True,
            with_search=True,
        )

        generator.generate(include_drafts=False)

        assert (temp_output_dir / "static" / "search.min.js").exists()
        assert not (temp_output_dir / "static" / "search.js").exists()

    def test_minify_js_search_url_in_search_page(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that search page references search.min.js when minify_js is enabled."""
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            minify_js=True,
            with_search=True,
        )

        generator.generate(include_drafts=False)

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
            content_dir=posts_dir,
            templates_dir=templates_dir,
            output_dir=temp_output_dir,
            minify_js=True,
        )

        generator.generate(include_drafts=False)

        assert (temp_output_dir / "static" / "theme.min.js").exists()
        assert not (temp_output_dir / "static" / "theme.js").exists()
        minified_content = (
            temp_output_dir / "static" / "theme.min.js"
        ).read_text(encoding="utf-8")
        assert "hello" in minified_content
        assert "world" in minified_content
