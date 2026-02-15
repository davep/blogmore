"""Feed generation for RSS and Atom formats."""

import datetime as dt
from pathlib import Path

from feedgen.feed import FeedGenerator as FeedGen  # type: ignore[import-untyped]

from blogmore.parser import Post


def create_feed_generator(
    site_title: str,
    site_url: str,
    feed_url: str,
    description: str | None = None,
) -> FeedGen:
    """
    Create and configure a base FeedGenerator.

    Args:
        site_title: Title of the blog site
        site_url: Base URL of the site
        feed_url: Full URL to this feed
        description: Optional description for the feed

    Returns:
        Configured FeedGenerator instance
    """
    fg = FeedGen()
    fg.id(site_url)
    fg.title(site_title)
    fg.link(href=site_url, rel="alternate")
    fg.link(href=feed_url, rel="self")
    fg.description(description or f"Latest posts from {site_title}")
    fg.language("en")
    return fg


def add_post_to_feed(fg: FeedGen, post: Post, site_url: str) -> None:
    """
    Add a post to a feed.

    Args:
        fg: FeedGenerator instance
        post: Post to add to the feed
        site_url: Base URL of the site
    """
    fe = fg.add_entry()
    fe.id(f"{site_url}{post.url}")
    fe.title(post.title)
    fe.link(href=f"{site_url}{post.url}")
    fe.content(post.html_content, type="html")

    # Add publication date if available
    if post.date:
        # Ensure timezone-aware datetime
        pub_date = (
            post.date.replace(tzinfo=dt.UTC) if post.date.tzinfo is None else post.date
        )
        fe.published(pub_date)
        fe.updated(pub_date)

    # Add category if available
    if post.category:
        fe.category(term=post.category)

    # Add tags if available
    if post.tags:
        for tag in post.tags:
            fe.category(term=tag)


def generate_feed(
    posts: list[Post],
    site_title: str,
    site_url: str,
    feed_url: str,
    description: str | None = None,
    max_posts: int = 20,
) -> tuple[str, str]:
    """
    Generate RSS and Atom feeds for a list of posts.

    Args:
        posts: List of posts to include in the feed (should be sorted newest first)
        site_title: Title of the blog site
        site_url: Base URL of the site
        feed_url: Full URL to this feed (used for RSS, Atom will use .atom extension)
        description: Optional description for the feed
        max_posts: Maximum number of posts to include (default: 20)

    Returns:
        Tuple of (rss_xml, atom_xml) strings
    """
    # Create feed generator
    fg = create_feed_generator(site_title, site_url, feed_url, description)

    # Add posts (limit to max_posts)
    # NOTE: feedgen reverses the order of entries, so we add them in reverse
    # to get the correct chronological order (newest first) in the output
    for post in reversed(posts[:max_posts]):
        add_post_to_feed(fg, post, site_url)

    # Generate RSS and Atom feeds
    rss_xml = fg.rss_str(pretty=True).decode("utf-8")
    atom_xml = fg.atom_str(pretty=True).decode("utf-8")

    return rss_xml, atom_xml


def write_feeds(
    output_dir: Path,
    feed_path: str,
    rss_xml: str,
    atom_xml: str,
) -> None:
    """
    Write RSS and Atom feeds to disk.

    Args:
        output_dir: Output directory for the site
        feed_path: Path relative to output_dir (without extension)
        rss_xml: RSS feed XML content
        atom_xml: Atom feed XML content
    """
    # Write RSS feed
    rss_path = output_dir / f"{feed_path}.rss"
    rss_path.parent.mkdir(parents=True, exist_ok=True)
    rss_path.write_text(rss_xml, encoding="utf-8")

    # Write Atom feed
    atom_path = output_dir / f"{feed_path}.atom"
    atom_path.parent.mkdir(parents=True, exist_ok=True)
    atom_path.write_text(atom_xml, encoding="utf-8")


class BlogFeedGenerator:
    """Generate RSS and Atom feeds for a blog site."""

    def __init__(
        self,
        output_dir: Path,
        site_title: str,
        site_url: str,
        max_posts: int = 20,
    ) -> None:
        """
        Initialize the feed generator.

        Args:
            output_dir: Directory where feeds will be written
            site_title: Title of the blog site
            site_url: Base URL of the site
            max_posts: Maximum number of posts per feed (default: 20)
        """
        self.output_dir = output_dir
        self.site_title = site_title
        self.site_url = site_url
        self.max_posts = max_posts

    def generate_index_feeds(self, posts: list[Post]) -> None:
        """
        Generate main index feeds.

        Args:
            posts: List of all posts
        """
        feed_url = f"{self.site_url}/feed.rss"
        rss_xml, atom_xml = generate_feed(
            posts=posts,
            site_title=self.site_title,
            site_url=self.site_url,
            feed_url=feed_url,
            description=f"Latest posts from {self.site_title}",
            max_posts=self.max_posts,
        )
        write_feeds(self.output_dir, "feed", rss_xml, atom_xml)

    def generate_tag_feeds(
        self,
        posts_by_tag: dict[str, tuple[str, list[Post]]],
        tag_dir: str,
    ) -> None:
        """
        Generate feeds for each tag.

        Args:
            posts_by_tag: Dictionary mapping tag (lowercase) to (display_name, posts)
            tag_dir: Directory name for tag pages
        """
        for tag_lower, (tag_display, tag_posts) in posts_by_tag.items():
            # Sanitize tag for filename
            from blogmore.generator import sanitize_for_url

            safe_tag = sanitize_for_url(tag_lower)

            feed_url = f"{self.site_url}/{tag_dir}/{safe_tag}/feed.rss"
            rss_xml, atom_xml = generate_feed(
                posts=tag_posts,
                site_title=self.site_title,
                site_url=self.site_url,
                feed_url=feed_url,
                description=f'Posts tagged with "{tag_display}" from {self.site_title}',
                max_posts=self.max_posts,
            )
            write_feeds(
                self.output_dir,
                f"{tag_dir}/{safe_tag}/feed",
                rss_xml,
                atom_xml,
            )

    def generate_category_feeds(
        self,
        posts_by_category: dict[str, tuple[str, list[Post]]],
        category_dir: str,
    ) -> None:
        """
        Generate feeds for each category.

        Args:
            posts_by_category: Dictionary mapping category (lowercase) to (display_name, posts)
            category_dir: Directory name for category pages
        """
        for category_lower, (
            category_display,
            category_posts,
        ) in posts_by_category.items():
            # Sanitize category for filename
            from blogmore.generator import sanitize_for_url

            safe_category = sanitize_for_url(category_lower)

            feed_url = f"{self.site_url}/{category_dir}/{safe_category}/feed.rss"
            rss_xml, atom_xml = generate_feed(
                posts=category_posts,
                site_title=self.site_title,
                site_url=self.site_url,
                feed_url=feed_url,
                description=f'Posts in category "{category_display}" from {self.site_title}',
                max_posts=self.max_posts,
            )
            write_feeds(
                self.output_dir,
                f"{category_dir}/{safe_category}/feed",
                rss_xml,
                atom_xml,
            )
