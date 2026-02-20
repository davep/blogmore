"""Static site generator for blog content."""

import datetime as dt
import re
import shutil
from collections import defaultdict
from importlib.resources import files
from pathlib import Path
from typing import Any

from blogmore import __version__
from blogmore.feeds import BlogFeedGenerator
from blogmore.icons import IconGenerator, detect_source_icon
from blogmore.parser import Page, Post, PostParser, remove_date_prefix
from blogmore.renderer import TemplateRenderer
from blogmore.search import write_search_index
from blogmore.utils import normalize_site_url


def sanitize_for_url(value: str) -> str:
    """Sanitize a string for safe use in URLs and filenames.

    Args:
        value: The string to sanitize

    Returns:
        A sanitized string safe for URLs and filenames
    """
    # Remove or replace dangerous characters
    # Allow only alphanumeric, dash, underscore
    sanitized = re.sub(r"[^\w\-]", "-", value.lower())
    # Remove multiple consecutive dashes
    sanitized = re.sub(r"-+", "-", sanitized)
    # Remove leading/trailing dashes
    sanitized = sanitized.strip("-")
    # Ensure it's not empty
    return sanitized or "unnamed"


def paginate_posts(posts: list[Post], posts_per_page: int) -> list[list[Post]]:
    """Split a list of posts into pages.

    Args:
        posts: List of posts to paginate
        posts_per_page: Number of posts per page

    Returns:
        List of pages, where each page is a list of posts
    """
    if not posts:
        return []
    if posts_per_page <= 0:
        return [posts]

    pages = []
    for i in range(0, len(posts), posts_per_page):
        pages.append(posts[i : i + posts_per_page])
    return pages


