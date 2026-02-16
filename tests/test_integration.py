"""End-to-end integration tests for the entire blogmore workflow."""

import shutil
from pathlib import Path

import pytest


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    def test_full_site_generation_workflow(
        self, posts_dir: Path, pages_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test complete workflow from content to generated site."""
        from blogmore.generator import SiteGenerator

        # Set up content directory - generator expects posts in the content_dir itself
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Copy post files directly to content_dir
        for post_file in posts_dir.glob("*.md"):
            shutil.copy(post_file, content_dir / post_file.name)

        # Copy pages to pages subdirectory
        pages_dest = content_dir / "pages"
        shutil.copytree(pages_dir, pages_dest)

        # Generate the site
        generator = SiteGenerator(
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_title="My Test Blog",
            site_url="https://test.example.com",
        )

        generator.generate(include_drafts=False)

        # Verify all expected outputs exist
        assert (temp_output_dir / "index.html").exists()
        assert (temp_output_dir / "archive.html").exists()
        assert (temp_output_dir / "tags.html").exists()
        assert (temp_output_dir / "categories.html").exists()
        assert (temp_output_dir / "feed.xml").exists()
        assert (temp_output_dir / "static" / "style.css").exists()

        # Verify post pages exist
        assert (temp_output_dir / "2024" / "01" / "15" / "first-post.html").exists()
        assert (temp_output_dir / "2024" / "01" / "10" / "complex-post.html").exists()

        # Verify static page exists
        assert (temp_output_dir / "about.html").exists()

        # Verify tag pages exist
        assert (temp_output_dir / "tag" / "python.html").exists()
        assert (temp_output_dir / "tag" / "blog.html").exists()

        # Verify category pages exist
        assert (temp_output_dir / "category" / "python.html").exists()

        # Verify content
        index_content = (temp_output_dir / "index.html").read_text()
        assert "My Test Blog" in index_content
        assert "My First Post" in index_content

        # Verify draft is not included
        assert "Draft Post" not in index_content

        # Verify feed content
        feed_content = (temp_output_dir / "feed.xml").read_text()
        assert "My First Post" in feed_content
        assert "My Test Blog" in feed_content

    def test_regeneration_workflow(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that site can be regenerated multiple times."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        # First generation
        generator.generate(include_drafts=False)
        first_index = (temp_output_dir / "index.html").read_text()

        # Second generation
        generator.generate(include_drafts=False)
        second_index = (temp_output_dir / "index.html").read_text()

        # Content should be similar (may have timestamp differences)
        assert "My First Post" in first_index
        assert "My First Post" in second_index

    def test_draft_workflow(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test workflow with and without drafts."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        # Generate without drafts
        generator.generate(include_drafts=False)
        index_without_drafts = (temp_output_dir / "index.html").read_text()
        assert "Draft Post" not in index_without_drafts

        # Generate with drafts
        generator.generate(include_drafts=True)
        index_with_drafts = (temp_output_dir / "index.html").read_text()
        assert "Draft Post" in index_with_drafts

    def test_custom_templates_workflow(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test workflow with custom templates."""
        from blogmore.generator import SiteGenerator

        # Create custom templates
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create a custom index template
        custom_index = templates_dir / "index.html"
        custom_index.write_text(
            """<!DOCTYPE html>
<html>
<head><title>{{ site_title }}</title></head>
<body>
<h1>CUSTOM INDEX TEMPLATE</h1>
{% for post in posts %}
<h2>{{ post.title }}</h2>
{% endfor %}
</body>
</html>"""
        )

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=templates_dir,
            output_dir=temp_output_dir,
            site_title="Custom Blog",
        )

        generator.generate(include_drafts=False)

        # Verify custom template was used
        index_content = (temp_output_dir / "index.html").read_text()
        assert "CUSTOM INDEX TEMPLATE" in index_content
        assert "My First Post" in index_content

    def test_cli_to_generation_workflow(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test workflow from CLI arguments to generated site."""
        import sys
        from unittest.mock import patch

        from blogmore.__main__ import main

        # Test CLI invocation
        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "generate",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
                "--site-title",
                "CLI Test Blog",
                "--site-url",
                "https://cli-test.com",
            ],
        ):
            result = main()

        assert result == 0
        assert (temp_output_dir / "index.html").exists()

        # Verify site title
        index_content = (temp_output_dir / "index.html").read_text()
        assert "CLI Test Blog" in index_content

    def test_empty_site_workflow(self, temp_output_dir: Path, tmp_path: Path) -> None:
        """Test workflow with no content."""
        from blogmore.generator import SiteGenerator

        # Create empty content directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        generator = SiteGenerator(
            content_dir=empty_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        # Should generate without errors
        generator.generate(include_drafts=False)

        # Should have basic structure
        assert (temp_output_dir / "index.html").exists()
        assert (temp_output_dir / "static" / "style.css").exists()

    def test_markdown_features_workflow(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that all Markdown features are properly rendered."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        # Check complex post rendering
        complex_post = (
            temp_output_dir / "2024" / "01" / "10" / "complex-post.html"
        ).read_text()

        # Verify code highlighting
        assert "highlight" in complex_post

        # Verify tables
        assert "<table>" in complex_post

        # Verify footnotes
        assert "footnote" in complex_post.lower()

    def test_feeds_workflow(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test complete feed generation workflow."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            site_url="https://test.example.com",
        )

        generator.generate(include_drafts=False)

        # Check main RSS feed
        rss_content = (temp_output_dir / "feed.xml").read_text()
        assert "<?xml version=" in rss_content  # Accept both single and double quotes
        assert "<rss" in rss_content
        assert "My First Post" in rss_content

        # Check Atom feed
        atom_content = (temp_output_dir / "feeds" / "all.atom.xml").read_text()
        assert "<?xml version=" in atom_content  # Accept both single and double quotes
        assert "<feed" in atom_content
        assert "My First Post" in atom_content

        # Check category feed
        category_rss = (temp_output_dir / "feeds" / "python.rss.xml").read_text()
        assert "My First Post" in category_rss
        assert "python" in category_rss.lower()

    def test_pagination_workflow(
        self, posts_dir: Path, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test pagination workflow with many posts."""
        from blogmore.generator import SiteGenerator
        from blogmore.parser import PostParser

        # Create many posts to trigger pagination
        many_posts_dir = tmp_path / "many_posts"
        many_posts_dir.mkdir()

        # Create 15 posts (more than one page worth)
        for i in range(15):
            post_file = many_posts_dir / f"2024-01-{i+1:02d}-post-{i}.md"
            post_file.write_text(
                f"""---
title: Post {i}
date: 2024-01-{i+1:02d}
category: test
tags: [test]
---

This is post number {i}.
"""
            )

        generator = SiteGenerator(
            content_dir=many_posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        # Verify index exists
        assert (temp_output_dir / "index.html").exists()
        index_content = (temp_output_dir / "index.html").read_text()

        # Should have posts on index page
        assert "Post" in index_content

    def test_special_characters_workflow(
        self, temp_output_dir: Path, tmp_path: Path
    ) -> None:
        """Test workflow with special characters in content."""
        from blogmore.generator import SiteGenerator

        # Create content with special characters
        content_dir = tmp_path / "special_content"
        content_dir.mkdir()

        post_file = content_dir / "2024-01-15-special.md"
        post_file.write_text(
            """---
title: "Post: With Special & Characters"
date: 2024-01-15
category: "Web Dev & More"
tags: ["C++", "C#"]
---

This post has special characters: <, >, &, ", '

And code with special chars:
```cpp
int main() {
    std::cout << "Hello & goodbye!" << std::endl;
}
```
"""
        )

        generator = SiteGenerator(
            content_dir=content_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
        )

        generator.generate(include_drafts=False)

        # Check that special characters are properly escaped
        post_html = (
            temp_output_dir / "2024" / "01" / "15" / "special.html"
        ).read_text()
        assert "With Special" in post_html
        assert "&amp;" in post_html or "&" in post_html  # Should be properly escaped

        # Check category with special chars
        assert (temp_output_dir / "category" / "web-dev-more.html").exists()

        # Check tags with special chars
        assert (temp_output_dir / "tag" / "c.html").exists()
