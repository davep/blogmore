"""Unit tests for the feeds module."""

import datetime as dt
from pathlib import Path

from blogmore.feeds import (
    BlogFeedGenerator,
    add_post_to_feed,
    create_feed_generator,
    generate_feed,
    write_feeds,
)
from blogmore.parser import Post


class TestCreateFeedGenerator:
    """Test the create_feed_generator function."""

    def test_create_feed_generator(self) -> None:
        """Test creating a basic feed generator."""
        fg = create_feed_generator(
            site_title="Test Blog",
            site_url="https://example.com",
            feed_url="https://example.com/feed.xml",
        )

        assert fg is not None
        # Check that basic properties are set
        assert fg.title() == "Test Blog"

    def test_create_feed_generator_normalizes_trailing_slash(self) -> None:
        """Test that create_feed_generator normalizes site_url with trailing slash."""
        fg = create_feed_generator(
            site_title="Test Blog",
            site_url="https://example.com/",
            feed_url="https://example.com/feed.xml",
        )

        assert fg is not None
        # The URL should be normalized (no double slashes in links)
        assert fg.title() == "Test Blog"

    def test_create_feed_generator_with_description(self) -> None:
        """Test creating feed generator with custom description."""
        fg = create_feed_generator(
            site_title="Test Blog",
            site_url="https://example.com",
            feed_url="https://example.com/feed.xml",
            description="My custom description",
        )

        assert "My custom description" in fg.description()

    def test_create_feed_generator_empty_url(self) -> None:
        """Test creating feed generator with empty site URL."""
        fg = create_feed_generator(
            site_title="Test Blog",
            site_url="",
            feed_url="",
        )

        # Should use fallback URL
        assert fg is not None


class TestAddPostToFeed:
    """Test the add_post_to_feed function."""

    def test_add_post_to_feed(self, sample_post: Post) -> None:
        """Test adding a post to a feed."""
        fg = create_feed_generator(
            site_title="Test Blog",
            site_url="https://example.com",
            feed_url="https://example.com/feed.xml",
        )
        add_post_to_feed(fg, sample_post, "https://example.com")

        # Check that the feed now has entries
        entries = fg.entry()
        assert len(entries) == 1

    def test_add_post_with_date(self, sample_post: Post) -> None:
        """Test that post date is included in feed."""
        fg = create_feed_generator(
            site_title="Test Blog",
            site_url="https://example.com",
            feed_url="https://example.com/feed.xml",
        )
        add_post_to_feed(fg, sample_post, "https://example.com")

        entries = fg.entry()
        assert entries[0].published() is not None

    def test_add_post_with_category(self, sample_post: Post) -> None:
        """Test that post category is included in feed."""
        fg = create_feed_generator(
            site_title="Test Blog",
            site_url="https://example.com",
            feed_url="https://example.com/feed.xml",
        )
        add_post_to_feed(fg, sample_post, "https://example.com")

        entries = fg.entry()
        categories = [cat["term"] for cat in entries[0].category()]
        assert "python" in categories

    def test_add_post_with_tags(self, sample_post: Post) -> None:
        """Test that post tags are included in feed."""
        fg = create_feed_generator(
            site_title="Test Blog",
            site_url="https://example.com",
            feed_url="https://example.com/feed.xml",
        )
        add_post_to_feed(fg, sample_post, "https://example.com")

        entries = fg.entry()
        categories = [cat["term"] for cat in entries[0].category()]
        assert "python" in categories
        assert "testing" in categories

    def test_add_post_without_date(self, sample_post_without_date: Post) -> None:
        """Test adding post without date doesn't crash."""
        fg = create_feed_generator(
            site_title="Test Blog",
            site_url="https://example.com",
            feed_url="https://example.com/feed.xml",
        )
        add_post_to_feed(fg, sample_post_without_date, "https://example.com")

        entries = fg.entry()
        assert len(entries) == 1

    def test_add_post_relative_urls_made_absolute(self) -> None:
        """Test that relative URLs in post HTML content are made absolute in the feed."""
        post = Post(
            path=Path("test-post.md"),
            title="Image Post",
            content="Some content with an image.",
            html_content='<p><img src="/attachments/2026/02/11/banner.png"></p>',
            date=None,
        )
        fg = create_feed_generator(
            site_title="Test Blog",
            site_url="https://example.com",
            feed_url="https://example.com/feed.xml",
        )
        add_post_to_feed(fg, post, "https://example.com")

        entry_content = fg.entry()[0].content()
        assert entry_content is not None
        assert 'src="/attachments/' not in entry_content["content"]
        assert (
            "https://example.com/attachments/2026/02/11/banner.png"
            in entry_content["content"]
        )


