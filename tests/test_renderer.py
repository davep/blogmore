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
        assert "2024" in formatted
        assert "01" in formatted
        assert "15" in formatted
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

    def test_format_date_links(self) -> None:
        """Test that format_date produces archive links for year, month and day."""
        date = dt.datetime(2026, 2, 20, 15, 46, 0, tzinfo=dt.UTC)
        formatted = TemplateRenderer._format_date(date)
        assert '<a href="/2026/">2026</a>' in formatted
        assert '<a href="/2026/02/">02</a>' in formatted
        assert '<a href="/2026/02/20/">20</a>' in formatted
        assert "15:46:00" in formatted
        assert "UTC" in formatted

    def test_render_post(self, sample_post: Post) -> None:
        """Test rendering a single post."""
        renderer = TemplateRenderer()
        html = renderer.render_post(sample_post, site_title="Test Blog")

        assert sample_post.title in html
        assert sample_post.html_content in html
        assert "Test Blog" in html

    def test_render_post_with_extra_stylesheets(self, sample_post: Post) -> None:
        """Test rendering post with extra stylesheets."""
        renderer = TemplateRenderer(extra_stylesheets=["https://example.com/style.css"])
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

    def test_render_index_default_feed_links(self, sample_post: Post) -> None:
        """Test that index page has default RSS and Atom links."""
        renderer = TemplateRenderer()
        html = renderer.render_index(
            posts=[sample_post],
            page=1,
            total_pages=1,
            site_title="Test Blog",
            site_url="https://example.com",
        )

        # Check navigation links point to default feeds
        assert 'href="/feed.xml"' in html
        assert 'href="/feeds/all.atom.xml"' in html
        # Check <link> tags in <head> also point to default feeds
        assert 'href="https://example.com/feed.xml"' in html
        assert 'href="https://example.com/feeds/all.atom.xml"' in html

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

    def test_render_category_page_feed_links(self, sample_post: Post) -> None:
        """Test that category pages have category-specific RSS and Atom links."""
        renderer = TemplateRenderer()
        html = renderer.render_category_page(
            category="Python",
            posts=[sample_post],
            site_title="Test Blog",
            site_url="https://example.com",
            safe_category="python",
        )

        # Check navigation links point to category feeds
        assert 'href="/feeds/python.rss.xml"' in html
        assert 'href="/feeds/python.atom.xml"' in html
        # Check <link> tags in <head> also point to category feeds
        assert 'href="https://example.com/feeds/python.rss.xml"' in html
        assert 'href="https://example.com/feeds/python.atom.xml"' in html
        # Make sure default feed links are NOT present
        assert 'href="/feed.xml"' not in html
        assert 'href="/feeds/all.atom.xml"' not in html

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

    def test_custom_templates_precedence(
        self, tmp_path: Path, sample_post: Post
    ) -> None:
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

    def test_render_post_seo_meta_tags(self) -> None:
        """Test that SEO meta tags are rendered correctly for posts."""
        renderer = TemplateRenderer()
        post = Post(
            path=Path("test.md"),
            title="SEO Test Post",
            content="Test content",
            html_content="<p>Test content</p>",
            date=dt.datetime(2024, 3, 1, 10, 0, 0, tzinfo=dt.UTC),
            category="testing",
            tags=["seo", "meta-tags"],
            metadata={
                "author": "John Doe",
                "description": "A test post for SEO",
                "cover": "https://example.com/cover.jpg",
                "modified": "2024-03-02T15:30:00+00:00",
                "twitter_creator": "@johndoe",
                "twitter_site": "@myblog",
            },
        )

        html = renderer.render_post(
            post, site_title="Test Blog", site_url="https://example.com"
        )

        # Check standard SEO meta tags
        assert '<meta name="author" content="John Doe">' in html
        assert '<meta name="description" content="A test post for SEO">' in html
        assert '<meta name="keywords" content="seo, meta-tags">' in html

        # Check Open Graph meta tags
        assert '<meta property="og:title" content="SEO Test Post">' in html
        assert '<meta property="og:type" content="article">' in html
        assert (
            '<meta property="og:url" content="https://example.com/2024/03/01/test.html">'
            in html
        )
        assert '<meta property="og:description" content="A test post for SEO">' in html
        assert '<meta property="og:site_name" content="Test Blog">' in html
        assert (
            '<meta property="og:image" content="https://example.com/cover.jpg">' in html
        )

        # Check article-specific Open Graph tags
        assert '<meta property="article:published_time"' in html
        assert (
            '<meta property="article:modified_time" content="2024-03-02T15:30:00+00:00">'
            in html
        )
        assert '<meta property="article:author" content="John Doe">' in html
        assert '<meta property="article:section" content="testing">' in html
        assert '<meta property="article:tag" content="seo">' in html
        assert '<meta property="article:tag" content="meta-tags">' in html

        # Check Twitter Card meta tags
        assert '<meta name="twitter:card" content="summary_large_image">' in html
        assert '<meta name="twitter:title" content="SEO Test Post">' in html
        assert '<meta name="twitter:description" content="A test post for SEO">' in html
        assert (
            '<meta name="twitter:image" content="https://example.com/cover.jpg">'
            in html
        )
        assert '<meta name="twitter:creator" content="@johndoe">' in html
        assert '<meta name="twitter:site" content="@myblog">' in html

    def test_render_post_modified_time_is_iso8601(self) -> None:
        """Test that article:modified_time is ISO 8601 even for non-ISO frontmatter."""
        renderer = TemplateRenderer()
        post = Post(
            path=Path("test.md"),
            title="Test Post",
            content="Test content",
            html_content="<p>Test content</p>",
            date=dt.datetime(2026, 2, 20, 15, 46, 0, tzinfo=dt.UTC),
            metadata={"modified": "2026-02-21 16:29:00 +0000"},
        )

        html = renderer.render_post(
            post, site_title="Test Blog", site_url="https://example.com"
        )

        assert (
            '<meta property="article:modified_time" content="2026-02-21T16:29:00+00:00">'
            in html
        )

    def test_render_post_minimal_meta_tags(self) -> None:
        """Test that posts without optional metadata still render correctly."""
        renderer = TemplateRenderer()
        post = Post(
            path=Path("minimal.md"),
            title="Minimal Post",
            content="Test content",
            html_content="<p>Test content</p>",
            date=dt.datetime(2024, 3, 1, 10, 0, 0, tzinfo=dt.UTC),
            metadata={},
        )

        html = renderer.render_post(
            post, site_title="Test Blog", site_url="https://example.com"
        )

        # Should still have basic Open Graph tags
        assert '<meta property="og:title" content="Minimal Post">' in html
        assert '<meta property="og:type" content="article">' in html

        # Description should be auto-generated from content
        assert '<meta name="description" content="Test content">' in html
        assert '<meta property="og:description" content="Test content">' in html
        assert '<meta name="twitter:description" content="Test content">' in html

        # Should not have optional tags
        assert '<meta name="author"' not in html
        assert '<meta property="og:image"' not in html

    def test_render_post_auto_description_from_content(self) -> None:
        """Test that description is auto-generated from post content."""
        renderer = TemplateRenderer()
        post = Post(
            path=Path("test.md"),
            title="Test Post",
            content="![Image](cover.jpg)\n\nThis is the first paragraph with some **bold** text.\n\nThis is the second paragraph.",
            html_content="<p>Test content</p>",
            date=dt.datetime(2024, 3, 1, 10, 0, 0, tzinfo=dt.UTC),
            metadata={},
        )

        html = renderer.render_post(
            post, site_title="Test Blog", site_url="https://example.com"
        )

        # Description should skip image and extract first paragraph with formatting removed
        assert (
            '<meta name="description" content="This is the first paragraph with some bold text.">'
            in html
        )
        assert (
            '<meta property="og:description" content="This is the first paragraph with some bold text.">'
            in html
        )
        assert (
            '<meta name="twitter:description" content="This is the first paragraph with some bold text.">'
            in html
        )

    def test_render_page_seo_meta_tags(self) -> None:
        """Test that SEO meta tags are rendered correctly for pages."""
        renderer = TemplateRenderer()
        page = Page(
            path=Path("about.md"),
            title="About Page",
            content="Test content",
            html_content="<p>Test content</p>",
            metadata={
                "author": "Jane Smith",
                "description": "About this site",
                "cover": "https://example.com/page-cover.jpg",
                "twitter_creator": "@janesmith",
            },
        )

        html = renderer.render_page(
            page, site_title="Test Blog", site_url="https://example.com"
        )

        # Check standard SEO meta tags
        assert '<meta name="author" content="Jane Smith">' in html
        assert '<meta name="description" content="About this site">' in html

        # Check Open Graph meta tags
        assert '<meta property="og:title" content="About Page">' in html
        assert '<meta property="og:type" content="website">' in html
        assert (
            '<meta property="og:url" content="https://example.com/about.html">' in html
        )
        assert '<meta property="og:description" content="About this site">' in html
        assert (
            '<meta property="og:image" content="https://example.com/page-cover.jpg">'
            in html
        )

        # Check Twitter Card meta tags
        assert '<meta name="twitter:card" content="summary_large_image">' in html
        assert '<meta name="twitter:title" content="About Page">' in html
        assert '<meta name="twitter:creator" content="@janesmith">' in html

    def test_render_post_with_relative_cover_absolute_path(self) -> None:
        """Test that posts with relative cover paths (starting with /) are rendered with site_url."""
        renderer = TemplateRenderer()
        post = Post(
            path=Path("test.md"),
            title="Test Post",
            content="Test content",
            html_content="<p>Test content</p>",
            date=dt.datetime(2024, 3, 1, 10, 0, 0, tzinfo=dt.UTC),
            metadata={
                "cover": "/images/cover.jpg",
            },
        )

        html = renderer.render_post(
            post, site_title="Test Blog", site_url="https://example.com"
        )

        # Check that site_url is prepended to relative path
        assert (
            '<meta property="og:image" content="https://example.com/images/cover.jpg">'
            in html
        )
        assert (
            '<meta name="twitter:image" content="https://example.com/images/cover.jpg">'
            in html
        )

    def test_render_post_with_relative_cover_no_slash(self) -> None:
        """Test that posts with relative cover paths (no leading /) are rendered with site_url/."""
        renderer = TemplateRenderer()
        post = Post(
            path=Path("test.md"),
            title="Test Post",
            content="Test content",
            html_content="<p>Test content</p>",
            date=dt.datetime(2024, 3, 1, 10, 0, 0, tzinfo=dt.UTC),
            metadata={
                "cover": "images/cover.jpg",
            },
        )

        html = renderer.render_post(
            post, site_title="Test Blog", site_url="https://example.com"
        )

        # Check that site_url/ is prepended to relative path
        assert (
            '<meta property="og:image" content="https://example.com/images/cover.jpg">'
            in html
        )
        assert (
            '<meta name="twitter:image" content="https://example.com/images/cover.jpg">'
            in html
        )

    def test_render_post_with_fully_qualified_cover(self) -> None:
        """Test that posts with fully-qualified cover URLs are used as-is."""
        renderer = TemplateRenderer()
        post = Post(
            path=Path("test.md"),
            title="Test Post",
            content="Test content",
            html_content="<p>Test content</p>",
            date=dt.datetime(2024, 3, 1, 10, 0, 0, tzinfo=dt.UTC),
            metadata={
                "cover": "https://cdn.example.com/images/cover.jpg",
            },
        )

        html = renderer.render_post(
            post, site_title="Test Blog", site_url="https://example.com"
        )

        # Check that fully-qualified URL is used as-is
        assert (
            '<meta property="og:image" content="https://cdn.example.com/images/cover.jpg">'
            in html
        )
        assert (
            '<meta name="twitter:image" content="https://cdn.example.com/images/cover.jpg">'
            in html
        )

    def test_init_with_site_url(self) -> None:
        """Test initializing renderer with site_url."""
        renderer = TemplateRenderer(site_url="https://example.com")
        assert renderer.site_url == "https://example.com"
        assert renderer.site_domain == "example.com"

    def test_is_external_link_absolute_external(self) -> None:
        """Test that absolute external URLs are identified correctly."""
        renderer = TemplateRenderer(site_url="https://example.com")
        assert renderer._is_external_link("https://external.com/page")
        assert renderer._is_external_link("http://external.com/page")

    def test_is_external_link_relative(self) -> None:
        """Test that relative URLs are identified as internal."""
        renderer = TemplateRenderer(site_url="https://example.com")
        assert not renderer._is_external_link("/posts/my-post")
        assert not renderer._is_external_link("posts/my-post")

    def test_is_external_link_anchor(self) -> None:
        """Test that anchor links are identified as internal."""
        renderer = TemplateRenderer(site_url="https://example.com")
        assert not renderer._is_external_link("#section")

    def test_is_external_link_same_domain(self) -> None:
        """Test that links to the same domain are identified as internal."""
        renderer = TemplateRenderer(site_url="https://example.com")
        assert not renderer._is_external_link("https://example.com/page")
        assert not renderer._is_external_link("https://www.example.com/page")

    def test_is_external_link_no_site_url(self) -> None:
        """Test external link detection when no site URL is configured."""
        renderer = TemplateRenderer()
        # With no site URL, all absolute URLs are considered external
        assert renderer._is_external_link("https://example.com/page")
        # Relative links are still internal
        assert not renderer._is_external_link("/page")

    def test_is_external_link_filter_in_template(self) -> None:
        """Test that is_external_link filter works in templates."""
        renderer = TemplateRenderer(site_url="https://example.com")
        template_str = """
        {% if "https://github.com"|is_external_link %}external{% else %}internal{% endif %}
        {% if "/about.html"|is_external_link %}external{% else %}internal{% endif %}
        """
        template = renderer.env.from_string(template_str)
        result = template.render()
        assert "external" in result
        assert "internal" in result

    def test_render_post_includes_generator_meta_tag(self, sample_post: Post) -> None:
        """Test that rendered posts include generator meta tag with version."""
        from blogmore import __version__

        renderer = TemplateRenderer()
        html = renderer.render_post(
            sample_post, site_title="Test Blog", blogmore_version=__version__
        )

        # Check for the generator meta tag with version
        assert f'<meta name="generator" content="blogmore v{__version__}">' in html

    def test_render_page_includes_generator_meta_tag(self, sample_page: Page) -> None:
        """Test that rendered pages include generator meta tag with version."""
        from blogmore import __version__

        renderer = TemplateRenderer()
        html = renderer.render_page(
            sample_page, site_title="Test Blog", blogmore_version=__version__
        )

        # Check for the generator meta tag with version
        assert f'<meta name="generator" content="blogmore v{__version__}">' in html

    def test_render_index_includes_generator_meta_tag(self, sample_post: Post) -> None:
        """Test that rendered index includes generator meta tag with version."""
        from blogmore import __version__

        renderer = TemplateRenderer()
        html = renderer.render_index(
            posts=[sample_post],
            page=1,
            total_pages=1,
            site_title="Test Blog",
            blogmore_version=__version__,
        )

        # Check for the generator meta tag with version
        assert f'<meta name="generator" content="blogmore v{__version__}">' in html
