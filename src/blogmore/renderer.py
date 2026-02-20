"""Template rendering using Jinja2."""

import datetime as dt
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jinja2 import (
    BaseLoader,
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
    select_autoescape,
)
from markupsafe import Markup

from blogmore.parser import Page, Post


class TemplateRenderer:
    """Render blog content using Jinja2 templates."""

    def __init__(
        self,
        templates_dir: Path | None = None,
        extra_stylesheets: list[str] | None = None,
        site_url: str | None = None,
    ) -> None:
        """Initialize the renderer with a templates directory.

        Args:
            templates_dir: Optional path to a directory containing custom Jinja2 templates.
                          If not provided, uses bundled templates. If provided, custom
                          templates take precedence but fall back to bundled templates.
            extra_stylesheets: Optional list of URLs for additional stylesheets to include
            site_url: Optional base URL of the site for determining internal vs external links
        """
        self.templates_dir = templates_dir
        self.extra_stylesheets = extra_stylesheets or []
        self.site_url = site_url

        # Parse the site URL to get the domain for link checking
        self.site_domain: str | None
        if site_url:
            parsed = urlparse(site_url)
            self.site_domain = parsed.netloc.lower()
        else:
            self.site_domain = None

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
        self.env.filters["is_external_link"] = self._is_external_link

    @staticmethod
    def _format_date(date: dt.datetime | None) -> Markup:
        """Format a datetime object as HTML with archive links.

        The date portion is rendered as
        ``<a href="/{year}/">{year}</a>-<a href="/{year}/{mm}/">{mm}</a>-<a href="/{year}/{mm}/{dd}/">{dd}</a>``
        so each component links to the corresponding archive page.

        Args:
            date: The datetime to format.

        Returns:
            Markup containing the formatted date HTML, or empty Markup if date is None.
        """
        if date is None:
            return Markup("")

        year = date.year
        month = date.month
        day = date.day

        year_link = Markup(f'<a href="/{year}/">{year}</a>')
        month_link = Markup(f'<a href="/{year}/{month:02d}/">{month:02d}</a>')
        day_link = Markup(f'<a href="/{year}/{month:02d}/{day:02d}/">{day:02d}</a>')

        time_str = date.strftime("%H:%M:%S")
        formatted = Markup(f"{year_link}-{month_link}-{day_link} {time_str}")

        # Add timezone information if available
        if date.tzinfo is not None:
            # Get timezone name or offset
            tz_str = date.strftime("%Z")
            if tz_str:
                formatted = Markup(f"{formatted} {tz_str}")
            else:
                # If %Z doesn't work, use the offset
                tz_offset = date.strftime("%z")
                if tz_offset:
                    # Format as UTC+HH:MM or UTC-HH:MM
                    formatted = Markup(
                        f"{formatted} UTC{tz_offset[0]}{tz_offset[1:3]}:{tz_offset[3:5]}"
                    )

        return formatted

    def _is_external_link(self, href: str) -> bool:
        """Determine if a link is external.

        Args:
            href: The href attribute value

        Returns:
            True if the link is external, False otherwise
        """
        # Skip empty hrefs
        if not href:
            return False

        # Relative links (starting with /, #, or no scheme) are internal
        if href.startswith("/") or href.startswith("#"):
            return False

        # Parse the URL
        parsed = urlparse(href)

        # If there's no scheme or netloc, it's a relative link (internal)
        if not parsed.scheme and not parsed.netloc:
            return False

        # If we have a site domain, check if the link matches
        if self.site_domain:
            link_domain = parsed.netloc.lower()
            # If domains match, it's internal
            if (
                link_domain == self.site_domain
                or link_domain == f"www.{self.site_domain}"
            ):
                return False

        # All other links with schemes are external
        return True

    def render_post(self, post: Post, **context: Any) -> str:
        """Render a single blog post.

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
        """Render a single static page.

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
        """Render the blog index/home page.

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
        """Render the blog archive page.

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
        """Render a tag page showing posts with a specific tag.

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
        """Render a category page showing posts in a specific category.

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
        """Render the tags page showing all tags as a word cloud.

        Args:
            tags: List of tag dictionaries
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
        """Render the categories page showing all categories as a word cloud.

        Args:
            categories: List of category dictionaries
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

    def render_search_page(self, **context: Any) -> str:
        """Render the search page.

        Args:
            **context: Context variables to pass to the template.

        Returns:
            Rendered HTML string.
        """
        template = self.env.get_template("search.html")
        return template.render(extra_stylesheets=self.extra_stylesheets, **context)

    def render_template(self, template_name: str, **context: Any) -> str:
        """Render an arbitrary template.

        Args:
            template_name: Name of the template file
            **context: Context variables to pass to the template

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template(template_name)
        return template.render(extra_stylesheets=self.extra_stylesheets, **context)
