"""Template rendering using Jinja2."""

import datetime as dt
from pathlib import Path
from typing import Any

from jinja2 import (
    BaseLoader,
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
    select_autoescape,
)

from blogmore.parser import Page, Post


class TemplateRenderer:
    """Render blog content using Jinja2 templates."""

    def __init__(
        self,
        templates_dir: Path | None = None,
        extra_stylesheets: list[str] | None = None,
    ) -> None:
        """
        Initialize the renderer with a templates directory.

        Args:
            templates_dir: Optional path to a directory containing custom Jinja2 templates.
                          If not provided, uses bundled templates. If provided, custom
                          templates take precedence but fall back to bundled templates.
            extra_stylesheets: Optional list of URLs for additional stylesheets to include
        """
        self.templates_dir = templates_dir
        self.extra_stylesheets = extra_stylesheets or []

        # Set up loaders: custom templates first (if provided), then bundled templates
        loaders: list[BaseLoader] = []
        if templates_dir is not None:
            loaders.append(FileSystemLoader(str(templates_dir)))
        # Always include bundled templates as fallback
        loaders.append(PackageLoader("blogmore", "templates"))

        self.env = Environment(
            loader=ChoiceLoader(loaders),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Add custom filters
        self.env.filters["format_date"] = self._format_date

    @staticmethod
    def _format_date(date: dt.datetime | None, fmt: str = "%B %d, %Y %H:%M:%S") -> str:
        """
        Format a datetime object.

        Args:
            date: The datetime to format
            fmt: The format string (default shows full date and time)

        Returns:
            Formatted date string or empty string if date is None
        """
        if date is None:
            return ""

        # Format the datetime
        formatted = date.strftime(fmt)

        # Add timezone information if available
        if date.tzinfo is not None:
            # Get timezone name or offset
            tz_str = date.strftime("%Z")
            if tz_str:
                formatted += f" {tz_str}"
            else:
                # If %Z doesn't work, use the offset
                tz_offset = date.strftime("%z")
                if tz_offset:
                    # Format as UTC+HH:MM or UTC-HH:MM
                    formatted += f" UTC{tz_offset[0]}{tz_offset[1:3]}:{tz_offset[3:5]}"

        return formatted

    def render_post(self, post: Post, **context: Any) -> str:
        """
        Render a single blog post.

        Args:
            post: The Post object to render
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template("post.html")
        return template.render(
            post=post, extra_stylesheets=self.extra_stylesheets, **context
        )

    def render_page(self, page: Page, **context: Any) -> str:
        """
        Render a single static page.

        Args:
            page: The Page object to render
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template("page.html")
        return template.render(
            page=page, extra_stylesheets=self.extra_stylesheets, **context
        )

    def render_index(
        self,
        posts: list[Post],
        page: int = 1,
        total_pages: int = 1,
        **context: Any,
    ) -> str:
        """
        Render the blog index/home page.

        Args:
            posts: List of Post objects to display
            page: Current page number (1-indexed)
            total_pages: Total number of pages
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template("index.html")
        return template.render(
            posts=posts,
            page=page,
            total_pages=total_pages,
            extra_stylesheets=self.extra_stylesheets,
            **context,
        )

    def render_archive(
        self,
        posts: list[Post],
        archive_title: str | None = None,
        page: int = 1,
        total_pages: int = 1,
        **context: Any,
    ) -> str:
        """
        Render the blog archive page.

        Args:
            posts: List of Post objects to display
            archive_title: Optional title for the archive (e.g., "Posts from 2023")
            page: Current page number (1-indexed)
            total_pages: Total number of pages
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template("archive.html")
        return template.render(
            posts=posts,
            archive_title=archive_title,
            page=page,
            total_pages=total_pages,
            extra_stylesheets=self.extra_stylesheets,
            **context,
        )

    def render_tag_page(
        self,
        tag: str,
        posts: list[Post],
        page: int = 1,
        total_pages: int = 1,
        **context: Any,
    ) -> str:
        """
        Render a tag page showing posts with a specific tag.

        Args:
            tag: The tag to display posts for
            posts: List of Post objects with this tag
            page: Current page number (1-indexed)
            total_pages: Total number of pages
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template("tag.html")
        return template.render(
            tag=tag,
            posts=posts,
            page=page,
            total_pages=total_pages,
            extra_stylesheets=self.extra_stylesheets,
            **context,
        )

    def render_category_page(
        self,
        category: str,
        posts: list[Post],
        page: int = 1,
        total_pages: int = 1,
        **context: Any,
    ) -> str:
        """
        Render a category page showing posts in a specific category.

        Args:
            category: The category to display posts for
            posts: List of Post objects in this category
            page: Current page number (1-indexed)
            total_pages: Total number of pages
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template("category.html")
        return template.render(
            category=category,
            posts=posts,
            page=page,
            total_pages=total_pages,
            extra_stylesheets=self.extra_stylesheets,
            **context,
        )

    def render_tags_page(
        self,
        tags: list[dict[str, Any]],
        **context: Any,
    ) -> str:
        """
        Render the tags page showing all tags as a word cloud.

        Args:
            tags: List of tag dictionaries with keys:
                  - display_name: The tag display name
                  - safe_tag: URL-safe version of the tag
                  - count: Number of posts with this tag
                  - font_size: Font size for word cloud effect
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template("tags.html")
        return template.render(
            tags=tags,
            extra_stylesheets=self.extra_stylesheets,
            **context,
        )

    def render_categories_page(
        self,
        categories: list[dict[str, Any]],
        **context: Any,
    ) -> str:
        """
        Render the categories page showing all categories as a word cloud.

        Args:
            categories: List of category dictionaries with keys:
                  - display_name: The category display name
                  - safe_category: URL-safe version of the category
                  - count: Number of posts with this category
                  - font_size: Font size for word cloud effect
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template("categories.html")
        return template.render(
            categories=categories,
            extra_stylesheets=self.extra_stylesheets,
            **context,
        )

    def render_template(self, template_name: str, **context: Any) -> str:
        """
        Render an arbitrary template.

        Args:
            template_name: Name of the template file
            **context: Context variables to pass to the template

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template(template_name)
        return template.render(extra_stylesheets=self.extra_stylesheets, **context)
