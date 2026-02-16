"""Unit tests for the renderer module."""

import datetime as dt
from pathlib import Path

import pytest

from blogmore.parser import Page, Post
from blogmore.renderer import TemplateRenderer


class TestTemplateRenderer:
    """Test the TemplateRenderer class."""

    def test_init_default(self) -> None:
        """Test initializing renderer with default templates."""
        renderer = TemplateRenderer()
        assert renderer.templates_dir is None
        assert renderer.extra_stylesheets == []

    def test_init_with_custom_templates(self, tmp_path: Path) -> None:
        """Test initializing renderer with custom templates directory."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        renderer = TemplateRenderer(templates_dir=templates_dir)
        assert renderer.templates_dir == templates_dir

    def test_init_with_extra_stylesheets(self) -> None:
        """Test initializing renderer with extra stylesheets."""
        stylesheets = ["https://example.com/style.css"]
        renderer = TemplateRenderer(extra_stylesheets=stylesheets)
        assert renderer.extra_stylesheets == stylesheets

    def test_format_date_with_datetime(self) -> None:
        """Test formatting a datetime object."""
        date = dt.datetime(2024, 1, 15, 14, 30, 0, tzinfo=dt.UTC)
        formatted = TemplateRenderer._format_date(date)
        assert "January 15, 2024" in formatted
        assert "14:30:00" in formatted

    def test_format_date_with_timezone(self) -> None:
        """Test formatting a datetime with timezone."""
        date = dt.datetime(2024, 1, 15, 14, 30, 0, tzinfo=dt.UTC)
        formatted = TemplateRenderer._format_date(date)
        # Should include timezone info
        assert "UTC" in formatted or "00:00" in formatted

    def test_format_date_none(self) -> None:
        """Test formatting None returns empty string."""
        assert TemplateRenderer._format_date(None) == ""

    def test_format_date_custom_format(self) -> None:
        """Test formatting with custom format string."""
        date = dt.datetime(2024, 1, 15, 14, 30, 0, tzinfo=dt.UTC)
        formatted = TemplateRenderer._format_date(date, fmt="%Y-%m-%d")
        assert formatted.startswith("2024-01-15")

    def test_render_post(self, sample_post: Post) -> None:
        """Test rendering a single post."""
        renderer = TemplateRenderer()
        html = renderer.render_post(sample_post, site_title="Test Blog")

        assert sample_post.title in html
        assert sample_post.html_content in html
        assert "Test Blog" in html

    def test_render_post_with_extra_stylesheets(self, sample_post: Post) -> None:
        """Test rendering post with extra stylesheets."""
        renderer = TemplateRenderer(
            extra_stylesheets=["https://example.com/style.css"]
        )
        html = renderer.render_post(sample_post)
        assert "https://example.com/style.css" in html

    def test_render_page(self, sample_page: Page) -> None:
        """Test rendering a static page."""
        renderer = TemplateRenderer()
        html = renderer.render_page(sample_page, site_title="Test Blog")

        assert sample_page.title in html
        assert sample_page.html_content in html
        assert "Test Blog" in html

    def test_render_index(self, sample_post: Post) -> None:
        """Test rendering the index page."""
        renderer = TemplateRenderer()
        html = renderer.render_index(
            posts=[sample_post],
            page=1,
            total_pages=1,
            site_title="Test Blog",
        )

        assert sample_post.title in html
        assert "Test Blog" in html

    def test_render_index_with_pagination(self, sample_post: Post) -> None:
        """Test rendering index with pagination."""
        renderer = TemplateRenderer()
        html = renderer.render_index(
            posts=[sample_post],
            page=2,
            total_pages=5,
            site_title="Test Blog",
        )

        assert sample_post.title in html
        # Should have pagination indicators
        assert "2" in html  # Current page

    def test_render_archive(self, sample_post: Post) -> None:
        """Test rendering the archive page."""
        renderer = TemplateRenderer()
        html = renderer.render_archive(
            posts=[sample_post],
            archive_title="Posts from 2024",
            site_title="Test Blog",
        )

        assert sample_post.title in html
        assert "Posts from 2024" in html

    def test_render_tag_page(self, sample_post: Post) -> None:
        """Test rendering a tag page."""
        renderer = TemplateRenderer()
        html = renderer.render_tag_page(
            tag="python",
            posts=[sample_post],
            site_title="Test Blog",
        )

        assert "python" in html
        assert sample_post.title in html

    def test_render_category_page(self, sample_post: Post) -> None:
        """Test rendering a category page."""
        renderer = TemplateRenderer()
        html = renderer.render_category_page(
            category="python",
            posts=[sample_post],
            site_title="Test Blog",
        )

        assert "python" in html
        assert sample_post.title in html

    def test_render_tags_page(self) -> None:
        """Test rendering the tags overview page."""
        renderer = TemplateRenderer()
        tags = [
            {
                "display_name": "Python",
                "safe_tag": "python",
                "count": 5,
                "font_size": 20,
            },
            {
                "display_name": "JavaScript",
                "safe_tag": "javascript",
                "count": 3,
                "font_size": 16,
            },
        ]
        html = renderer.render_tags_page(tags=tags, site_title="Test Blog")

        assert "Python" in html
        assert "JavaScript" in html

    def test_render_categories_page(self) -> None:
        """Test rendering the categories overview page."""
        renderer = TemplateRenderer()
        categories = [
            {
                "display_name": "Python",
                "safe_category": "python",
                "count": 5,
                "font_size": 20,
            },
            {
                "display_name": "Web Dev",
                "safe_category": "webdev",
                "count": 3,
                "font_size": 16,
            },
        ]
        html = renderer.render_categories_page(
            categories=categories, site_title="Test Blog"
        )

        assert "Python" in html
        assert "Web Dev" in html

    def test_render_template(self) -> None:
        """Test rendering an arbitrary template."""
        renderer = TemplateRenderer()
        # Test with a template we know exists (base.html)
        html = renderer.render_template("base.html", site_title="Test Blog")
        assert html  # Should return some HTML

    def test_date_filter_in_template(self, sample_post: Post) -> None:
        """Test that the format_date filter works in templates."""
        renderer = TemplateRenderer()
        # The filter should be available in templates
        assert "format_date" in renderer.env.filters

        # Render a post and check date formatting
        html = renderer.render_post(sample_post, site_title="Test Blog")
        # Should contain formatted date
        assert "2024" in html

    def test_custom_templates_precedence(self, tmp_path: Path, sample_post: Post) -> None:
        """Test that custom templates take precedence over bundled ones."""
        # Create a custom template directory with a custom post template
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create a simple custom post template
        custom_template = templates_dir / "post.html"
        custom_template.write_text(
            "<html><body>CUSTOM TEMPLATE: {{ post.title }}</body></html>"
        )

        renderer = TemplateRenderer(templates_dir=templates_dir)
        html = renderer.render_post(sample_post, site_title="Test Blog")

        assert "CUSTOM TEMPLATE" in html
        assert sample_post.title in html

    def test_fallback_to_bundled_templates(
        self, tmp_path: Path, sample_post: Post
    ) -> None:
        """Test that missing custom templates fall back to bundled ones."""
        # Create a custom template directory WITHOUT post.html
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        renderer = TemplateRenderer(templates_dir=templates_dir)
        # Should fall back to bundled template without error
        html = renderer.render_post(sample_post, site_title="Test Blog")

        assert sample_post.title in html
