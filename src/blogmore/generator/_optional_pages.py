"""Mixin providing optional-feature page generation for
[`SiteGenerator`][blogmore.generator.site.SiteGenerator].

Covers feeds, search, statistics, calendar, graph, and sitemap output.
"""

from typing import TYPE_CHECKING

from blogmore.backlinks import Backlink
from blogmore.calendar import CalendarYear, build_calendar
from blogmore.clean_url import make_url_clean
from blogmore.feeds import BlogFeedGenerator
from blogmore.generator.constants import CATEGORY_DIR, TAG_DIR
from blogmore.graph import GraphData, build_graph_data
from blogmore.parser import Page, Post, post_sort_key
from blogmore.search import write_search_index
from blogmore.sitemap import write_sitemap
from blogmore.stats import BlogStats, compute_blog_stats

if TYPE_CHECKING:
    from blogmore.renderer import TemplateRenderer
    from blogmore.site_config import SiteConfig


class _OptionalPagesMixin:
    """Mixin that generates optional-feature pages (feeds, search, stats, calendar, graph).

    This mixin is intended to be composed into
    [`SiteGenerator`][blogmore.generator.site.SiteGenerator] via
    [`_PagesMixin`][blogmore.generator._pages._PagesMixin].  It expects
    the host class to provide the following instance attributes:

    - `site_config` ([`SiteConfig`][blogmore.site_config.SiteConfig])
    - `renderer` ([`TemplateRenderer`][blogmore.renderer.TemplateRenderer])
    - `_extras_html_paths` (`frozenset[str]`)
    """

    site_config: "SiteConfig"
    renderer: "TemplateRenderer"
    _extras_html_paths: frozenset[str]

    def _generate_feeds(self, posts: list[Post]) -> None:
        """Generate RSS and Atom feeds.

        Args:
            posts: List of all posts
        """
        feed_gen = BlogFeedGenerator(
            output_dir=self.site_config.output_dir,
            site_title=self.site_config.site_title,
            site_url=self.site_config.site_url,
            max_posts=self.site_config.posts_per_feed,
        )

        # Generate main index feeds
        feed_gen.generate_index_feeds(posts)

        # Generate category feeds
        posts_by_category = self._group_posts_by_category(posts)  # type: ignore[attr-defined]
        # Sort posts by date for each category
        for _category_lower, (
            _category_display,
            category_posts,
        ) in posts_by_category.items():
            category_posts.sort(key=post_sort_key, reverse=True)

        feed_gen.generate_category_feeds(posts_by_category)

    def _generate_search_index(self, posts: list[Post]) -> None:
        """Generate the search index JSON file.

        Args:
            posts: List of all posts to index.
        """
        write_search_index(posts, self.site_config.output_dir)

    def _generate_search_page(self, pages: list[Page]) -> None:
        """Generate the search page.

        Args:
            pages: List of static pages (for the sidebar navigation).
        """
        context = self._get_global_context()  # type: ignore[attr-defined]
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.search_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        search_url = self._get_search_url()  # type: ignore[attr-defined]
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{search_url}"
                if self.site_config.site_url
                else search_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)  # type: ignore[attr-defined]
        html = self.renderer.render_search_page(**context)
        self._write_html(output_path, html)  # type: ignore[attr-defined]

    def _generate_stats_page(
        self,
        posts: list[Post],
        pages: list[Page],
        backlink_map: "dict[str, list[Backlink]] | None" = None,
    ) -> None:
        """Generate the blog statistics page.

        Args:
            posts: All published posts; used to compute statistics.
            pages: List of static pages (for the sidebar navigation).
            backlink_map: Optional mapping from post URL to list of
                [`Backlink`][blogmore.backlinks.Backlink] objects.  When provided,
                the statistics page includes a "Top Internal Links" section.
        """
        context = self._get_global_context()  # type: ignore[attr-defined]
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.stats_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        stats_url = self._get_stats_url()  # type: ignore[attr-defined]
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{stats_url}"
                if self.site_config.site_url
                else stats_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)  # type: ignore[attr-defined]
        blog_stats: BlogStats = compute_blog_stats(
            posts, self.site_config.site_url, backlink_map
        )
        html = self.renderer.render_stats_page(stats=blog_stats, **context)
        self._write_html(output_path, html)  # type: ignore[attr-defined]

    def _generate_calendar_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the calendar view page.

        Args:
            posts: All published posts; used to populate the calendar grid.
            pages: List of static pages (for the sidebar navigation).
        """
        context = self._get_global_context()  # type: ignore[attr-defined]
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.calendar_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        calendar_url = self._get_calendar_url()  # type: ignore[attr-defined]
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{calendar_url}"
                if self.site_config.site_url
                else calendar_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)  # type: ignore[attr-defined]
        # Determine page1_suffix for archive URL construction.  When
        # clean_urls is enabled, strip any index filename (e.g. "index.html")
        # so that calendar links to year/month/day archives end with a
        # trailing slash instead of "/index.html".
        page1_suffix = self.site_config.page_1_path.lstrip("/")
        if self.site_config.clean_urls:
            page1_suffix = make_url_clean(f"/{page1_suffix}").lstrip("/")
        calendar_years: list[CalendarYear] = build_calendar(
            posts, page1_suffix, forward=self.site_config.forward_calendar
        )
        html = self.renderer.render_calendar_page(
            calendar_years=calendar_years, **context
        )
        self._write_html(output_path, html)  # type: ignore[attr-defined]

    def _generate_graph_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the post-relationship graph page.

        Args:
            posts: All published posts; used to build graph nodes and edges.
            pages: List of static pages (for the sidebar navigation).
        """
        context = self._get_global_context()  # type: ignore[attr-defined]
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.graph_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        graph_url = self._get_graph_url()  # type: ignore[attr-defined]
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{graph_url}"
                if self.site_config.site_url
                else graph_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)  # type: ignore[attr-defined]
        graph_data: GraphData = build_graph_data(
            posts,
            tag_dir=TAG_DIR,
            category_dir=CATEGORY_DIR,
            site_url=self.site_config.site_url,
        )
        html = self.renderer.render_graph_page(
            graph_data_json=graph_data.to_json(), **context
        )
        self._write_html(output_path, html)  # type: ignore[attr-defined]

    def _remove_stale_search_files(self) -> None:
        """Remove search-related files left over from a previous build.

        When search is disabled, any search page (at the configured
        ``search_path`` or the default ``search.html``) and
        ``search_index.json`` that may have been written by an earlier
        build that had search enabled are deleted so they do not appear
        in the output directory.
        """
        # Always remove search_index.json (fixed location).
        stale_json = self.site_config.output_dir / "search_index.json"
        if stale_json.exists():
            stale_json.unlink()

        # Remove the search page at the configured path.
        stale_page = (
            self.site_config.output_dir / self.site_config.search_path.lstrip("/")
        ).resolve()
        if stale_page.exists():
            stale_page.unlink()

        # Also remove the default search.html location for backward
        # compatibility (in case the user previously used the default path).
        default_page = (self.site_config.output_dir / "search.html").resolve()
        if default_page.exists() and default_page != stale_page:
            default_page.unlink()

    def _generate_sitemap(self) -> None:
        """Generate the XML sitemap file.

        Writes ``sitemap.xml`` to the root of the output directory,
        containing an entry for every generated HTML page except the
        configured search page and any HTML files copied verbatim from
        the ``extras`` directory.
        """
        write_sitemap(
            self.site_config.output_dir,
            self.site_config.site_url,
            clean_urls=self.site_config.clean_urls,
            search_path=self.site_config.search_path,
            extra_excluded_paths=self._extras_html_paths,
            extra_urls=self.site_config.sitemap_extras,
        )


### _optional_pages.py ends here
