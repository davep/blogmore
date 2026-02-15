"""Template rendering using Jinja2."""

from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from blogmore.parser import Post


class TemplateRenderer:
    """Render blog content using Jinja2 templates."""

    def __init__(self, templates_dir: Path) -> None:
        """
        Initialize the renderer with a templates directory.

        Args:
            templates_dir: Path to the directory containing Jinja2 templates
        """
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Add custom filters
        self.env.filters["format_date"] = self._format_date

    @staticmethod
    def _format_date(date: datetime | None, fmt: str = "%B %d, %Y") -> str:
        """
        Format a datetime object.

        Args:
            date: The datetime to format
            fmt: The format string

        Returns:
            Formatted date string or empty string if date is None
        """
        if date is None:
            return ""
        return date.strftime(fmt)

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
        return template.render(post=post, **context)

    def render_index(self, posts: list[Post], **context: Any) -> str:
        """
        Render the blog index/home page.

        Args:
            posts: List of Post objects to display
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template("index.html")
        return template.render(posts=posts, **context)

    def render_archive(self, posts: list[Post], **context: Any) -> str:
        """
        Render the blog archive page.

        Args:
            posts: List of Post objects to display
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template("archive.html")
        return template.render(posts=posts, **context)

    def render_tag_page(self, tag: str, posts: list[Post], **context: Any) -> str:
        """
        Render a tag page showing posts with a specific tag.

        Args:
            tag: The tag to display posts for
            posts: List of Post objects with this tag
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template("tag.html")
        return template.render(tag=tag, posts=posts, **context)

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
        return template.render(**context)