class SiteGenerator:
    """Generate a static blog site from markdown posts."""

    # Directory names for organizing content
    TAG_DIR = "tag"
    CATEGORY_DIR = "category"

    # Pagination constants - posts per page for each index type
    POSTS_PER_PAGE_INDEX = 10
    POSTS_PER_PAGE_TAG = 10
    POSTS_PER_PAGE_CATEGORY = 10
    POSTS_PER_PAGE_ARCHIVE = 10

    # Feed constants - posts per feed
    POSTS_PER_FEED = 20

    def __init__(
        self,
        content_dir: Path,
        templates_dir: Path | None,
        output_dir: Path,
        site_title: str = "My Blog",
        site_subtitle: str = "",
        site_url: str = "",
        posts_per_feed: int = 20,
        extra_stylesheets: list[str] | None = None,
        default_author: str | None = None,
        sidebar_config: dict[str, Any] | None = None,
        clean_first: bool = False,
        icon_source: str | None = None,
        with_search: bool = False,
    ) -> None:
        """Initialize the site generator.

        Args:
            content_dir: Directory containing markdown posts
            templates_dir: Optional directory containing custom Jinja2 templates.
                          If not provided, uses bundled templates.
            output_dir: Directory where generated site will be written
            site_title: Title of the blog site
            site_subtitle: Subtitle of the blog site
            site_url: Base URL of the site
            posts_per_feed: Maximum number of posts to include in feeds (default: 20)
            extra_stylesheets: Optional list of URLs for additional stylesheets
            default_author: Default author name for posts without author in frontmatter
            sidebar_config: Optional sidebar configuration (site_logo, links, socials)
            clean_first: Whether to remove the output directory before generating
            icon_source: Optional source icon filename in extras/ directory
            with_search: Whether to generate a search index and search page
        """
        self.content_dir = content_dir
        self.templates_dir = templates_dir
        self.output_dir = output_dir
        self.site_title = site_title
        self.site_subtitle = site_subtitle
        self.site_url = normalize_site_url(site_url)
        self.posts_per_feed = posts_per_feed
        self.default_author = default_author
        self.sidebar_config = sidebar_config or {}
        self.clean_first = clean_first
        self.icon_source = icon_source
        self.with_search = with_search

        self.parser = PostParser(site_url=self.site_url)
        self.renderer = TemplateRenderer(
            templates_dir, extra_stylesheets, self.site_url
        )

    def _detect_favicon(self) -> str | None:
        """Detect if a favicon file exists in the icons or extras directory.

        Checks for favicon files with common extensions in priority order.
        First checks the icons directory (for generated icons), then falls back
        to the extras directory (for manually provided icons).

        Returns:
            The favicon URL (relative to site root) if found, None otherwise
        """
        # First check icons directory (generated icons)
        icons_dir = self.output_dir / "icons"
        if icons_dir.exists():
            favicon_path = icons_dir / "favicon.ico"
            if favicon_path.is_file():
                return "/icons/favicon.ico"

        # Fall back to extras directory (existing behavior)
        extras_dir = self.content_dir / "extras"
        if not extras_dir.exists():
            return None

        # Common favicon extensions in priority order
        favicon_extensions = [".ico", ".png", ".svg", ".gif", ".jpg", ".jpeg"]

        # Check for favicon files
        for ext in favicon_extensions:
            favicon_path = extras_dir / f"favicon{ext}"
            if favicon_path.is_file():
                return f"/favicon{ext}"

        return None

    def _detect_generated_icons(self) -> bool:
        """Detect if generated platform icons exist in the icons directory.

        Returns:
            True if generated icons exist, False otherwise
        """
        icons_dir = self.output_dir / "icons"
        if not icons_dir.exists():
            return False

        # Check if the main Apple touch icon exists as an indicator
        apple_icon_path = icons_dir / "apple-touch-icon.png"
        return apple_icon_path.is_file()

    def _generate_icons(self) -> None:
        """Generate icons from a source image if present."""
        extras_dir = self.content_dir / "extras"

        # Look for a source icon (using configured name if provided)
        source_icon = detect_source_icon(extras_dir, self.icon_source)

        if source_icon:
            print(f"Found source icon: {source_icon.name}")
            print("Generating favicon and Apple touch icons...")

            # Generate to /icons subdirectory
            icons_output_dir = self.output_dir / "icons"
            generator = IconGenerator(source_icon, icons_output_dir)
            generated = generator.generate_all()

            if generated:
                print(f"Generated {len(generated)} icon file(s):")
                for icon_name in generated:
                    print(f"  - icons/{icon_name}")
            else:
                print("Warning: No icons were generated")

    def _get_global_context(self) -> dict[str, Any]:
        """Get the global context available to all templates."""
        context = {
            "site_title": self.site_title,
            "site_subtitle": self.site_subtitle,
            "site_url": self.site_url,
            "tag_dir": self.TAG_DIR,
            "category_dir": self.CATEGORY_DIR,
            "favicon_url": self._detect_favicon(),
            "has_platform_icons": self._detect_generated_icons(),
            "blogmore_version": __version__,
            "with_search": self.with_search,
        }
        # Merge sidebar config into context
        context.update(self.sidebar_config)
        return context

    def generate(self, include_drafts: bool = False) -> None:
        """Generate the complete static site.

        Args:
            include_drafts: Whether to include posts marked as drafts
        """
        # Clean output directory if requested
        if self.clean_first and self.output_dir.exists():
            print(f"Removing output directory: {self.output_dir}")
            shutil.rmtree(self.output_dir)

        # Parse all posts
        print(f"Parsing posts from {self.content_dir}...")
        posts = self.parser.parse_directory(
            self.content_dir, include_drafts=include_drafts
        )
        print(f"Found {len(posts)} posts")

        # Apply default author to posts that don't have one
        if self.default_author:
            for post in posts:
                if post.metadata is not None and "author" not in post.metadata:
                    post.metadata["author"] = self.default_author

        # Parse all pages from the pages subdirectory
        pages_dir = self.content_dir / "pages"
        pages = self.parser.parse_pages_directory(pages_dir)
        if pages:
            print(f"Found {len(pages)} pages")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate icons from source image BEFORE generating HTML pages
        # so that the has_apple_touch_icons flag is correctly set
        self._generate_icons()

        # Generate individual post pages
        print("Generating post pages...")
        for post in posts:
            self._generate_post_page(post, posts, pages)

        # Generate static pages
        if pages:
            print("Generating static pages...")
            for page in pages:
                self._generate_page(page, pages)

        # Generate index page
        print("Generating index page...")
        self._generate_index_page(posts, pages)

        # Generate archive page
        print("Generating archive page...")
        self._generate_archive_page(posts, pages)

        # Generate date-based archive pages
        print("Generating date-based archive pages...")
        self._generate_date_archives(posts, pages)

        # Generate tag pages
        print("Generating tag pages...")
        self._generate_tag_pages(posts, pages)

        # Generate tags overview page
        print("Generating tags overview page...")
        self._generate_tags_page(posts, pages)

        # Generate category pages
        print("Generating category pages...")
        self._generate_category_pages(posts, pages)

        # Generate categories overview page
        print("Generating categories overview page...")
        self._generate_categories_page(posts, pages)

        # Generate feeds
        print("Generating RSS and Atom feeds...")
        self._generate_feeds(posts)

        # Generate search index and search page (only when enabled)
        if self.with_search:
            print("Generating search index and search page...")
            self._generate_search_index(posts)
            self._generate_search_page(pages)

        # Copy static assets if they exist
        self._copy_static_assets()

        # Copy post attachments from content directory
        self._copy_attachments()

        # Copy extra files from extras directory
        self._copy_extras()

        print(f"Site generation complete! Output: {self.output_dir}")

    def _generate_post_page(
        self, post: Post, all_posts: list[Post], pages: list[Page]
    ) -> None:
        """Generate a single post page."""
        context = self._get_global_context()
        context["all_posts"] = all_posts
        context["pages"] = pages

        # Find previous and next posts in chronological order
        # all_posts is already sorted by date (newest first)
        try:
            current_index = all_posts.index(post)
            # Previous post is older (higher index)
            context["prev_post"] = (
                all_posts[current_index + 1]
                if current_index + 1 < len(all_posts)
                else None
            )
            # Next post is newer (lower index)
            context["next_post"] = (
                all_posts[current_index - 1] if current_index > 0 else None
            )
        except ValueError:
            # Post not in list, no navigation
            context["prev_post"] = None
            context["next_post"] = None

        html = self.renderer.render_post(post, **context)

        # Determine output path based on date
        if post.date:
            # Create year/month/day directory structure
            year = post.date.year
            month = f"{post.date.month:02d}"
            day = f"{post.date.day:02d}"

            # Remove date prefix from slug if present
            slug = remove_date_prefix(post.slug)

            # Create directory structure
            post_dir = self.output_dir / str(year) / month / day
            post_dir.mkdir(parents=True, exist_ok=True)
            output_path = post_dir / f"{slug}.html"
        else:
            # Fallback for posts without dates
            output_path = self.output_dir / f"{post.slug}.html"

        output_path.write_text(html, encoding="utf-8")

    def _generate_page(self, page: Page, pages: list[Page]) -> None:
        """Generate a single static page."""
        context = self._get_global_context()
        context["pages"] = pages

        html = self.renderer.render_page(page, **context)

        # Output to root of site
        output_path = self.output_dir / f"{page.slug}.html"
        output_path.write_text(html, encoding="utf-8")

    def _generate_index_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the main index page with pagination."""
        context = self._get_global_context()
        context["pages"] = pages

        # Paginate posts
        paginated_posts = paginate_posts(posts, self.POSTS_PER_PAGE_INDEX)
        if not paginated_posts:
            paginated_posts = [[]]  # Empty page if no posts

        total_pages = len(paginated_posts)

        # Generate each page
        for page_num, page_posts in enumerate(paginated_posts, start=1):
            html = self.renderer.render_index(
                page_posts, page=page_num, total_pages=total_pages, **context
            )

            if page_num == 1:
                # First page is at root
                output_path = self.output_dir / "index.html"
            else:
                # Additional pages in page/ directory
                page_dir = self.output_dir / "page"
                page_dir.mkdir(exist_ok=True)
                output_path = page_dir / f"{page_num}.html"

            output_path.write_text(html, encoding="utf-8")

    def _generate_archive_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the archive page."""
        context = self._get_global_context()
        context["pages"] = pages
        html = self.renderer.render_archive(
            posts, page=1, total_pages=1, base_path="/archive", **context
        )
        output_path = self.output_dir / "archive.html"
        output_path.write_text(html, encoding="utf-8")

    def _generate_date_archives(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate date-based archive pages (year, month, day) with pagination."""
        # Group posts by year, month, and day
        posts_by_year: dict[int, list[Post]] = defaultdict(list)
        posts_by_month: dict[tuple[int, int], list[Post]] = defaultdict(list)
        posts_by_day: dict[tuple[int, int, int], list[Post]] = defaultdict(list)

        for post in posts:
            if post.date:
                year = post.date.year
                month = post.date.month
                day = post.date.day

                posts_by_year[year].append(post)
                posts_by_month[(year, month)].append(post)
                posts_by_day[(year, month, day)].append(post)

        context = self._get_global_context()
        context["pages"] = pages

        # Generate year archives with pagination
        for year, year_posts in posts_by_year.items():
            year_dir = self.output_dir / str(year)
            year_dir.mkdir(parents=True, exist_ok=True)

            # Paginate posts
            paginated_posts = paginate_posts(year_posts, self.POSTS_PER_PAGE_ARCHIVE)
            total_pages = len(paginated_posts)

            # Generate each page
            for page_num, page_posts in enumerate(paginated_posts, start=1):
                # Base path for pagination links
                base_path = f"/{year}"

                html = self.renderer.render_archive(
                    page_posts,
                    archive_title=f"Posts from {year}",
                    page=page_num,
                    total_pages=total_pages,
                    base_path=base_path,
                    **context,
                )

                if page_num == 1:
                    # First page is at year/index.html
                    output_path = year_dir / "index.html"
                else:
                    # Additional pages in year/page/ directory
                    page_dir = year_dir / "page"
                    page_dir.mkdir(exist_ok=True)
                    output_path = page_dir / f"{page_num}.html"

                output_path.write_text(html, encoding="utf-8")

        # Generate month archives with pagination
        for (year, month), month_posts in posts_by_month.items():
            month_dir = self.output_dir / str(year) / f"{month:02d}"
            month_dir.mkdir(parents=True, exist_ok=True)

            month_name = dt.datetime(year, month, 1).strftime("%B %Y")

            # Paginate posts
            paginated_posts = paginate_posts(month_posts, self.POSTS_PER_PAGE_ARCHIVE)
            total_pages = len(paginated_posts)

            # Generate each page
            for page_num, page_posts in enumerate(paginated_posts, start=1):
                # Base path for pagination links
                base_path = f"/{year}/{month:02d}"

                html = self.renderer.render_archive(
                    page_posts,
                    archive_title=f"Posts from {month_name}",
                    page=page_num,
                    total_pages=total_pages,
                    base_path=base_path,
                    **context,
                )

                if page_num == 1:
                    # First page is at year/month/index.html
                    output_path = month_dir / "index.html"
                else:
                    # Additional pages in year/month/page/ directory
                    page_dir = month_dir / "page"
                    page_dir.mkdir(exist_ok=True)
                    output_path = page_dir / f"{page_num}.html"

                output_path.write_text(html, encoding="utf-8")

        # Generate day archives with pagination
        for (year, month, day), day_posts in posts_by_day.items():
            day_dir = self.output_dir / str(year) / f"{month:02d}" / f"{day:02d}"
            day_dir.mkdir(parents=True, exist_ok=True)

            date_str = dt.datetime(year, month, day).strftime("%B %d, %Y")

            # Paginate posts
            paginated_posts = paginate_posts(day_posts, self.POSTS_PER_PAGE_ARCHIVE)
            total_pages = len(paginated_posts)

            # Generate each page
            for page_num, page_posts in enumerate(paginated_posts, start=1):
                # Base path for pagination links
                base_path = f"/{year}/{month:02d}/{day:02d}"

                html = self.renderer.render_archive(
                    page_posts,
                    archive_title=f"Posts from {date_str}",
                    page=page_num,
                    total_pages=total_pages,
                    base_path=base_path,
                    **context,
                )

                if page_num == 1:
                    # First page is at year/month/day/index.html
                    output_path = day_dir / "index.html"
                else:
                    # Additional pages in year/month/day/page/ directory
                    page_dir = day_dir / "page"
                    page_dir.mkdir(exist_ok=True)
                    output_path = page_dir / f"{page_num}.html"

                output_path.write_text(html, encoding="utf-8")

    def _generate_tag_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each tag with pagination."""
        # Group posts by tag (case-insensitive)
        # Key is lowercase tag, value is (display_name, posts)
        posts_by_tag = self._group_posts_by_tag(posts)

        # Create tag directory
        tag_dir = self.output_dir / self.TAG_DIR
        tag_dir.mkdir(exist_ok=True)

        # Generate paginated pages for each tag
        for tag_lower, (tag_display, tag_posts) in posts_by_tag.items():
            # Sort tag posts by date (newest first)
            # Handle timezone-aware and naive datetimes
            def get_sort_key(post: Post) -> float:
                if post.date is None:
                    return 0.0
                if post.date.tzinfo:
                    return post.date.timestamp()
                return post.date.replace(tzinfo=dt.UTC).timestamp()

            tag_posts.sort(key=get_sort_key, reverse=True)

            # Sanitize tag for filename (use lowercase version)
            safe_tag = sanitize_for_url(tag_lower)

            # Paginate posts
            paginated_posts = paginate_posts(tag_posts, self.POSTS_PER_PAGE_TAG)
            total_pages = len(paginated_posts)

            context = self._get_global_context()
            context["pages"] = pages

            # Generate each page
            for page_num, page_posts in enumerate(paginated_posts, start=1):
                html = self.renderer.render_tag_page(
                    tag_display,  # Use display name for rendering
                    page_posts,
                    page=page_num,
                    total_pages=total_pages,
                    safe_tag=safe_tag,
                    **context,
                )

                if page_num == 1:
                    # First page is at tag/{tag}.html
                    output_path = tag_dir / f"{safe_tag}.html"
                else:
                    # Additional pages in tag/{tag}/ directory
                    tag_page_dir = tag_dir / safe_tag
                    tag_page_dir.mkdir(exist_ok=True)
                    output_path = tag_page_dir / f"{page_num}.html"

                output_path.write_text(html, encoding="utf-8")

    def _group_posts_by_tag(
        self, posts: list[Post]
    ) -> dict[str, tuple[str, list[Post]]]:
        """Group posts by tag (case-insensitive).

        Args:
            posts: List of posts to group

        Returns:
            Dictionary mapping lowercase tag to (display_name, posts)
        """
        posts_by_tag: dict[str, tuple[str, list[Post]]] = {}
        for post in posts:
            if post.tags:
                for tag in post.tags:
                    tag_lower = tag.lower()
                    if tag_lower not in posts_by_tag:
                        # Store the first occurrence as the display name
                        posts_by_tag[tag_lower] = (tag, [])
                    posts_by_tag[tag_lower][1].append(post)
        return posts_by_tag

    def _generate_tags_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the tags overview page with word cloud."""
        # Group posts by tag to get counts
        posts_by_tag = self._group_posts_by_tag(posts)

        if not posts_by_tag:
            # No tags, skip generation
            return

        # Calculate tag counts and prepare data
        tag_data: list[dict[str, Any]] = []
        min_count: int | None = None
        max_count: int | None = None

        for tag_lower, (tag_display, tag_posts) in posts_by_tag.items():
            count = len(tag_posts)
            safe_tag = sanitize_for_url(tag_lower)
            tag_data.append(
                {
                    "display_name": tag_display,
                    "safe_tag": safe_tag,
                    "count": count,
                    "tag_lower": tag_lower,
                }
            )
            if min_count is None or count < min_count:
                min_count = count
            if max_count is None or count > max_count:
                max_count = count

        # Sort alphabetically by display name
        tag_data.sort(key=lambda x: x["display_name"].lower())

        # Calculate font sizes for word cloud effect
        # Font sizes range from 1.0em to 2.5em
        min_font_size = 1.0
        max_font_size = 2.5

        # min_count and max_count are guaranteed to be set since posts_by_tag is non-empty
        assert min_count is not None
        assert max_count is not None

        if max_count > min_count:
            # Scale based on count
            for tag_info in tag_data:
                # Linear interpolation between min and max font size
                ratio = (tag_info["count"] - min_count) / (max_count - min_count)
                tag_info["font_size"] = min_font_size + ratio * (
                    max_font_size - min_font_size
                )
        else:
            # All tags have the same count, use middle size
            for tag_info in tag_data:
                tag_info["font_size"] = (min_font_size + max_font_size) / 2

        # Render the tags page
        context = self._get_global_context()
        context["pages"] = pages

        html = self.renderer.render_tags_page(tag_data, **context)

        # Output to root of site
        output_path = self.output_dir / "tags.html"
        output_path.write_text(html, encoding="utf-8")

    def _generate_categories_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the categories overview page with word cloud."""
        # Group posts by category to get counts
        posts_by_category = self._group_posts_by_category(posts)

        if not posts_by_category:
            # No categories, skip generation
            return

        # Calculate category counts and prepare data
        category_data: list[dict[str, Any]] = []
        min_count: int | None = None
        max_count: int | None = None

        for category_lower, (
            category_display,
            category_posts,
        ) in posts_by_category.items():
            count = len(category_posts)
            safe_category = sanitize_for_url(category_lower)
            category_data.append(
                {
                    "display_name": category_display,
                    "safe_category": safe_category,
                    "count": count,
                    "category_lower": category_lower,
                }
            )
            if min_count is None or count < min_count:
                min_count = count
            if max_count is None or count > max_count:
                max_count = count

        # Sort alphabetically by display name
        category_data.sort(key=lambda x: x["display_name"].lower())

        # Calculate font sizes for word cloud effect
        # Font sizes range from 1.0em to 2.5em
        min_font_size = 1.0
        max_font_size = 2.5

        # min_count and max_count are guaranteed to be set since posts_by_category is non-empty
        assert min_count is not None
        assert max_count is not None

        if max_count > min_count:
            # Scale based on count
            for category_info in category_data:
                # Linear interpolation between min and max font size
                ratio = (category_info["count"] - min_count) / (max_count - min_count)
                category_info["font_size"] = min_font_size + ratio * (
                    max_font_size - min_font_size
                )
        else:
            # All categories have the same count, use middle size
            for category_info in category_data:
                category_info["font_size"] = (min_font_size + max_font_size) / 2

        # Render the categories page
        context = self._get_global_context()
        context["pages"] = pages

        html = self.renderer.render_categories_page(category_data, **context)

        # Output to root of site
        output_path = self.output_dir / "categories.html"
        output_path.write_text(html, encoding="utf-8")

    def _generate_category_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each category with pagination."""
        # Group posts by category (case-insensitive)
        # Key is lowercase category, value is (display_name, posts)
        posts_by_category = self._group_posts_by_category(posts)

        # Create category directory
        category_dir = self.output_dir / self.CATEGORY_DIR
        category_dir.mkdir(exist_ok=True)

        # Generate paginated pages for each category
        for category_lower, (
            category_display,
            category_posts,
        ) in posts_by_category.items():
            # Sort category posts by date (newest first)
            # Handle timezone-aware and naive datetimes
            def get_sort_key(post: Post) -> float:
                if post.date is None:
                    return 0.0
                if post.date.tzinfo:
                    return post.date.timestamp()
                return post.date.replace(tzinfo=dt.UTC).timestamp()

            category_posts.sort(key=get_sort_key, reverse=True)

            # Sanitize category for filename (use lowercase version)
            safe_category = sanitize_for_url(category_lower)

            # Paginate posts
            paginated_posts = paginate_posts(
                category_posts, self.POSTS_PER_PAGE_CATEGORY
            )
            total_pages = len(paginated_posts)

            context = self._get_global_context()
            context["pages"] = pages

            # Generate each page
            for page_num, page_posts in enumerate(paginated_posts, start=1):
                html = self.renderer.render_category_page(
                    category_display,  # Use display name for rendering
                    page_posts,
                    page=page_num,
                    total_pages=total_pages,
                    safe_category=safe_category,
                    **context,
                )

                if page_num == 1:
                    # First page is at category/{category}.html
                    output_path = category_dir / f"{safe_category}.html"
                else:
                    # Additional pages in category/{category}/ directory
                    category_page_dir = category_dir / safe_category
                    category_page_dir.mkdir(exist_ok=True)
                    output_path = category_page_dir / f"{page_num}.html"

                output_path.write_text(html, encoding="utf-8")

    def _group_posts_by_category(
        self, posts: list[Post]
    ) -> dict[str, tuple[str, list[Post]]]:
        """Group posts by category (case-insensitive).

        Args:
            posts: List of posts to group

        Returns:
            Dictionary mapping lowercase category to (display_name, posts)
        """
        posts_by_category: dict[str, tuple[str, list[Post]]] = {}
        for post in posts:
            if post.category:
                category_lower = post.category.lower()
                if category_lower not in posts_by_category:
                    # Store the first occurrence as the display name
                    posts_by_category[category_lower] = (post.category, [])
                posts_by_category[category_lower][1].append(post)
        return posts_by_category

    def _generate_feeds(self, posts: list[Post]) -> None:
        """Generate RSS and Atom feeds.

        Args:
            posts: List of all posts
        """
        feed_gen = BlogFeedGenerator(
            output_dir=self.output_dir,
            site_title=self.site_title,
            site_url=self.site_url,
            max_posts=self.posts_per_feed,
        )

        # Generate main index feeds
        feed_gen.generate_index_feeds(posts)

        # Generate category feeds
        posts_by_category = self._group_posts_by_category(posts)
        # Sort posts by date for each category
        for _category_lower, (
            _category_display,
            category_posts,
        ) in posts_by_category.items():

            def get_sort_key(post: Post) -> float:
                if post.date is None:
                    return 0.0
                if post.date.tzinfo:
                    return post.date.timestamp()
                return post.date.replace(tzinfo=dt.UTC).timestamp()

            category_posts.sort(key=get_sort_key, reverse=True)

        feed_gen.generate_category_feeds(posts_by_category)

    def _generate_search_index(self, posts: list[Post]) -> None:
        """Generate the search index JSON file.

        Args:
            posts: List of all posts to index.
        """
        write_search_index(posts, self.output_dir)

    def _generate_search_page(self, pages: list[Page]) -> None:
        """Generate the search page.

        Args:
            pages: List of static pages (for the sidebar navigation).
        """
        context = self._get_global_context()
        context["pages"] = pages
        html = self.renderer.render_search_page(**context)
        output_path = self.output_dir / "search.html"
        output_path.write_text(html, encoding="utf-8")

    def _copy_static_assets(self) -> None:
        """Copy static assets (CSS, JS, images) to output directory."""
        output_static = self.output_dir / "static"

        # Clear output static directory if it exists
        if output_static.exists():
            shutil.rmtree(output_static)
        output_static.mkdir(parents=True, exist_ok=True)

        # First, copy bundled static assets
        try:
            # Get bundled static directory
            bundled_static = files("blogmore").joinpath("templates", "static")
            if bundled_static.is_dir():
                for item in bundled_static.iterdir():
                    if item.is_file():
                        # Read content and write to output
                        content = item.read_bytes()
                        output_file = output_static / item.name
                        output_file.write_bytes(content)
                print("Copied bundled static assets")
        except Exception as e:
            print(f"Warning: Could not copy bundled static assets: {e}")

        # Then, copy custom static assets (if provided), which will override bundled ones
        if self.templates_dir is not None:
            custom_static_dir = self.templates_dir / "static"
            if custom_static_dir.exists():
                for item in custom_static_dir.rglob("*"):
                    if item.is_file():
                        relative_path = item.relative_to(custom_static_dir)
                        output_file = output_static / relative_path
                        output_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, output_file)
                print(f"Copied custom static assets from {custom_static_dir}")

    def _copy_attachments(self) -> None:
        """Copy post attachments (images, files, etc.) from the attachments directory to output directory."""
        attachments_dir = self.content_dir / "attachments"

        if not attachments_dir.exists():
            print(f"No attachments directory found in {self.content_dir}")
            return

        # Count how many attachments we copy
        attachment_count = 0
        failed_count = 0

        # Recursively copy all files from the attachments directory
        for file_path in attachments_dir.rglob("*"):
            # Skip directories
            if file_path.is_file():
                try:
                    # Calculate relative path from attachments directory to preserve structure
                    relative_path = file_path.relative_to(attachments_dir)
                    # Copy to output_dir/attachments/... to preserve the attachments directory structure
                    output_path = self.output_dir / "attachments" / relative_path

                    # Create parent directories if they don't exist
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file preserving metadata
                    shutil.copy2(file_path, output_path)
                    attachment_count += 1
                except (OSError, PermissionError) as e:
                    print(f"Warning: Failed to copy attachment {file_path}: {e}")
                    failed_count += 1
                    continue

        if attachment_count > 0:
            print(f"Copied {attachment_count} attachment(s) from {attachments_dir}")
        else:
            print(f"No attachments found in {attachments_dir}")

        if failed_count > 0:
            print(f"Warning: Failed to copy {failed_count} attachment(s)")

    def _copy_extras(self) -> None:
        """Copy extra files from the extras directory to the output directory.

        Files in the extras directory are copied to the output root, preserving
        directory structure relative to the extras directory. If a file would
        override an existing file, it is allowed but a message is printed.
        """
        extras_dir = self.content_dir / "extras"

        if not extras_dir.exists():
            return

        # Count how many extras we copy
        extras_count = 0
        override_count = 0
        failed_count = 0

        # Recursively copy all files from the extras directory
        for file_path in extras_dir.rglob("*"):
            # Skip directories
            if file_path.is_file():
                try:
                    # Calculate relative path from extras directory to preserve structure
                    relative_path = file_path.relative_to(extras_dir)
                    # Copy to output_dir root, preserving directory structure
                    output_path = self.output_dir / relative_path

                    # Check if file already exists
                    file_exists = output_path.exists()

                    # Create parent directories if they don't exist
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file preserving metadata
                    shutil.copy2(file_path, output_path)
                    extras_count += 1

                    # Print message if we overrode an existing file
                    if file_exists:
                        print(f"Overriding existing file: {relative_path}")
                        override_count += 1
                except (OSError, PermissionError) as e:
                    print(f"Warning: Failed to copy extra file {file_path}: {e}")
                    failed_count += 1
                    continue

        if extras_count > 0:
            print(f"Copied {extras_count} extra file(s) from {extras_dir}")
        if override_count > 0:
            print(f"Overrode {override_count} existing file(s)")
        if failed_count > 0:
            print(f"Warning: Failed to copy {failed_count} extra file(s)")
