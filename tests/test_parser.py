"""Unit tests for the parser module."""

import datetime as dt
from pathlib import Path

import pytest

from blogmore.parser import (
    Page,
    Post,
    PostParser,
    remove_date_prefix,
    sanitize_for_url,
)


class TestSanitizeForUrl:
    """Test the sanitize_for_url function."""

    def test_sanitize_simple_string(self) -> None:
        """Test sanitizing a simple string."""
        assert sanitize_for_url("Hello World") == "hello-world"

    def test_sanitize_with_special_chars(self) -> None:
        """Test sanitizing a string with special characters."""
        assert sanitize_for_url("Hello@World!") == "hello-world"

    def test_sanitize_with_multiple_spaces(self) -> None:
        """Test sanitizing a string with multiple spaces."""
        assert sanitize_for_url("Hello   World") == "hello-world"

    def test_sanitize_with_dashes(self) -> None:
        """Test sanitizing a string with dashes."""
        assert sanitize_for_url("Hello--World") == "hello-world"

    def test_sanitize_with_underscores(self) -> None:
        """Test that underscores are preserved."""
        assert sanitize_for_url("Hello_World") == "hello_world"

    def test_sanitize_empty_string(self) -> None:
        """Test sanitizing an empty string returns 'unnamed'."""
        assert sanitize_for_url("") == "unnamed"

    def test_sanitize_only_special_chars(self) -> None:
        """Test sanitizing a string with only special characters."""
        assert sanitize_for_url("@#$%") == "unnamed"

    def test_sanitize_leading_trailing_dashes(self) -> None:
        """Test that leading and trailing dashes are removed."""
        assert sanitize_for_url("--hello-world--") == "hello-world"


class TestRemoveDatePrefix:
    """Test the remove_date_prefix function."""

    def test_remove_date_prefix(self) -> None:
        """Test removing a date prefix from a slug."""
        assert remove_date_prefix("2024-01-15-my-post") == "my-post"

    def test_remove_date_prefix_no_date(self) -> None:
        """Test that strings without date prefix are unchanged."""
        assert remove_date_prefix("my-post") == "my-post"

    def test_remove_date_prefix_partial_date(self) -> None:
        """Test that partial dates don't match."""
        assert remove_date_prefix("2024-01-my-post") == "2024-01-my-post"


class TestPost:
    """Test the Post dataclass."""

    def test_post_slug(self, sample_post: Post) -> None:
        """Test that slug is generated from filename."""
        assert sample_post.slug == "test-post"

    def test_post_url_with_date(self, sample_post: Post) -> None:
        """Test URL generation for post with date."""
        assert sample_post.url == "/2024/01/15/test-post.html"

    def test_post_url_without_date(self, sample_post_without_date: Post) -> None:
        """Test URL generation for post without date."""
        assert sample_post_without_date.url == "/no-date-post.html"

    def test_post_url_removes_date_prefix(self) -> None:
        """Test that date prefix is removed from slug in URL."""
        post = Post(
            path=Path("2024-01-15-my-post.md"),
            title="My Post",
            content="Content",
            html_content="<p>Content</p>",
            date=dt.datetime(2024, 1, 15, tzinfo=dt.UTC),
        )
        assert post.url == "/2024/01/15/my-post.html"

    def test_safe_category(self, sample_post: Post) -> None:
        """Test safe_category property."""
        assert sample_post.safe_category == "python"

    def test_safe_category_none(self, sample_post_without_date: Post) -> None:
        """Test safe_category when category has special characters."""
        post_with_special = Post(
            path=Path("test.md"),
            title="Test",
            content="Test",
            html_content="<p>Test</p>",
            category="Web Dev & More",
        )
        assert post_with_special.safe_category == "web-dev-more"

    def test_safe_tags(self, sample_post: Post) -> None:
        """Test safe_tags method."""
        assert sample_post.safe_tags() == ["python", "testing"]

    def test_safe_tags_empty(self) -> None:
        """Test safe_tags with no tags."""
        post = Post(
            path=Path("test.md"),
            title="Test",
            content="Test",
            html_content="<p>Test</p>",
            tags=None,
        )
        assert post.safe_tags() == []

    def test_safe_tags_with_special_chars(self) -> None:
        """Test safe_tags with special characters."""
        post = Post(
            path=Path("test.md"),
            title="Test",
            content="Test",
            html_content="<p>Test</p>",
            tags=["C++", "Web Dev"],
        )
        assert post.safe_tags() == ["c", "web-dev"]


