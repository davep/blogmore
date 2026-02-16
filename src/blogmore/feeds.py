"""Feed generation for RSS and Atom formats."""

import datetime as dt
from pathlib import Path

from feedgen.feed import FeedGenerator as FeedGen  # type: ignore[import-untyped]

from blogmore.parser import Post

# Directory for feed files (excluding main RSS feed which is at root)
FEEDS_DIR = "feeds"


def normalize_site_url(site_url: str) -> str:
    """
    Normalize a site URL by removing trailing slashes.

    Args:
        site_url: The site URL to normalize

    Returns:
        The normalized site URL without trailing slash, or empty string if empty
    """
    return site_url.rstrip("/") if site_url else ""


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
        site_url: Base URL of the site (will be normalized to remove trailing slash)
        feed_url: Full URL to this feed
        description: Optional description for the feed

    Returns:
        Configured FeedGenerator instance
    """
    fg = FeedGen()
    # Normalize site_url to remove trailing slash
    site_url = normalize_site_url(site_url)
    # Use a fallback URL if site_url is empty
    base_url = site_url if site_url else "https://example.com"
    fg.id(base_url)
    fg.title(site_title)
    # IMPORTANT: Order matters! The last link becomes the channel <link> in RSS.
    # Add self link first, then alternate link (which becomes the channel link).
    fg.link(href=feed_url if feed_url else f"{base_url}/feed.rss", rel="self")
    fg.link(href=base_url, rel="alternate")
    fg.description(description or f"Latest posts from {site_title}")
    fg.language("en")
    return fg


def add_post_to_feed(fg: FeedGen, post: Post, site_url: str) -> None:
    """
    Add a post to a feed.

    Args:
        fg: FeedGenerator instance
        post: Post to add to the feed
        site_url: Base URL of the site (will be normalized to remove trailing slash)
    """
    fe = fg.add_entry()
    # Normalize site_url to remove trailing slash
    site_url = normalize_site_url(site_url)
    # Use a fallback URL if site_url is empty
    base_url = site_url if site_url else "https://example.com"
    fe.id(f"{base_url}{post.url}")
    fe.title(post.title)
    fe.link(href=f"{base_url}{post.url}")
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
    rss_feed_url: str,
    atom_feed_url: str,
    description: str | None = None,
    max_posts: int = 20,
) -> tuple[str, str]:
    """
    Generate RSS and Atom feeds for a list of posts.

    Args:
        posts: List of posts to include in the feed (should be sorted newest first)
        site_title: Title of the blog site
        site_url: Base URL of the site
        rss_feed_url: Full URL to the RSS feed
        atom_feed_url: Full URL to the Atom feed
        description: Optional description for the feed
        max_posts: Maximum number of posts to include (default: 20)

    Returns:
        Tuple of (rss_xml, atom_xml) strings
    """
    # Create two separate feed generators, one for each feed type
    # This ensures each feed has the correct self-referencing URL
    feed_generator_rss = create_feed_generator(
        site_title, site_url, rss_feed_url, description
    )
    feed_generator_atom = create_feed_generator(
        site_title, site_url, atom_feed_url, description
    )

    # Add posts to both feeds in a single loop
    # NOTE: feedgen reverses the order of entries, so we add them in reverse
    # to get the correct chronological order (newest first) in the output
    for post in reversed(posts[:max_posts]):
        add_post_to_feed(feed_generator_rss, post, site_url)
        add_post_to_feed(feed_generator_atom, post, site_url)

    # Generate both feed formats and return
    return (
        feed_generator_rss.rss_str(pretty=True).decode("utf-8"),
        feed_generator_atom.atom_str(pretty=True).decode("utf-8"),
    )


def write_feeds(
    output_dir: Path,
    rss_path: str,
    atom_path: str,
    rss_xml: str,
    atom_xml: str,
) -> None:
    """
    Write RSS and Atom feeds to disk.

    Args:
        output_dir: Output directory for the site
        rss_path: Path relative to output_dir for RSS feed (including extension)
        atom_path: Path relative to output_dir for Atom feed (including extension)
        rss_xml: RSS feed XML content
        atom_xml: Atom feed XML content
    """
    # Write RSS feed
    rss_file = output_dir / rss_path
    rss_file.parent.mkdir(parents=True, exist_ok=True)
    rss_file.write_text(rss_xml, encoding="utf-8")

    # Write Atom feed
    atom_file = output_dir / atom_path
    atom_file.parent.mkdir(parents=True, exist_ok=True)
    atom_file.write_text(atom_xml, encoding="utf-8")


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
            site_url: Base URL of the site (will be normalized to remove trailing slash)
            max_posts: Maximum number of posts per feed (default: 20)
        """
        self.output_dir = output_dir
        self.site_title = site_title
        self.site_url = normalize_site_url(site_url)
        self.max_posts = max_posts

    def _get_base_url(self) -> str:
        """
        Get the effective base URL, using fallback if site_url is empty.

        Returns:
            Base URL (either site_url or fallback)
        """
        return self.site_url if self.site_url else "https://example.com"

    def generate_index_feeds(self, posts: list[Post]) -> None:
        """
        Generate main index feeds.

        Args:
            posts: List of all posts
        """
        base_url = self._get_base_url()

        # Generate both RSS and Atom feeds with correct self-referencing URLs
        rss_feed_url = f"{base_url}/feed.xml"
        atom_feed_url = f"{base_url}/{FEEDS_DIR}/all.atom.xml"

        rss_xml, atom_xml = generate_feed(
            posts=posts,
            site_title=self.site_title,
            site_url=self.site_url,
            rss_feed_url=rss_feed_url,
            atom_feed_url=atom_feed_url,
            description=f"Latest posts from {self.site_title}",
            max_posts=self.max_posts,
        )

        write_feeds(
            self.output_dir,
            "feed.xml",
            f"{FEEDS_DIR}/all.atom.xml",
            rss_xml,
            atom_xml,
        )

    def generate_category_feeds(
        self,
        posts_by_category: dict[str, tuple[str, list[Post]]],
    ) -> None:
        """
        Generate feeds for each category.

        Args:
            posts_by_category: Dictionary mapping category (lowercase) to (display_name, posts)
        """
        base_url = self._get_base_url()
        for category_lower, (
            category_display,
            category_posts,
        ) in posts_by_category.items():
            # Sanitize category for filename
            from blogmore.generator import sanitize_for_url

            safe_category = sanitize_for_url(category_lower)

            # Generate both RSS and Atom feeds with correct self-referencing URLs
            rss_feed_url = f"{base_url}/{FEEDS_DIR}/{safe_category}.rss.xml"
            atom_feed_url = f"{base_url}/{FEEDS_DIR}/{safe_category}.atom.xml"

            rss_xml, atom_xml = generate_feed(
                posts=category_posts,
                site_title=self.site_title,
                site_url=self.site_url,
                rss_feed_url=rss_feed_url,
                atom_feed_url=atom_feed_url,
                description=f'Posts in category "{category_display}" from {self.site_title}',
                max_posts=self.max_posts,
            )

            write_feeds(
                self.output_dir,
                f"{FEEDS_DIR}/{safe_category}.rss.xml",
                f"{FEEDS_DIR}/{safe_category}.atom.xml",
                rss_xml,
                atom_xml,
            )
