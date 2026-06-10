"""Template rendering using Jinja2."""

import datetime as dt
import re
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

from blogmore.markdown.external_links import is_external_link
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
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters["format_date"] = self._format_date
        self.env.filters["format_date_plain"] = self._format_date_plain
        self.env.filters["is_external_link"] = self._is_external_link
        self.env.filters["shift_headings"] = self._shift_headings
        self.env.filters["format_commas"] = self._format_commas

        # Provide default values for pagination context variables so that
        # templates rendering without a full generator context (e.g. tests)
        # do not raise UndefinedError.
        self.env.globals["pagination_page_urls"] = []
        self.env.globals["pagination_page1_suffix"] = "index.html"

    @staticmethod
    def _format_date(date: dt.datetime | None) -> Markup:
        """Format a datetime object as HTML with archive links.

        The date portion is rendered as separate links for the year, month, and day
        (separated by dashes), with each link containing an appropriate aria-label
        pointing to the corresponding archive page.

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

        year_label = f"Archive for {year}"
        month_name = date.strftime("%B")
        month_label = f"Archive for {month_name} {year}"
        day_label = f"Archive for {month_name} {day}, {year}"

        year_link = Markup(f'<a href="/{year}/" aria-label="{year_label}">{year}</a>')
        month_link = Markup(
            f'<a href="/{year}/{month:02d}/" aria-label="{month_label}">{month:02d}</a>'
        )
        day_link = Markup(
            f'<a href="/{year}/{month:02d}/{day:02d}/" aria-label="{day_label}">{day:02d}</a>'
        )

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

    @staticmethod
    def _format_date_plain(date: dt.datetime | None) -> Markup:
        """Format a datetime object as plain text without archive links.

        Formats the date and time components as a plain string with no
        hyperlinks.  Used for the modified date display where linking to
        the archive would be misleading or redundant.

        Args:
            date: The datetime to format.

        Returns:
            Markup containing the formatted date as plain text, or empty Markup if date is None.
        """
        if date is None:
            return Markup("")

        time_str = date.strftime("%Y-%m-%d %H:%M:%S")
        formatted = Markup(time_str)

        # Add timezone information if available
        if date.tzinfo is not None:
            tz_str = date.strftime("%Z")
            if tz_str:
                formatted = Markup(f"{formatted} {tz_str}")
            else:
                tz_offset = date.strftime("%z")
                if tz_offset:
                    formatted = Markup(
                        f"{formatted} UTC{tz_offset[0]}{tz_offset[1:3]}:{tz_offset[3:5]}"
                    )

        return formatted

    @staticmethod
    def _format_commas(value: Any) -> str:
        """Format a numeric value or string with commas for thousands.

        Args:
            value: The value to format.

        Returns:
            A string with commas if the value is numeric, otherwise the string
            representation of the value.
        """
        if value is None:
            return ""
        try:
            if isinstance(value, (int, float)):
                return f"{value:,}"
            if isinstance(value, str):
                if value.isdigit():
                    return f"{int(value):,}"
                try:
                    val = float(value)
                    if val.is_integer():
                        return f"{int(val):,}"
                    return f"{val:,}"
                except ValueError:
                    pass
            return str(value)
        except Exception:
            return str(value)

    def _is_external_link(self, href: str) -> bool:
        """Determine if a link is external.

        Args:
            href: The href attribute value.

        Returns:
            True if the link is external, False otherwise.
        """
        # Skip empty hrefs
        if not href:
            return False
        return is_external_link(href, self.site_domain)

    @staticmethod
    def _shift_headings(html: str, shift: int = 1) -> str:
        """Shift HTML heading levels (h1-h6) by a given amount.

        Args:
            html: The HTML content to modify.
            shift: The number of levels to shift headings by. Positive values
                make headings smaller (e.g. h1 -> h2), negative values make
                them larger. Results are clamped to the h1-h6 range.

        Returns:
            The HTML with heading levels shifted.
        """
        if shift == 0:
            return html

        def shift_tag(match: re.Match[str]) -> str:
            prefix, level_str = match.groups()
            level = int(level_str)
            new_level = max(1, min(6, level + shift))
            return f"<{prefix}{new_level}"

        # Matches <h1, <h2, ..., </h1, </h2, ...
        return re.sub(r"<(/?h)([1-6])", shift_tag, html)

    def render_post(self, post: Post, **context: Any) -> str:
        """Render a single blog post.

        Args:
            post: The Post object to render
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        context["has_mermaid"] = (
            'class="mermaid"' in post.html_content
            or 'class="language-mermaid"' in post.html_content
        )
        context["has_math"] = (
            'class="math-inline"' in post.html_content
            or 'class="math-block"' in post.html_content
        )
        return self.render_template("post.html", post=post, **context)

    def render_page(self, page: Page, **context: Any) -> str:
        """Render a single static page.

        Args:
            page: The Page object to render
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        context["has_mermaid"] = (
            'class="mermaid"' in page.html_content
            or 'class="language-mermaid"' in page.html_content
        )
        context["has_math"] = (
            'class="math-inline"' in page.html_content
            or 'class="math-block"' in page.html_content
        )
        return self.render_template("page.html", page=page, **context)

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
        context["has_mermaid"] = any(
            'class="mermaid"' in p.html_content
            or 'class="language-mermaid"' in p.html_content
            for p in posts
        )
        context["has_math"] = any(
            'class="math-inline"' in p.html_content
            or 'class="math-block"' in p.html_content
            for p in posts
        )
        return self.render_template(
            "index.html",
            posts=posts,
            page=page,
            total_pages=total_pages,
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
        context["has_mermaid"] = any(
            'class="mermaid"' in p.html_content
            or 'class="language-mermaid"' in p.html_content
            for p in posts
        )
        context["has_math"] = any(
            'class="math-inline"' in p.html_content
            or 'class="math-block"' in p.html_content
            for p in posts
        )
        return self.render_template(
            "archive.html",
            posts=posts,
            archive_title=archive_title,
            page=page,
            total_pages=total_pages,
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
        context["has_mermaid"] = any(
            'class="mermaid"' in p.html_content
            or 'class="language-mermaid"' in p.html_content
            for p in posts
        )
        context["has_math"] = any(
            'class="math-inline"' in p.html_content
            or 'class="math-block"' in p.html_content
            for p in posts
        )
        return self.render_template(
            "tag.html",
            tag=tag,
            posts=posts,
            page=page,
            total_pages=total_pages,
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
        context["has_mermaid"] = any(
            'class="mermaid"' in p.html_content
            or 'class="language-mermaid"' in p.html_content
            for p in posts
        )
        context["has_math"] = any(
            'class="math-inline"' in p.html_content
            or 'class="math-block"' in p.html_content
            for p in posts
        )
        return self.render_template(
            "category.html",
            category=category,
            posts=posts,
            page=page,
            total_pages=total_pages,
            **context,
        )

    def render_series_page(
        self,
        series: str,
        posts: list[Post],
        page: int = 1,
        total_pages: int = 1,
        **context: Any,
    ) -> str:
        """Render a series page showing posts in a specific series.

        Args:
            series: The series name to display posts for
            posts: List of Post objects in this series
            page: Current page number (1-indexed)
            total_pages: Total number of pages
            **context: Additional context variables

        Returns:
            Rendered HTML string
        """
        context["has_mermaid"] = any(
            'class="mermaid"' in p.html_content
            or 'class="language-mermaid"' in p.html_content
            for p in posts
        )
        context["has_math"] = any(
            'class="math-inline"' in p.html_content
            or 'class="math-block"' in p.html_content
            for p in posts
        )
        return self.render_template(
            "series.html",
            series=series,
            posts=posts,
            page=page,
            total_pages=total_pages,
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
        return self.render_template(
            "tags.html",
            tags=tags,
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
        return self.render_template(
            "categories.html",
            categories=categories,
            **context,
        )

    def render_search_page(self, **context: Any) -> str:
        """Render the search page.

        Args:
            **context: Context variables to pass to the template.

        Returns:
            Rendered HTML string.
        """
        return self.render_template("search.html", **context)

    def render_stats_page(self, **context: Any) -> str:
        """Render the blog statistics page.

        Args:
            **context: Context variables to pass to the template.  Should
                include a `stats` key containing a
                `blogmore.stats.BlogStats` instance.

        Returns:
            Rendered HTML string.
        """
        return self.render_template("stats.html", **context)

    def render_calendar_page(self, **context: Any) -> str:
        """Render the calendar view page.

        Args:
            **context: Context variables to pass to the template.  Should
                include a `calendar_years` key containing a list of
                `blogmore.calendar.CalendarYear` instances.

        Returns:
            Rendered HTML string.
        """
        return self.render_template("calendar.html", **context)

    def render_graph_page(self, **context: Any) -> str:
        """Render the post-relationship graph page.

        Args:
            **context: Context variables to pass to the template.  Should
                include a `graph_data_json` key containing the serialised
                JSON string produced by
                `blogmore.graph.GraphData.to_json`.

        Returns:
            Rendered HTML string.
        """
        return self.render_template("graph.html", **context)

    def render_series_index_page(
        self,
        series: list[dict[str, Any]],
        **context: Any,
    ) -> str:
        """Render the series index page showing all series and post counts.

        Args:
            series: List of series dictionaries containing name, url, and count.
            **context: Additional context variables.

        Returns:
            Rendered HTML string.
        """
        return self.render_template(
            "series_index.html",
            series=series,
            **context,
        )

    def render_template(self, template_name: str, **context: Any) -> str:
        """Render an arbitrary template.

        Args:
            template_name: Name of the template file
            **context: Context variables to pass to the template

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template(template_name)

        # Ensure defaults for author and third-party variables are present in the context.
        render_context = {
            "show_author": False,
            "default_author": None,
            "default_author_url": None,
            "extra_stylesheets": self.extra_stylesheets,
            "mermaid_script_url": "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs",
            "katex_css_url": "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css",
            "katex_js_url": "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js",
            "mathjax_js_url": "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js",
            "fontawesome_woff2_url": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/webfonts/fa-brands-400.woff2",
            "force_graph_js_url": "https://unpkg.com/force-graph",
            **context,
        }

        return template.render(**render_context)