class TestPage:
    """Test the Page dataclass."""

    def test_page_slug(self, sample_page: Page) -> None:
        """Test that slug is generated from filename."""
        assert sample_page.slug == "about"

    def test_page_url(self, sample_page: Page) -> None:
        """Test URL generation for page."""
        assert sample_page.url == "/about.html"


class TestPostParser:
    """Test the PostParser class."""

    def test_parse_file_simple_post(self, posts_dir: Path) -> None:
        """Test parsing a simple post file."""
        parser = PostParser()
        post = parser.parse_file(posts_dir / "2024-01-15-first-post.md")

        assert post.title == "My First Post"
        # Date is parsed as naive datetime when no time/timezone is specified
        assert post.date == dt.datetime(2024, 1, 15, 0, 0)
        assert post.category == "python"
        assert post.tags == ["python", "blog", "testing"]
        assert post.draft is False
        assert "This is my first blog post!" in post.content
        assert "<p>This is my first blog post!</p>" in post.html_content

    def test_parse_file_draft_post(self, posts_dir: Path) -> None:
        """Test parsing a draft post."""
        parser = PostParser()
        post = parser.parse_file(posts_dir / "2024-01-20-draft-post.md")

        assert post.title == "Draft Post"
        assert post.draft is True

    def test_parse_file_no_date(self, posts_dir: Path) -> None:
        """Test parsing a post without a date."""
        parser = PostParser()
        post = parser.parse_file(posts_dir / "2024-02-01-no-date-post.md")

        assert post.title == "Post Without Date"
        assert post.date is None

    def test_parse_file_complex_markdown(self, posts_dir: Path) -> None:
        """Test parsing a post with complex Markdown features."""
        parser = PostParser()
        post = parser.parse_file(posts_dir / "2024-01-10-complex-post.md")

        assert post.title == "Complex Post with Many Features"
        # Check that code blocks are rendered
        assert "highlight" in post.html_content
        # Check that tables are rendered
        assert "<table>" in post.html_content
        # Check that footnotes are rendered
        assert "footnote" in post.html_content.lower()

    def test_parse_file_not_found(self) -> None:
        """Test parsing a non-existent file raises FileNotFoundError."""
        parser = PostParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_file(Path("nonexistent.md"))

    def test_parse_file_missing_title(self, tmp_path: Path) -> None:
        """Test that parsing a file without title raises ValueError."""
        parser = PostParser()
        post_file = tmp_path / "no-title.md"
        post_file.write_text("---\ndate: 2024-01-01\n---\nContent")

        with pytest.raises(ValueError, match="missing required 'title'"):
            parser.parse_file(post_file)

    def test_parse_file_malformed_yaml(self, tmp_path: Path) -> None:
        """Test that malformed YAML raises ValueError with helpful message."""
        parser = PostParser()
        post_file = tmp_path / "bad-yaml.md"
        post_file.write_text("---\ntitle: My post: the sequel\n---\nContent")

        with pytest.raises(ValueError, match="YAML syntax error"):
            parser.parse_file(post_file)

    def test_parse_directory(self, posts_dir: Path) -> None:
        """Test parsing a directory of posts."""
        parser = PostParser()
        posts = parser.parse_directory(posts_dir, include_drafts=False)

        # Should have 4 posts (excluding draft)
        assert len(posts) == 4
        # Posts should be sorted by date (newest first)
        assert posts[0].title == "SEO Test Post"  # 2024-03-01
        assert posts[1].title == "My First Post"  # 2024-01-15
        assert posts[2].title == "Complex Post with Many Features"  # 2024-01-10
        # Post without date should be last
        assert posts[3].title == "Post Without Date"

    def test_parse_directory_include_drafts(self, posts_dir: Path) -> None:
        """Test parsing directory including drafts."""
        parser = PostParser()
        posts = parser.parse_directory(posts_dir, include_drafts=True)

        # Should have 5 posts (including draft)
        assert len(posts) == 5

    def test_parse_directory_not_found(self) -> None:
        """Test parsing non-existent directory raises FileNotFoundError."""
        parser = PostParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_directory(Path("nonexistent"))

    def test_parse_page(self, pages_dir: Path) -> None:
        """Test parsing a static page."""
        parser = PostParser()
        page = parser.parse_page(pages_dir / "about.md")

        assert page.title == "About Me"
        assert "This is a static page" in page.content
        assert "<p>This is a static page" in page.html_content

    def test_parse_page_not_found(self) -> None:
        """Test parsing non-existent page raises FileNotFoundError."""
        parser = PostParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_page(Path("nonexistent.md"))

    def test_parse_page_missing_title(self, tmp_path: Path) -> None:
        """Test that parsing page without title raises ValueError."""
        parser = PostParser()
        page_file = tmp_path / "no-title.md"
        page_file.write_text("---\n---\nContent")

        with pytest.raises(ValueError, match="missing required 'title'"):
            parser.parse_page(page_file)

    def test_parse_pages_directory(self, pages_dir: Path) -> None:
        """Test parsing a directory of pages."""
        parser = PostParser()
        pages = parser.parse_pages_directory(pages_dir)

        assert len(pages) == 2
        # Pages should be sorted alphabetically
        assert pages[0].title == "About Me"
        assert pages[1].title == "SEO Test Page"

    def test_parse_pages_directory_not_found(self) -> None:
        """Test parsing non-existent pages directory returns empty list."""
        parser = PostParser()
        pages = parser.parse_pages_directory(Path("nonexistent"))
        assert pages == []

    def test_parse_date_formats(self, tmp_path: Path) -> None:
        """Test parsing various date formats."""
        parser = PostParser()

        # Test ISO format with time
        post_file = tmp_path / "date-test.md"
        post_file.write_text(
            "---\ntitle: Test\ndate: 2024-01-15T14:30:00\n---\nContent"
        )
        post = parser.parse_file(post_file)
        assert post.date is not None
        assert post.date.year == 2024
        assert post.date.month == 1
        assert post.date.day == 15

    def test_parse_tags_string(self, tmp_path: Path) -> None:
        """Test parsing tags as comma-separated string."""
        parser = PostParser()
        post_file = tmp_path / "tags-test.md"
        post_file.write_text(
            '---\ntitle: Test\ntags: "python, webdev, testing"\n---\nContent'
        )
        post = parser.parse_file(post_file)
        assert post.tags == ["python", "webdev", "testing"]

    def test_parse_tags_list(self, tmp_path: Path) -> None:
        """Test parsing tags as YAML list."""
        parser = PostParser()
        post_file = tmp_path / "tags-test.md"
        post_file.write_text(
            "---\ntitle: Test\ntags: [python, webdev, testing]\n---\nContent"
        )
        post = parser.parse_file(post_file)
        assert post.tags == ["python", "webdev", "testing"]

    def test_markdown_reset_between_parses(self, posts_dir: Path) -> None:
        """Test that markdown parser is reset between parses."""
        parser = PostParser()
        post1 = parser.parse_file(posts_dir / "2024-01-15-first-post.md")
        post2 = parser.parse_file(posts_dir / "2024-01-10-complex-post.md")

        # Both should have valid HTML content
        assert "<p>" in post1.html_content
        assert "<p>" in post2.html_content
        # And they should be different
        assert post1.html_content != post2.html_content