class TestGenerateFeed:
    """Test the generate_feed function."""

    def test_generate_feed_basic(self, sample_post: Post) -> None:
        """Test generating basic RSS and Atom feeds."""
        rss_xml, atom_xml = generate_feed(
            posts=[sample_post],
            site_title="Test Blog",
            site_url="https://example.com",
            rss_feed_url="https://example.com/feed.xml",
            atom_feed_url="https://example.com/feeds/all.atom.xml",
        )

        assert rss_xml
        assert atom_xml
        assert "Test Post" in rss_xml
        assert "Test Post" in atom_xml

    def test_generate_feed_with_multiple_posts(
        self, sample_post: Post, sample_draft_post: Post
    ) -> None:
        """Test generating feed with multiple posts."""
        rss_xml, atom_xml = generate_feed(
            posts=[sample_post, sample_draft_post],
            site_title="Test Blog",
            site_url="https://example.com",
            rss_feed_url="https://example.com/feed.xml",
            atom_feed_url="https://example.com/feeds/all.atom.xml",
        )

        assert "Test Post" in rss_xml
        assert "Draft Post" in rss_xml
        assert "Test Post" in atom_xml
        assert "Draft Post" in atom_xml

    def test_generate_feed_max_posts(
        self, sample_post: Post, sample_draft_post: Post
    ) -> None:
        """Test that max_posts limit is respected."""
        # Create a list with more posts than max
        posts = [sample_post] * 25  # 25 posts

        rss_xml, atom_xml = generate_feed(
            posts=posts,
            site_title="Test Blog",
            site_url="https://example.com",
            rss_feed_url="https://example.com/feed.xml",
            atom_feed_url="https://example.com/feeds/all.atom.xml",
            max_posts=10,
        )

        # Count items in feed (rough check)
        # RSS has <item> tags, Atom has <entry> tags
        assert rss_xml.count("<item>") <= 10
        assert atom_xml.count("<entry>") <= 10

    def test_generate_feed_empty_posts(self) -> None:
        """Test generating feed with no posts."""
        rss_xml, atom_xml = generate_feed(
            posts=[],
            site_title="Test Blog",
            site_url="https://example.com",
            rss_feed_url="https://example.com/feed.xml",
            atom_feed_url="https://example.com/feeds/all.atom.xml",
        )

        assert rss_xml
        assert atom_xml
        # Should still have feed structure
        assert "Test Blog" in rss_xml
        assert "Test Blog" in atom_xml


class TestWriteFeeds:
    """Test the write_feeds function."""

    def test_write_feeds(self, tmp_path: Path) -> None:
        """Test writing RSS and Atom feeds to disk."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        rss_xml = '<?xml version="1.0" ?><rss></rss>'
        atom_xml = '<?xml version="1.0" ?><feed></feed>'

        write_feeds(
            output_dir=output_dir,
            rss_path="feed.xml",
            atom_path="feeds/all.atom.xml",
            rss_xml=rss_xml,
            atom_xml=atom_xml,
        )

        # Check that files were created
        assert (output_dir / "feed.xml").exists()
        assert (output_dir / "feeds" / "all.atom.xml").exists()

        # Check content
        assert (output_dir / "feed.xml").read_text() == rss_xml
        assert (output_dir / "feeds" / "all.atom.xml").read_text() == atom_xml

    def test_write_feeds_creates_directories(self, tmp_path: Path) -> None:
        """Test that write_feeds creates necessary directories."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        rss_xml = '<?xml version="1.0" ?><rss></rss>'
        atom_xml = '<?xml version="1.0" ?><feed></feed>'

        # feeds/ directory doesn't exist yet
        write_feeds(
            output_dir=output_dir,
            rss_path="feed.xml",
            atom_path="feeds/subdir/all.atom.xml",
            rss_xml=rss_xml,
            atom_xml=atom_xml,
        )

        # Should create the directory structure
        assert (output_dir / "feeds" / "subdir" / "all.atom.xml").exists()


