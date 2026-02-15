"""Markdown parser with frontmatter support for blog posts."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import frontmatter
import markdown


@dataclass
class Post:
    """Represents a blog post with metadata and content."""

    path: Path
    title: str
    content: str
    html_content: str
    date: datetime | None = None
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
        return f"/{self.slug}.html"


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
            ValueError: If required metadata is missing
        """
        if not path.exists():
            raise FileNotFoundError(f"Post file not found: {path}")

        # Parse frontmatter
        post_data = frontmatter.load(path)

        # Extract metadata
        title = post_data.get("title")
        if not title:
            raise ValueError(f"Post missing required 'title' in frontmatter: {path}")

        # Parse date if present
        date = None
        if "date" in post_data:
            date_value = post_data["date"]
            if isinstance(date_value, datetime):
                date = date_value
            elif isinstance(date_value, str):
                # Try to parse common date formats
                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        date = datetime.strptime(date_value, fmt)
                        break
                    except ValueError:
                        continue

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
            tags=tags,
            draft=draft,
            metadata=dict(post_data.metadata),
        )

    def parse_directory(self, directory: Path, include_drafts: bool = False) -> list[Post]:
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
        posts.sort(key=lambda p: p.date or datetime.min, reverse=True)
        return posts
