"""Static site generator for blog content."""

import datetime as dt
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from blogmore.parser import Post, PostParser
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


class SiteGenerator:
    """Generate a static blog site from markdown posts."""

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
        output_path = self.output_dir / f"{post.slug}.html"
        output_path.write_text(html, encoding="utf-8")

    def _generate_index_page(self, posts: list[Post]) -> None:
        """Generate the main index page."""
        context = self._get_global_context()
        html = self.renderer.render_index(posts, **context)
        output_path = self.output_dir / "index.html"
        output_path.write_text(html, encoding="utf-8")

    def _generate_archive_page(self, posts: list[Post]) -> None:
        """Generate the archive page."""
        context = self._get_global_context()
        html = self.renderer.render_archive(posts, **context)
        output_path = self.output_dir / "archive.html"
        output_path.write_text(html, encoding="utf-8")

    def _generate_tag_pages(self, posts: list[Post]) -> None:
        """Generate pages for each tag."""
        # Group posts by tag
        posts_by_tag: dict[str, list[Post]] = defaultdict(list)
        for post in posts:
            if post.tags:
                for tag in post.tags:
                    posts_by_tag[tag].append(post)

        # Create tag directory
        tag_dir = self.output_dir / "tags"
        tag_dir.mkdir(exist_ok=True)

        # Generate a page for each tag
        for tag, tag_posts in posts_by_tag.items():
            # Sort tag posts by date (newest first)
            # Handle timezone-aware and naive datetimes
            def get_sort_key(post: Post) -> float:
                if post.date is None:
                    return 0.0
                if post.date.tzinfo:
                    return post.date.timestamp()
                return post.date.replace(tzinfo=dt.UTC).timestamp()

            tag_posts.sort(key=get_sort_key, reverse=True)
            context = self._get_global_context()
            html = self.renderer.render_tag_page(tag, tag_posts, **context)
            # Sanitize tag for filename
            safe_tag = sanitize_for_url(tag)
            output_path = tag_dir / f"{safe_tag}.html"
            output_path.write_text(html, encoding="utf-8")

    def _generate_category_pages(self, posts: list[Post]) -> None:
        """Generate pages for each category."""
        # Group posts by category
        posts_by_category: dict[str, list[Post]] = defaultdict(list)
        for post in posts:
            if post.category:
                posts_by_category[post.category].append(post)

        # Create category directory
        category_dir = self.output_dir / "category"
        category_dir.mkdir(exist_ok=True)

        # Generate a page for each category
        for category, category_posts in posts_by_category.items():
            # Sort category posts by date (newest first)
            # Handle timezone-aware and naive datetimes
            def get_sort_key(post: Post) -> float:
                if post.date is None:
                    return 0.0
                if post.date.tzinfo:
                    return post.date.timestamp()
                return post.date.replace(tzinfo=dt.UTC).timestamp()

            category_posts.sort(key=get_sort_key, reverse=True)
            context = self._get_global_context()
            html = self.renderer.render_category_page(
                category, category_posts, **context
            )
            # Sanitize category for filename
            safe_category = sanitize_for_url(category)
            output_path = category_dir / f"{safe_category}.html"
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
            return

        # Count how many attachments we copy
        attachment_count = 0

        # Copy all non-markdown files from the content directory
        for file_path in self.content_dir.iterdir():
            # Skip markdown files and directories
            if file_path.is_file() and file_path.suffix.lower() != ".md":
                try:
                    # Copy to output directory with the same name
                    output_path = self.output_dir / file_path.name
                    shutil.copy2(file_path, output_path)
                    attachment_count += 1
                except (OSError, PermissionError) as e:
                    print(f"Warning: Failed to copy attachment {file_path}: {e}")
                    continue

        if attachment_count > 0:
            print(f"Copied {attachment_count} attachment(s) from {self.content_dir}")