class TestBlogFeedGenerator:
    """Test the BlogFeedGenerator class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test initializing BlogFeedGenerator."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generator = BlogFeedGenerator(
            output_dir=output_dir,
            site_title="Test Blog",
            site_url="https://example.com",
            max_posts=15,
        )

        assert generator.output_dir == output_dir
        assert generator.site_title == "Test Blog"
        assert generator.site_url == "https://example.com"
        assert generator.max_posts == 15

    def test_init_normalizes_trailing_slash(self, tmp_path: Path) -> None:
        """Test that BlogFeedGenerator normalizes site_url with trailing slash."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generator = BlogFeedGenerator(
            output_dir=output_dir,
            site_title="Test Blog",
            site_url="https://example.com/",
            max_posts=15,
        )

        # Trailing slash should be removed
        assert generator.site_url == "https://example.com"

    def test_generate_index_feeds(self, tmp_path: Path, sample_post: Post) -> None:
        """Test generating index feeds."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generator = BlogFeedGenerator(
            output_dir=output_dir,
            site_title="Test Blog",
            site_url="https://example.com",
        )

        generator.generate_index_feeds(posts=[sample_post])

        # Check that feed files were created
        assert (output_dir / "feed.xml").exists()
        assert (output_dir / "feeds" / "all.atom.xml").exists()

        # Check content
        rss_content = (output_dir / "feed.xml").read_text()
        assert "Test Post" in rss_content

    def test_generate_category_feeds(self, tmp_path: Path, sample_post: Post) -> None:
        """Test generating category feeds."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generator = BlogFeedGenerator(
            output_dir=output_dir,
            site_title="Test Blog",
            site_url="https://example.com",
        )

        posts_by_category = {
            "python": ("Python", [sample_post]),
        }

        generator.generate_category_feeds(posts_by_category=posts_by_category)

        # Check that feed files were created
        assert (output_dir / "feeds" / "python.rss.xml").exists()
        assert (output_dir / "feeds" / "python.atom.xml").exists()

        # Check content
        rss_content = (output_dir / "feeds" / "python.rss.xml").read_text()
        assert "Test Post" in rss_content
        assert "Python" in rss_content

    def test_get_base_url_with_site_url(self, tmp_path: Path) -> None:
        """Test _get_base_url with site_url set."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generator = BlogFeedGenerator(
            output_dir=output_dir,
            site_title="Test Blog",
            site_url="https://example.com",
        )

        assert generator._get_base_url() == "https://example.com"

    def test_get_base_url_without_site_url(self, tmp_path: Path) -> None:
        """Test _get_base_url with empty site_url."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        generator = BlogFeedGenerator(
            output_dir=output_dir,
            site_title="Test Blog",
            site_url="",
        )

        # Should use fallback
        assert generator._get_base_url() == "https://example.com"

    def test_generate_feeds_with_timezone_aware_dates(self, tmp_path: Path) -> None:
        """Test generating feeds with timezone-aware dates."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create post with timezone-aware date
        post = Post(
            path=Path("test.md"),
            title="Test Post",
            content="Content",
            html_content="<p>Content</p>",
            date=dt.datetime(2024, 1, 15, 12, 0, 0, tzinfo=dt.UTC),
        )

        generator = BlogFeedGenerator(
            output_dir=output_dir,
            site_title="Test Blog",
            site_url="https://example.com",
        )

        generator.generate_index_feeds(posts=[post])

        # Should generate without errors
        assert (output_dir / "feed.xml").exists()
