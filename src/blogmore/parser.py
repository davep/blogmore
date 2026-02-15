"""Markdown parser with frontmatter support for blog posts."""

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import frontmatter  # type: ignore[import-untyped]
import markdown
import yaml


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


@dataclass
class Post:
    """Represents a blog post with metadata and content."""

    path: Path
    title: str
    content: str
    html_content: str
    date: dt.datetime | None = None
    category: str | None = None
    tags: list[str] | None = None
    draft: bool = False
    metadata: dict[str, Any] | None = None

    @property
    def slug(self) -> str:
        """Generate a URL slug from the post filename."""
        return self.path.stem

    @property
    def url(self) -> str:
        """Generate the URL path for the post."""
        if self.date:
            # Extract date components
            year = self.date.year
            month = f"{self.date.month:02d}"
            day = f"{self.date.day:02d}"
            # Remove date prefix from slug if present
            slug = self.slug
            # Remove YYYY-MM-DD- prefix if it exists
            import re
            slug = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', slug)
            return f"/{year}/{month}/{day}/{slug}.html"
        # Fallback for posts without dates
        return f"/{self.slug}.html"

    @property
    def safe_category(self) -> str | None:
        """Get the category sanitized for use in URLs and filenames."""
        if self.category:
            return sanitize_for_url(self.category)
        return None

    def safe_tags(self) -> list[str]:
        """Get tags sanitized for use in URLs and filenames."""
        if self.tags:
            return [sanitize_for_url(tag) for tag in self.tags]
        return []


class PostParser:
    """Parse markdown files with frontmatter into Post objects."""

    def __init__(self) -> None:
        """Initialize the parser with markdown extensions."""
        self.markdown = markdown.Markdown(
            extensions=[
                "meta",
                "fenced_code",
                "codehilite",
                "tables",
                "toc",
                "footnotes",
            ]
        )

    def parse_file(self, path: Path) -> Post:
        """
        Parse a markdown file with frontmatter.

        Args:
            path: Path to the markdown file

        Returns:
            A Post object with parsed metadata and content

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If required metadata is missing or YAML is malformed
        """
        if not path.exists():
            raise FileNotFoundError(f"Post file not found: {path}")

        # Parse frontmatter
        try:
            post_data = frontmatter.load(path)
        except yaml.scanner.ScannerError as e:
            # Provide a helpful error message for YAML syntax errors
            raise ValueError(
                f"YAML syntax error in frontmatter of {path}:\n"
                f"  {e}\n\n"
                f"Common causes:\n"
                f"  - Unquoted colons in values (e.g., 'title: My post: the sequel')\n"
                f"  - Missing quotes around special characters\n"
                f"  - Incorrect indentation\n\n"
                f"Fix: Wrap values containing colons or special characters in quotes:\n"
                f'  title: "My post: the sequel"'
            ) from e
        except Exception as e:
            raise ValueError(f"Error parsing frontmatter in {path}: {e}") from e

        # Extract metadata
        title = post_data.get("title")
        if not title:
            raise ValueError(f"Post missing required 'title' in frontmatter: {path}")

        # Parse date if present
        date = None
        if "date" in post_data:
            date_value = post_data["date"]
            if isinstance(date_value, dt.datetime):
                date = date_value
            elif isinstance(date_value, dt.date):
                # Convert date to datetime
                date = dt.datetime.combine(date_value, dt.time())
            elif isinstance(date_value, str):
                # Try to parse common date formats, including timezone-aware formats
                date_formats = [
                    "%Y-%m-%d %H:%M:%S%z",  # With timezone offset
                    "%Y-%m-%dT%H:%M:%S%z",  # ISO format with timezone
                    "%Y-%m-%d %H:%M:%S",  # Without timezone
                    "%Y-%m-%dT%H:%M:%S",  # ISO format without timezone
                    "%Y-%m-%d",  # Date only
                ]
                for fmt in date_formats:
                    try:
                        date = dt.datetime.strptime(date_value, fmt)
                        break
                    except ValueError:
                        continue

                # If we still couldn't parse it, try with python-dateutil if available
                if date is None:
                    try:
                        from dateutil import parser as dateutil_parser

                        date = dateutil_parser.parse(date_value)
                    except (ImportError, ValueError):
                        pass

        # Extract category
        category = post_data.get("category")
        if category and isinstance(category, str):
            category = category.strip()

        # Extract tags
        tags = post_data.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",")]

        # Check draft status
        draft = post_data.get("draft", False)

        # Convert markdown to HTML
        html_content = self.markdown.convert(post_data.content)

        # Reset markdown parser for next use
        self.markdown.reset()

        return Post(
            path=path,
            title=title,
            content=post_data.content,
            html_content=html_content,
            date=date,
            category=category,
            tags=tags,
            draft=draft,
            metadata=dict(post_data.metadata),
        )

    def parse_directory(
        self, directory: Path, include_drafts: bool = False
    ) -> list[Post]:
        """
        Parse all markdown files in a directory.

        Args:
            directory: Directory containing markdown files
            include_drafts: Whether to include posts marked as drafts

        Returns:
            List of Post objects sorted by date (newest first)
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        posts = []
        for md_file in directory.glob("*.md"):
            try:
                post = self.parse_file(md_file)
                if not post.draft or include_drafts:
                    posts.append(post)
            except (ValueError, FileNotFoundError) as e:
                print(f"Warning: Skipping {md_file}: {e}")
                continue

        # Sort by date (newest first)
        # Handle timezone-aware and naive datetimes by converting to UTC timestamp
        def get_sort_key(post: Post) -> float:
            if post.date is None:
                return 0.0  # Posts without dates sort to the end
            # Convert to UTC timestamp for comparison
            if post.date.tzinfo:
                return post.date.timestamp()
            return post.date.replace(tzinfo=dt.UTC).timestamp()

        posts.sort(key=get_sort_key, reverse=True)
        return posts
