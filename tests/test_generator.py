"""Unit tests for the generator module."""

from pathlib import Path

import pytest

from blogmore.generator import SiteGenerator, paginate_posts, sanitize_for_url
from blogmore.parser import Post
from blogmore.utils import normalize_site_url


class TestNormalizeSiteUrl:
    """Test the normalize_site_url function."""

    def test_normalize_no_trailing_slash(self) -> None:
        """Test normalizing URL without trailing slash."""
        assert normalize_site_url("https://example.com") == "https://example.com"

    def test_normalize_with_trailing_slash(self) -> None:
        """Test normalizing URL with trailing slash."""
        assert normalize_site_url("https://example.com/") == "https://example.com"

    def test_normalize_multiple_trailing_slashes(self) -> None:
        """Test normalizing URL with multiple trailing slashes."""
        assert normalize_site_url("https://example.com///") == "https://example.com"

    def test_normalize_empty_string(self) -> None:
        """Test normalizing empty string."""
        assert normalize_site_url("") == ""

    def test_normalize_just_slash(self) -> None:
        """Test normalizing just a slash."""
        assert normalize_site_url("/") == ""


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

    def test_generate_with_drafts(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
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

    def test_generate_with_no_posts(self, temp_output_dir: Path, tmp_path: Path) -> None:
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
