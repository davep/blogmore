"""Unit tests for the parser module."""

import datetime as dt
import re
from pathlib import Path

import pytest

from blogmore.parser import (
    Page,
    Post,
    PostParser,
    extract_first_paragraph,
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


class TestExtractFirstParagraph:
    """Test the extract_first_paragraph function."""

    def test_extract_simple_paragraph(self) -> None:
        """Test extracting a simple paragraph."""
        content = "This is the first paragraph.\n\nThis is the second paragraph."
        assert extract_first_paragraph(content) == "This is the first paragraph."

    def test_extract_multiline_paragraph(self) -> None:
        """Test extracting a paragraph that spans multiple lines."""
        content = (
            "This is the first line.\nThis is the second line.\n\nSecond paragraph."
        )
        assert (
            extract_first_paragraph(content)
            == "This is the first line. This is the second line."
        )

    def test_skip_image_markdown(self) -> None:
        """Test that markdown images are skipped."""
        content = "![Alt text](image.jpg)\n\nThis is the first paragraph."
        assert extract_first_paragraph(content) == "This is the first paragraph."

    def test_skip_image_html(self) -> None:
        """Test that HTML img tags are skipped."""
        content = '<img src="image.jpg">\n\nThis is the first paragraph.'
        assert extract_first_paragraph(content) == "This is the first paragraph."

    def test_skip_heading(self) -> None:
        """Test that headings are skipped."""
        content = "# Main Heading\n\nThis is the first paragraph."
        assert extract_first_paragraph(content) == "This is the first paragraph."

    def test_remove_markdown_formatting(self) -> None:
        """Test that markdown formatting is removed."""
        content = "This is **bold** and *italic* and `code` and [link](url)."
        assert (
            extract_first_paragraph(content)
            == "This is bold and italic and code and link."
        )

    def test_stop_at_heading(self) -> None:
        """Test that extraction stops at a heading after paragraph."""
        content = "First paragraph.\n\n## Second Heading\n\nSecond paragraph."
        assert extract_first_paragraph(content) == "First paragraph."

    def test_empty_content(self) -> None:
        """Test with empty content."""
        assert extract_first_paragraph("") == ""

    def test_only_images(self) -> None:
        """Test with only images."""
        content = "![Image 1](img1.jpg)\n![Image 2](img2.jpg)"
        assert extract_first_paragraph(content) == ""

    def test_paragraph_after_multiple_images(self) -> None:
        """Test extracting paragraph after multiple images."""
        content = "![Image 1](img1.jpg)\n![Image 2](img2.jpg)\n\nFirst paragraph here."
        assert extract_first_paragraph(content) == "First paragraph here."

    def test_code_block_stops_extraction(self) -> None:
        """Test that code blocks stop extraction if we have content."""
        content = "First paragraph.\n\n```python\ncode here\n```"
        assert extract_first_paragraph(content) == "First paragraph."


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

    def test_description_from_metadata(self) -> None:
        """Test that description from metadata is used when present."""
        post = Post(
            path=Path("test.md"),
            title="Test",
            content="This is the first paragraph of content.",
            html_content="<p>This is the first paragraph of content.</p>",
            metadata={"description": "Custom description from frontmatter"},
        )
        assert post.description == "Custom description from frontmatter"

    def test_description_from_content(self) -> None:
        """Test that first paragraph is used when no description in metadata."""
        post = Post(
            path=Path("test.md"),
            title="Test",
            content="This is the first paragraph.\n\nThis is the second paragraph.",
            html_content="<p>Test</p>",
            metadata={},
        )
        assert post.description == "This is the first paragraph."

    def test_description_from_content_no_metadata(self) -> None:
        """Test that first paragraph is used when metadata is None."""
        post = Post(
            path=Path("test.md"),
            title="Test",
            content="First paragraph here.\n\nSecond paragraph.",
            html_content="<p>Test</p>",
            metadata=None,
        )
        assert post.description == "First paragraph here."

    def test_description_skips_images(self) -> None:
        """Test that description extraction skips images."""
        post = Post(
            path=Path("test.md"),
            title="Test",
            content="![Image](img.jpg)\n\nThis is the first paragraph.",
            html_content="<p>Test</p>",
            metadata={},
        )
        assert post.description == "This is the first paragraph."

    def test_reading_time_short_post(self) -> None:
        """Test reading time calculation for a short post."""
        post = Post(
            path=Path("test.md"),
            title="Test",
            content="Hello world, this is a short post.",
            html_content="<p>Hello world, this is a short post.</p>",
        )
        assert post.reading_time == 1

    def test_reading_time_medium_post(self) -> None:
        """Test reading time calculation for a medium post."""
        # 400 words at 200 WPM = 2 minutes
        content = " ".join(["word"] * 400)
        post = Post(
            path=Path("test.md"),
            title="Test",
            content=content,
            html_content=f"<p>{content}</p>",
        )
        assert post.reading_time == 2

    def test_reading_time_with_markdown(self) -> None:
        """Test reading time calculation with markdown content."""
        content = """
        # Heading
        
        This is a **bold** paragraph with *italic* text and `code`.
        
        Here is a [link](https://example.com) and some more text.
        
        ```python
        def hello():
            print("This code should not be counted")
        ```
        
        And some final thoughts.
        """
        post = Post(
            path=Path("test.md"),
            title="Test",
            content=content,
            html_content="<p>Test</p>",
        )
        # Reading time should be calculated from the actual text content
        assert post.reading_time >= 1

    def test_modified_date_none_when_no_metadata(self) -> None:
        """Test that modified_date returns None when metadata is None."""
        post = Post(
            path=Path("test.md"),
            title="Test",
            content="Content",
            html_content="<p>Content</p>",
            metadata=None,
        )
        assert post.modified_date is None

    def test_modified_date_none_when_not_in_metadata(self) -> None:
        """Test that modified_date returns None when modified key absent."""
        post = Post(
            path=Path("test.md"),
            title="Test",
            content="Content",
            html_content="<p>Content</p>",
            metadata={},
        )
        assert post.modified_date is None

    def test_modified_date_from_datetime_object(self) -> None:
        """Test that modified_date returns datetime objects from metadata as-is."""
        modified = dt.datetime(2026, 2, 21, 16, 29, 0, tzinfo=dt.UTC)
        post = Post(
            path=Path("test.md"),
            title="Test",
            content="Content",
            html_content="<p>Content</p>",
            metadata={"modified": modified},
        )
        assert post.modified_date == modified

    def test_modified_date_from_string_with_space_separator(self) -> None:
        """Test that modified_date parses a string with space separator correctly."""
        post = Post(
            path=Path("test.md"),
            title="Test",
            content="Content",
            html_content="<p>Content</p>",
            metadata={"modified": "2026-02-21 16:29:00 +0000"},
        )
        result = post.modified_date
        assert result is not None
        assert result.isoformat() == "2026-02-21T16:29:00+00:00"

    def test_modified_date_from_iso_string(self) -> None:
        """Test that modified_date parses a proper ISO 8601 string correctly."""
        post = Post(
            path=Path("test.md"),
            title="Test",
            content="Content",
            html_content="<p>Content</p>",
            metadata={"modified": "2026-02-21T16:29:00+00:00"},
        )
        result = post.modified_date
        assert result is not None
        assert result.isoformat() == "2026-02-21T16:29:00+00:00"

    def test_modified_date_isoformat_is_iso8601(self) -> None:
        """Test that modified_date.isoformat() produces a valid ISO 8601 string."""
        post = Post(
            path=Path("test.md"),
            title="Test",
            content="Content",
            html_content="<p>Content</p>",
            metadata={"modified": "2026-02-21 16:29:00 +0000"},
        )
        result = post.modified_date
        assert result is not None
        iso_string = result.isoformat()
        # ISO 8601 requires T as separator between date and time
        assert "T" in iso_string


class TestPage:
    """Test the Page dataclass."""

    def test_page_slug(self, sample_page: Page) -> None:
        """Test that slug is generated from filename."""
        assert sample_page.slug == "about"

    def test_page_url(self, sample_page: Page) -> None:
        """Test URL generation for page."""
        assert sample_page.url == "/about.html"

    def test_description_from_metadata(self) -> None:
        """Test that description from metadata is used when present."""
        page = Page(
            path=Path("test.md"),
            title="Test",
            content="This is the first paragraph of content.",
            html_content="<p>This is the first paragraph of content.</p>",
            metadata={"description": "Custom description from frontmatter"},
        )
        assert page.description == "Custom description from frontmatter"

    def test_description_from_content(self) -> None:
        """Test that first paragraph is used when no description in metadata."""
        page = Page(
            path=Path("test.md"),
            title="Test",
            content="This is the first paragraph.\n\nThis is the second paragraph.",
            html_content="<p>Test</p>",
            metadata={},
        )
        assert page.description == "This is the first paragraph."


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

        # Should have 7 posts (excluding draft), including nested subdirectory post
        assert len(posts) == 7
        # Posts should be sorted by date (newest first)
        assert posts[0].title == "Nested Post"  # 2025-01-05 (in subdirectory)
        assert posts[1].title == "Test Post with Relative Cover No Slash"  # 2024-04-02
        assert posts[2].title == "Test Post with Relative Cover"  # 2024-04-01
        assert posts[3].title == "SEO Test Post"  # 2024-03-01
        assert posts[4].title == "My First Post"  # 2024-01-15
        assert posts[5].title == "Complex Post with Many Features"  # 2024-01-10
        # Post without date should be last
        assert posts[6].title == "Post Without Date"

    def test_parse_directory_include_drafts(self, posts_dir: Path) -> None:
        """Test parsing directory including drafts."""
        parser = PostParser()
        posts = parser.parse_directory(posts_dir, include_drafts=True)

        # Should have 8 posts (including draft and nested subdirectory post)
        assert len(posts) == 8

    def test_parse_directory_finds_posts_in_subdirectories(
        self, posts_dir: Path
    ) -> None:
        """Test that posts in subdirectories are discovered recursively."""
        parser = PostParser()
        posts = parser.parse_directory(posts_dir, include_drafts=False)

        titles = [post.title for post in posts]
        assert "Nested Post" in titles

    def test_parse_directory_not_found(self) -> None:
        """Test parsing non-existent directory raises FileNotFoundError."""
        parser = PostParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_directory(Path("nonexistent"))

    def test_parse_directory_excludes_subdirectory(self, tmp_path: Path) -> None:
        """Test that files in excluded subdirectories are not returned."""
        parser = PostParser()

        # Create a post in the root content directory
        post_file = tmp_path / "my-post.md"
        post_file.write_text(
            "---\ntitle: Regular Post\ndate: 2024-01-01\n---\nContent"
        )

        # Create a page in the pages subdirectory (should be excluded)
        pages_subdir = tmp_path / "pages"
        pages_subdir.mkdir()
        page_file = pages_subdir / "about.md"
        page_file.write_text(
            "---\ntitle: About Page\ndate: 2024-01-02\n---\nPage content"
        )

        posts_without_exclusion = parser.parse_directory(tmp_path)
        assert len(posts_without_exclusion) == 2

        posts_with_exclusion = parser.parse_directory(
            tmp_path, exclude_dirs=[pages_subdir]
        )
        assert len(posts_with_exclusion) == 1
        assert posts_with_exclusion[0].title == "Regular Post"

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

    def test_external_links_open_in_new_tab(self, tmp_path: Path) -> None:
        """Test that external links get target='_blank' attribute."""
        parser = PostParser(site_url="https://example.com")
        post_file = tmp_path / "test-links.md"
        post_file.write_text("""---
title: Test Links
---

This post has [an external link](https://external.com) and 
[an internal link](/posts/my-post) and 
[an anchor link](#section).
""")
        post = parser.parse_file(post_file)

        # External link should have target="_blank"
        assert 'href="https://external.com"' in post.html_content
        assert 'target="_blank"' in post.html_content
        assert 'rel="noopener noreferrer"' in post.html_content

        # Internal links should not have target="_blank"
        assert 'href="/posts/my-post"' in post.html_content
        assert post.html_content.count('target="_blank"') == 1  # Only external link

    def test_footnote_ids_unique_across_multiple_posts(self, tmp_path: Path) -> None:
        """Test that footnote IDs are unique when multiple posts are parsed.

        When multiple posts with footnotes appear on the same index page,
        footnote IDs must not clash to avoid duplicate IDs in the DOM.
        """
        parser = PostParser()

        post_file_1 = tmp_path / "post-one.md"
        post_file_1.write_text(
            "---\ntitle: Post One\n---\n\nText with footnote[^1].\n\n[^1]: Footnote one.\n"
        )
        post_file_2 = tmp_path / "post-two.md"
        post_file_2.write_text(
            "---\ntitle: Post Two\n---\n\nText with footnote[^1].\n\n[^1]: Footnote two.\n"
        )

        post1 = parser.parse_file(post_file_1)
        post2 = parser.parse_file(post_file_2)

        # Both posts must contain footnote markup
        assert "footnote" in post1.html_content.lower()
        assert "footnote" in post2.html_content.lower()

        # Extract all id attributes from both posts combined HTML
        ids = re.findall(r'\bid="([^"]+)"', post1.html_content + post2.html_content)

        # Every id must be unique - no duplicates across both posts
        assert len(ids) == len(set(ids)), (
            f"Duplicate footnote IDs found across posts: "
            f"{[i for i in ids if ids.count(i) > 1]}"
        )

    def test_external_links_without_site_url(self, tmp_path: Path) -> None:
        """Test that external links work even without site_url configured."""
        parser = PostParser()  # No site_url
        post_file = tmp_path / "test-links.md"
        post_file.write_text("""---
title: Test Links
---

This post has [an external link](https://external.com) and 
[a relative link](/posts/my-post).
""")
        post = parser.parse_file(post_file)

        # External link should have target="_blank"
        assert 'href="https://external.com"' in post.html_content
        assert 'target="_blank"' in post.html_content

        # Relative link should not have target="_blank"
        assert 'href="/posts/my-post"' in post.html_content
        # Only the external link should have target="_blank"
        assert post.html_content.count('target="_blank"') == 1
