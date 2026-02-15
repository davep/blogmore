"""Static site generator for blog content."""

import datetime as dt
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from blogmore.parser import Post, PostParser, remove_date_prefix
from blogmore.renderer import TemplateRenderer


def sanitize_for_url(value: str) -> str:
    """
    Sanitize a string for safe use in URLs and filenames.

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
    """
    Split a list of posts into pages.

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

    def __init__(
        self,
        content_dir: Path,
        templates_dir: Path,
        output_dir: Path,
        site_title: str = "My Blog",
        site_url: str = "",
    ) -> None:
        """
        Initialize the site generator.

        Args:
            content_dir: Directory containing markdown posts
            templates_dir: Directory containing Jinja2 templates
            output_dir: Directory where generated site will be written
            site_title: Title of the blog site
            site_url: Base URL of the site
        """
        self.content_dir = content_dir
        self.templates_dir = templates_dir
        self.output_dir = output_dir
        self.site_title = site_title
        self.site_url = site_url

        self.parser = PostParser()
        self.renderer = TemplateRenderer(templates_dir)

    def _get_global_context(self) -> dict[str, Any]:
        """Get the global context available to all templates."""
        return {
            "site_title": self.site_title,
            "site_url": self.site_url,
            "tag_dir": self.TAG_DIR,
            "category_dir": self.CATEGORY_DIR,
        }

    def generate(self, include_drafts: bool = False) -> None:
        """
        Generate the complete static site.

        Args:
            include_drafts: Whether to include posts marked as drafts
        """
        # Parse all posts
        print(f"Parsing posts from {self.content_dir}...")
        posts = self.parser.parse_directory(
            self.content_dir, include_drafts=include_drafts
        )
        print(f"Found {len(posts)} posts")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate individual post pages
        print("Generating post pages...")
        for post in posts:
            self._generate_post_page(post, posts)

        # Generate index page
        print("Generating index page...")
        self._generate_index_page(posts)

        # Generate archive page
        print("Generating archive page...")
        self._generate_archive_page(posts)

        # Generate date-based archive pages
        print("Generating date-based archive pages...")
        self._generate_date_archives(posts)

        # Generate tag pages
        print("Generating tag pages...")
        self._generate_tag_pages(posts)

        # Generate category pages
        print("Generating category pages...")
        self._generate_category_pages(posts)

        # Copy static assets if they exist
        self._copy_static_assets()

        # Copy post attachments from content directory
        self._copy_attachments()

        print(f"Site generation complete! Output: {self.output_dir}")

    def _generate_post_page(self, post: Post, all_posts: list[Post]) -> None:
        """Generate a single post page."""
        context = self._get_global_context()
        context["all_posts"] = all_posts

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

    def _generate_index_page(self, posts: list[Post]) -> None:
        """Generate the main index page with pagination."""
        context = self._get_global_context()

        # Paginate posts
        pages = paginate_posts(posts, self.POSTS_PER_PAGE_INDEX)
        if not pages:
            pages = [[]]  # Empty page if no posts

        total_pages = len(pages)

        # Generate each page
        for page_num, page_posts in enumerate(pages, start=1):
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

    def _generate_archive_page(self, posts: list[Post]) -> None:
        """Generate the archive page."""
        context = self._get_global_context()
        html = self.renderer.render_archive(
            posts, page=1, total_pages=1, base_path="/archive", **context
        )
        output_path = self.output_dir / "archive.html"
        output_path.write_text(html, encoding="utf-8")

    def _generate_date_archives(self, posts: list[Post]) -> None:
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

        # Generate year archives with pagination
        for year, year_posts in posts_by_year.items():
            year_dir = self.output_dir / str(year)
            year_dir.mkdir(parents=True, exist_ok=True)

            # Paginate posts
            pages = paginate_posts(year_posts, self.POSTS_PER_PAGE_ARCHIVE)
            total_pages = len(pages)

            # Generate each page
            for page_num, page_posts in enumerate(pages, start=1):
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
            pages = paginate_posts(month_posts, self.POSTS_PER_PAGE_ARCHIVE)
            total_pages = len(pages)

            # Generate each page
            for page_num, page_posts in enumerate(pages, start=1):
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
            pages = paginate_posts(day_posts, self.POSTS_PER_PAGE_ARCHIVE)
            total_pages = len(pages)

            # Generate each page
            for page_num, page_posts in enumerate(pages, start=1):
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

    def _generate_tag_pages(self, posts: list[Post]) -> None:
        """Generate pages for each tag with pagination."""
        # Group posts by tag (case-insensitive)
        # Key is lowercase tag, value is (display_name, posts)
        posts_by_tag: dict[str, tuple[str, list[Post]]] = {}
        for post in posts:
            if post.tags:
                for tag in post.tags:
                    tag_lower = tag.lower()
                    if tag_lower not in posts_by_tag:
                        # Store the first occurrence as the display name
                        posts_by_tag[tag_lower] = (tag, [])
                    posts_by_tag[tag_lower][1].append(post)

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
            pages = paginate_posts(tag_posts, self.POSTS_PER_PAGE_TAG)
            total_pages = len(pages)

            context = self._get_global_context()

            # Generate each page
            for page_num, page_posts in enumerate(pages, start=1):
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

    def _generate_category_pages(self, posts: list[Post]) -> None:
        """Generate pages for each category with pagination."""
        # Group posts by category (case-insensitive)
        # Key is lowercase category, value is (display_name, posts)
        posts_by_category: dict[str, tuple[str, list[Post]]] = {}
        for post in posts:
            if post.category:
                category_lower = post.category.lower()
                if category_lower not in posts_by_category:
                    # Store the first occurrence as the display name
                    posts_by_category[category_lower] = (post.category, [])
                posts_by_category[category_lower][1].append(post)

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
            pages = paginate_posts(category_posts, self.POSTS_PER_PAGE_CATEGORY)
            total_pages = len(pages)

            context = self._get_global_context()

            # Generate each page
            for page_num, page_posts in enumerate(pages, start=1):
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

    def _copy_static_assets(self) -> None:
        """Copy static assets (CSS, JS, images) to output directory."""
        static_dir = self.templates_dir / "static"
        if static_dir.exists():
            output_static = self.output_dir / "static"
            if output_static.exists():
                shutil.rmtree(output_static)
            shutil.copytree(static_dir, output_static)
            print(f"Copied static assets from {static_dir}")

    def _copy_attachments(self) -> None:
        """Copy post attachments (images, files, etc.) from content directory to output directory."""
        if not self.content_dir.exists():
            print(f"Warning: Content directory does not exist: {self.content_dir}")
            return

        # Count how many attachments we copy
        attachment_count = 0
        failed_count = 0

        # Recursively copy all non-markdown files from the content directory
        for file_path in self.content_dir.rglob("*"):
            # Skip markdown files and directories
            if file_path.is_file() and file_path.suffix.lower() != ".md":
                try:
                    # Calculate relative path to preserve directory structure
                    relative_path = file_path.relative_to(self.content_dir)
                    output_path = self.output_dir / relative_path

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
            print(f"Copied {attachment_count} attachment(s) from {self.content_dir}")
        else:
            print(f"No attachments found in {self.content_dir}")

        if failed_count > 0:
            print(f"Warning: Failed to copy {failed_count} attachment(s)")
