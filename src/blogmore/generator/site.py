"""Main site generator logic."""

import datetime as dt
import shutil
import time
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

import minify_html

from blogmore.backlinks import Backlink, build_backlink_map
from blogmore.calendar import CalendarYear, build_calendar
from blogmore.clean_url import make_url_clean
from blogmore.comment_invite import build_mailto_url, get_invite_email_for_post
from blogmore.feeds import BlogFeedGenerator
from blogmore.fontawesome import FONTAWESOME_CDN_CSS_URL
from blogmore.generator.assets import (
    copy_extras,
    copy_static_assets,
    detect_favicon,
    detect_generated_icons,
    generate_icons,
    prepare_fontawesome_css,
    write_fontawesome_css,
)
from blogmore.generator.context import build_global_context, resolve_sidebar_pages
from blogmore.generator.listing import generate_paginated_listing
from blogmore.generator.paths import (
    build_pagination_page_urls,
    canonical_url_for_path,
    get_asset_url,
    get_configured_url,
    get_pagination_output_path,
    get_pagination_url,
    pagination_prev_next,
    with_cache_bust,
)
from blogmore.generator.utils import paginate_posts
from blogmore.graph import GraphData, build_graph_data
from blogmore.page_path import compute_page_output_path
from blogmore.parser import (
    CUSTOM_404_HTML,
    Page,
    Post,
    PostParser,
    post_sort_key,
    sanitize_for_url,
)
from blogmore.post_path import compute_output_path
from blogmore.renderer import TemplateRenderer
from blogmore.search import write_search_index
from blogmore.site_config import SiteConfig
from blogmore.sitemap import write_sitemap
from blogmore.stats import BlogStats, compute_blog_stats


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

    def __init__(self, site_config: SiteConfig) -> None:
        """Initialize the site generator.

        Args:
            site_config: Configuration for the site to be generated.  The
                [`content_dir`][blogmore.site_config.SiteConfig.content_dir] field must not be `None`.
        """
        if site_config.content_dir is None:
            raise ValueError(
                "site_config.content_dir must be provided for site generation"
            )
        self.site_config = site_config

        # Default to CDN URL; updated during generate() once socials are known
        self._fontawesome_css_url: str = FONTAWESOME_CDN_CSS_URL

        # Cache-busting token; set at the start of each generate() call so all
        # pages in one generation share the same token but successive generations
        # get a fresh one, forcing browsers to re-fetch updated stylesheets.
        self._cache_bust_token: str = ""

        self.parser = PostParser(site_url=site_config.site_url)
        self.renderer = TemplateRenderer(
            site_config.templates_dir,
            site_config.extra_stylesheets,
            site_config.site_url,
        )

        # Relative paths (forward-slash strings) of HTML files that were copied
        # verbatim from the extras directory.  Populated by _copy_extras() and
        # consumed by _generate_sitemap() to exclude those files from the sitemap.
        self._extras_html_paths: frozenset[str] = frozenset()

    @property
    def _content_dir(self) -> Path:
        """Return the content directory as a `Path`, guaranteed non-`None`.

        `__init__` validates that `site_config.content_dir` is not `None`,
        so this property is always safe to call on a constructed instance.

        Returns:
            The resolved content directory path.
        """
        assert self.site_config.content_dir is not None
        return self.site_config.content_dir

    def _get_global_context(self) -> dict[str, Any]:
        """Get the global context available to all templates."""
        return build_global_context(
            self.site_config,
            self._cache_bust_token,
            self._fontawesome_css_url,
            detect_favicon(self.site_config, self._content_dir),
            detect_generated_icons(self.site_config),
            self.TAG_DIR,
            self.CATEGORY_DIR,
        )

    def _canonical_url_for_path(self, output_path: Path) -> str:
        """Compute the fully-qualified canonical URL for a given output file path."""
        return canonical_url_for_path(self.site_config, output_path)

    def _write_html(self, output_path: Path, html: str) -> None:
        """Write an HTML string to a file, minifying it when configured to do so."""
        if self.site_config.minify_html:
            html = minify_html.minify(html, minify_js=False, minify_css=False)
        output_path.write_text(html, encoding="utf-8")

    def _detect_favicon(self) -> str | None:
        """Detect if a favicon file exists."""
        return detect_favicon(self.site_config, self._content_dir)

    def _detect_generated_icons(self) -> bool:
        """Detect if generated platform icons exist."""
        return detect_generated_icons(self.site_config)

    def _generate_icons(self) -> None:
        """Generate icons from a source image if present."""
        generate_icons(self.site_config, self._content_dir)

    def _resolve_sidebar_pages(self, pages: list[Page]) -> list[Page]:
        """Resolve which pages appear in the sidebar."""
        return resolve_sidebar_pages(self.site_config, pages)

    def _copy_extras(self) -> None:
        """Copy extra files from the extras directory."""
        self._extras_html_paths = copy_extras(self.site_config, self._content_dir)

    def _with_cache_bust(self, url: str) -> str:
        """Return a URL with a cache-busting query parameter appended."""
        return with_cache_bust(url, self._cache_bust_token)

    def _get_configured_url(self, path_field_name: str) -> str:
        """Return the URL path for a configured page."""
        return get_configured_url(self.site_config, path_field_name)

    def _get_search_url(self) -> str:
        return self._get_configured_url("search_path")

    def _get_archive_url(self) -> str:
        return self._get_configured_url("archive_path")

    def _get_tags_url(self) -> str:
        return self._get_configured_url("tags_path")

    def _get_categories_url(self) -> str:
        return self._get_configured_url("categories_path")

    def _get_stats_url(self) -> str:
        return self._get_configured_url("stats_path")

    def _get_calendar_url(self) -> str:
        return self._get_configured_url("calendar_path")

    def _get_graph_url(self) -> str:
        return self._get_configured_url("graph_path")

    def _get_asset_url(
        self,
        regular: str,
        minify: bool,
        *,
        cache_bust: bool = True,
    ) -> str:
        return get_asset_url(
            regular, minify, self._cache_bust_token, cache_bust=cache_bust
        )

    def _get_pagination_url(self, base_url: str, page_num: int) -> str:
        return get_pagination_url(self.site_config, base_url, page_num)

    def _build_pagination_page_urls(self, base_url: str, total_pages: int) -> list[str]:
        return build_pagination_page_urls(self.site_config, base_url, total_pages)

    def _get_pagination_output_path(self, base_dir: Path, page_num: int) -> Path:
        return get_pagination_output_path(self.site_config, base_dir, page_num)

    @staticmethod
    def _pagination_prev_next(
        page_num: int,
        page_urls: list[str],
    ) -> tuple[str | None, str | None]:
        return pagination_prev_next(page_num, page_urls)

    def _generate_paginated_listing(
        self,
        post_list: list[Post],
        base_url: str,
        output_dir: Path,
        posts_per_page: int,
        context: dict[str, Any],
        render_func: Callable[[list[Post], int, int], str],
    ) -> None:
        generate_paginated_listing(
            self.site_config,
            post_list,
            base_url,
            output_dir,
            posts_per_page,
            context,
            render_func,
            self._write_html,
            self._canonical_url_for_path,
        )

    def generate(self) -> None:
        """Generate the complete static site."""
        content_dir = self._content_dir

        # Mint a fresh cache-busting token for this generation.
        self._cache_bust_token = str(int(time.time()))

        # Apply cache-busting to any local extra stylesheets.
        extra_stylesheets = self.site_config.extra_stylesheets or []
        self.renderer.extra_stylesheets = [
            with_cache_bust(url, self._cache_bust_token) for url in extra_stylesheets
        ]

        # Clean output directory if requested
        if self.site_config.clean_first and self.site_config.output_dir.exists():
            print(f"Removing output directory: {self.site_config.output_dir}")
            try:
                shutil.rmtree(self.site_config.output_dir)
            except OSError:
                time.sleep(0.1)
                try:
                    shutil.rmtree(self.site_config.output_dir)
                except OSError:
                    shutil.rmtree(self.site_config.output_dir, ignore_errors=True)
                    print(
                        "Warning: Some files could not be removed from output directory"
                    )

        # Parse all pages from the pages subdirectory.
        pages_dir = content_dir / "pages"
        pages = self.parser.parse_pages_directory(pages_dir)
        page_404 = self.parser.parse_404_page(pages_dir)

        # Parse all posts, excluding the pages subdirectory.
        print(f"Parsing posts from {content_dir}...")
        posts = self.parser.parse_directory(
            content_dir,
            include_drafts=self.site_config.include_drafts,
            exclude_dirs=[pages_dir],
        )
        print(f"Found {len(posts)} posts")

        # Apply configured reading-speed to every post.
        for post in posts:
            post.words_per_minute = self.site_config.read_time_wpm

        # Apply default author to posts that don't have one.
        if self.site_config.default_author:
            for post in posts:
                if post.metadata is not None and "author" not in post.metadata:
                    post.metadata["author"] = self.site_config.default_author
        if pages:
            print(f"Found {len(pages)} pages")

        # Resolve the list of pages to display in the sidebar.
        sidebar_pages = resolve_sidebar_pages(self.site_config, pages)

        # Create output directory
        self.site_config.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate icons from source image BEFORE generating HTML pages
        generate_icons(self.site_config, self._content_dir)

        # Prepare the FontAwesome CSS URL.
        fontawesome_css_content, self._fontawesome_css_url = prepare_fontawesome_css(
            self.site_config
        )

        # Resolve page output paths before generating any HTML.
        page_output_paths = self._resolve_page_output_paths(pages)

        # Generate individual post pages
        print("Generating post pages...")
        post_output_paths = self._resolve_post_output_paths(posts)

        # Build the backlink map only when the feature is enabled.
        backlinks_map: dict[str, list[Backlink]] = {}
        if self.site_config.with_backlinks:
            print("Building backlink map...")
            backlinks_map = build_backlink_map(
                posts,
                site_url=self.site_config.site_url,
            )

        generated_paths: set[str] = set()
        for post in posts:
            output_path = post_output_paths[id(post)]
            path_key = str(output_path)
            if path_key in generated_paths:
                continue
            generated_paths.add(path_key)
            self._generate_post_page(
                post, posts, sidebar_pages, output_path, backlinks_map
            )

        # Generate static pages
        if pages:
            print("Generating static pages...")
            for page in pages:
                self._generate_page(page, sidebar_pages, page_output_paths[id(page)])

        # Generate custom 404 page if present
        if page_404 is not None:
            print("Generating custom 404 page...")
            self._generate_404_page(page_404, sidebar_pages)

        # Generate index page
        print("Generating index page...")
        self._generate_index_page(posts, sidebar_pages)

        # Generate archive page
        print("Generating archive page...")
        self._generate_archive_page(posts, sidebar_pages)

        # Generate date-based archive pages
        print("Generating date-based archive pages...")
        self._generate_date_archives(posts, sidebar_pages)

        # Generate tag pages
        print("Generating tag pages...")
        self._generate_tag_pages(posts, sidebar_pages)

        # Generate tags overview page
        print("Generating tags overview page...")
        self._generate_tags_page(posts, sidebar_pages)

        # Generate category pages
        print("Generating category pages...")
        self._generate_category_pages(posts, sidebar_pages)

        # Generate categories overview page
        print("Generating categories overview page...")
        self._generate_categories_page(posts, sidebar_pages)

        # Generate feeds
        print("Generating RSS and Atom feeds...")
        self._generate_feeds(posts)

        # Generate search index and search page (only when enabled)
        if self.site_config.with_search:
            print("Generating search index and search page...")
            write_search_index(posts, self.site_config.output_dir)
            self._generate_search_page(sidebar_pages)
        else:
            self._remove_stale_search_files()

        # Generate statistics page (only when enabled)
        if self.site_config.with_stats:
            print("Generating blog statistics page...")
            self._generate_stats_page(
                posts,
                sidebar_pages,
                backlinks_map if self.site_config.with_backlinks else None,
            )

        # Generate calendar page (only when enabled)
        if self.site_config.with_calendar:
            print("Generating calendar page...")
            self._generate_calendar_page(posts, sidebar_pages)

        # Generate graph page (only when enabled)
        if self.site_config.with_graph:
            print("Generating graph page...")
            self._generate_graph_page(posts, sidebar_pages)

        # Copy static assets if they exist
        copy_static_assets(self.site_config)

        # Write the optimised FontAwesome CSS file.
        if fontawesome_css_content is not None:
            write_fontawesome_css(self.site_config, fontawesome_css_content)

        # Copy extra files from extras directory
        self._extras_html_paths = copy_extras(self.site_config, self._content_dir)

        # Generate XML sitemap (only when enabled)
        if self.site_config.with_sitemap:
            print("Generating XML sitemap...")
            self._generate_sitemap()

        print(f"Site generation complete! Output: {self.site_config.output_dir}")

    def _resolve_post_output_paths(self, posts: list[Post]) -> dict[int, Path]:
        """Resolve the output path for every post and detect path clashes."""
        post_output_paths: dict[int, Path] = {}
        path_to_post_ids: dict[str, list[int]] = defaultdict(list)
        post_by_id: dict[int, Post] = {id(post): post for post in posts}

        for post in posts:
            output_path = compute_output_path(
                self.site_config.output_dir, post, self.site_config.post_path
            )
            post_output_paths[id(post)] = output_path

            relative = output_path.relative_to(self.site_config.output_dir)
            url_path = "/" + relative.as_posix()

            if self.site_config.clean_urls:
                url_path = make_url_clean(url_path)

            post.url_path = url_path
            path_to_post_ids[str(output_path)].append(id(post))

        # Detect and warn about path clashes.
        for path_str, clashing_ids in path_to_post_ids.items():
            if len(clashing_ids) > 1:
                clashing_posts = [post_by_id[pid] for pid in clashing_ids]
                winner = clashing_posts[0]
                losers = clashing_posts[1:]
                print(
                    "\nWARNING: Post path clash detected!  "
                    "Multiple posts would be written to the same output file."
                )
                print(f"  Output path : {path_str}")
                print(f"  Winner (newest) : '{winner.title}'")
                for loser in losers:
                    print(f"  Ignored (older): '{loser.title}'")
                print()

        return post_output_paths

    def _generate_post_page(
        self,
        post: Post,
        all_posts: list[Post],
        pages: list[Page],
        output_path: Path,
        backlinks_map: "dict[str, list[Backlink]] | None" = None,
    ) -> None:
        """Generate a single post page."""
        context = self._get_global_context()
        context["all_posts"] = all_posts
        context["pages"] = pages
        context["backlinks"] = backlinks_map.get(post.url, []) if backlinks_map else []

        invite_email = get_invite_email_for_post(
            post,
            self.site_config.invite_comments,
            self.site_config.invite_comments_to,
        )
        context["invite_comments_mailto"] = (
            build_mailto_url(invite_email, post.title) if invite_email else None
        )

        try:
            current_index = all_posts.index(post)
            context["prev_post"] = (
                all_posts[current_index + 1]
                if current_index + 1 < len(all_posts)
                else None
            )
            context["next_post"] = (
                all_posts[current_index - 1] if current_index > 0 else None
            )
        except ValueError:
            context["prev_post"] = None
            context["next_post"] = None

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{post.url}"
                if self.site_config.site_url
                else post.url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)
        html = self.renderer.render_post(post, **context)
        self._write_html(output_path, html)

    def _resolve_page_output_paths(self, pages: list[Page]) -> dict[int, Path]:
        """Resolve the output path for every static page."""
        page_output_paths: dict[int, Path] = {}
        for page in pages:
            output_path = compute_page_output_path(
                self.site_config.output_dir, page, self.site_config.page_path
            )
            page_output_paths[id(page)] = output_path
            relative = output_path.relative_to(self.site_config.output_dir)
            url_path = "/" + relative.as_posix()
            if self.site_config.clean_urls:
                url_path = make_url_clean(url_path)
            page.url_path = url_path
        return page_output_paths

    def _generate_page(self, page: Page, pages: list[Page], output_path: Path) -> None:
        """Generate a single static page."""
        context = self._get_global_context()
        context["pages"] = pages
        output_path.parent.mkdir(parents=True, exist_ok=True)
        context["canonical_url"] = self._canonical_url_for_path(output_path)
        html = self.renderer.render_page(page, **context)
        self._write_html(output_path, html)

    def _generate_404_page(self, page: Page, pages: list[Page]) -> None:
        """Generate the custom 404 page in the root of the output directory."""
        context = self._get_global_context()
        context["pages"] = pages
        output_path = self.site_config.output_dir / CUSTOM_404_HTML
        context["canonical_url"] = self._canonical_url_for_path(output_path)
        html = self.renderer.render_page(page, **context)
        self._write_html(output_path, html)

    def _generate_index_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the main index page with pagination."""
        context = self._get_global_context()
        context["pages"] = pages

        paginated_posts = paginate_posts(posts, self.POSTS_PER_PAGE_INDEX)
        if not paginated_posts:
            paginated_posts = [[]]

        total_pages = len(paginated_posts)
        page1_url: str = "/index.html"
        if self.site_config.clean_urls:
            page1_url = make_url_clean(page1_url)

        page_urls = [page1_url] + [
            get_pagination_url(self.site_config, "", page_num)
            for page_num in range(2, total_pages + 1)
        ]

        for page_num, page_posts in enumerate(paginated_posts, start=1):
            if page_num == 1:
                output_path = self.site_config.output_dir / "index.html"
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = get_pagination_output_path(
                    self.site_config, self.site_config.output_dir, page_num
                )
            context["canonical_url"] = self._canonical_url_for_path(output_path)
            prev_url, next_url = pagination_prev_next(page_num, page_urls)
            context["prev_page_url"] = prev_url
            context["next_page_url"] = next_url
            context["pagination_page_urls"] = page_urls
            html = self.renderer.render_index(
                page_posts, page=page_num, total_pages=total_pages, **context
            )
            self._write_html(output_path, html)

    def _generate_archive_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the archive page."""
        context = self._get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.archive_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        archive_url = get_configured_url(self.site_config, "archive_path")
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{archive_url}"
                if self.site_config.site_url
                else archive_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)
        html = self.renderer.render_archive(
            posts, page=1, total_pages=1, base_path="/archive", **context
        )
        self._write_html(output_path, html)

    def _generate_date_archives(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate date-based archive pages."""
        posts_by_year: dict[int, list[Post]] = defaultdict(list)
        posts_by_month: dict[tuple[int, int], list[Post]] = defaultdict(list)
        posts_by_day: dict[tuple[int, int, int], list[Post]] = defaultdict(list)

        for post in posts:
            if post.date:
                year, month, day = post.date.year, post.date.month, post.date.day
                posts_by_year[year].append(post)
                posts_by_month[(year, month)].append(post)
                posts_by_day[(year, month, day)].append(post)

        context = self._get_global_context()
        context["pages"] = pages

        for year, year_posts in posts_by_year.items():
            year_dir = self.site_config.output_dir / str(year)
            year_dir.mkdir(parents=True, exist_ok=True)
            base_path = f"/{year}"

            def render_year(
                p: list[Post], n: int, t: int, y: int = year, bp: str = base_path
            ) -> str:
                return self.renderer.render_archive(
                    p,
                    archive_title=f"Posts from {y}",
                    page=n,
                    total_pages=t,
                    base_path=bp,
                    **context,
                )

            generate_paginated_listing(
                self.site_config,
                year_posts,
                base_path,
                year_dir,
                self.POSTS_PER_PAGE_ARCHIVE,
                context,
                render_year,
                self._write_html,
                self._canonical_url_for_path,
            )

        for (year, month), month_posts in posts_by_month.items():
            month_dir = self.site_config.output_dir / str(year) / f"{month:02d}"
            month_dir.mkdir(parents=True, exist_ok=True)
            month_name = dt.datetime(year, month, 1).strftime("%B %Y")
            base_path = f"/{year}/{month:02d}"

            def render_month(
                p: list[Post],
                n: int,
                t: int,
                name: str = month_name,
                bp: str = base_path,
            ) -> str:
                return self.renderer.render_archive(
                    p,
                    archive_title=f"Posts from {name}",
                    page=n,
                    total_pages=t,
                    base_path=bp,
                    **context,
                )

            generate_paginated_listing(
                self.site_config,
                month_posts,
                base_path,
                month_dir,
                self.POSTS_PER_PAGE_ARCHIVE,
                context,
                render_month,
                self._write_html,
                self._canonical_url_for_path,
            )

        for (year, month, day), day_posts in posts_by_day.items():
            day_dir = (
                self.site_config.output_dir / str(year) / f"{month:02d}" / f"{day:02d}"
            )
            day_dir.mkdir(parents=True, exist_ok=True)
            date_str = dt.datetime(year, month, day).strftime("%B %d, %Y")
            base_path = f"/{year}/{month:02d}/{day:02d}"

            def render_day(
                p: list[Post], n: int, t: int, d: str = date_str, bp: str = base_path
            ) -> str:
                return self.renderer.render_archive(
                    p,
                    archive_title=f"Posts from {d}",
                    page=n,
                    total_pages=t,
                    base_path=bp,
                    **context,
                )

            generate_paginated_listing(
                self.site_config,
                day_posts,
                base_path,
                day_dir,
                self.POSTS_PER_PAGE_ARCHIVE,
                context,
                render_day,
                self._write_html,
                self._canonical_url_for_path,
            )

    def _generate_tag_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each tag with pagination."""
        from blogmore.generator.grouping import group_posts_by_tag

        posts_by_tag = group_posts_by_tag(posts)
        tag_dir = self.site_config.output_dir / self.TAG_DIR
        tag_dir.mkdir(exist_ok=True)

        for tag_lower, (tag_display, tag_posts) in posts_by_tag.items():
            tag_posts.sort(key=post_sort_key, reverse=True)
            safe_tag = sanitize_for_url(tag_lower)
            base_url = f"/{self.TAG_DIR}/{safe_tag}"
            tag_base_dir = tag_dir / safe_tag
            context = self._get_global_context()
            context["pages"] = pages

            def render_tag(
                p: list[Post],
                n: int,
                t: int,
                d: str = tag_display,
                s: str = safe_tag,
                ctx: dict[str, Any] = context,
            ) -> str:
                return self.renderer.render_tag_page(
                    d, p, page=n, total_pages=t, safe_tag=s, **ctx
                )

            generate_paginated_listing(
                self.site_config,
                tag_posts,
                base_url,
                tag_base_dir,
                self.POSTS_PER_PAGE_TAG,
                context,
                render_tag,
                self._write_html,
                self._canonical_url_for_path,
            )

    def _generate_tags_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the tags overview page with word cloud."""
        from blogmore.generator.grouping import (
            calculate_cloud_font_sizes,
            group_posts_by_tag,
        )

        posts_by_tag = group_posts_by_tag(posts)
        if not posts_by_tag:
            return

        tag_data = [
            {
                "display_name": tag_display,
                "safe_tag": sanitize_for_url(tag_lower),
                "count": len(tag_posts),
                "tag_lower": tag_lower,
            }
            for tag_lower, (tag_display, tag_posts) in posts_by_tag.items()
        ]

        def sort_key(x: dict[str, Any]) -> str:
            return str(x["display_name"]).lower()

        tag_data.sort(key=sort_key)
        calculate_cloud_font_sizes(tag_data)

        context = self._get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.tags_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tags_url = get_configured_url(self.site_config, "tags_path")
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{tags_url}"
                if self.site_config.site_url
                else tags_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)
        html = self.renderer.render_tags_page(tag_data, **context)
        self._write_html(output_path, html)

    def _generate_category_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each category with pagination."""
        from blogmore.generator.grouping import group_posts_by_category

        posts_by_category = group_posts_by_category(posts)
        category_dir = self.site_config.output_dir / self.CATEGORY_DIR
        category_dir.mkdir(exist_ok=True)

        for category_lower, (
            category_display,
            category_posts,
        ) in posts_by_category.items():
            category_posts.sort(key=post_sort_key, reverse=True)
            safe_category = sanitize_for_url(category_lower)
            base_url = f"/{self.CATEGORY_DIR}/{safe_category}"
            category_base_dir = category_dir / safe_category
            context = self._get_global_context()
            context["pages"] = pages

            def render_category(
                p: list[Post],
                n: int,
                t: int,
                d: str = category_display,
                s: str = safe_category,
                ctx: dict[str, Any] = context,
            ) -> str:
                return self.renderer.render_category_page(
                    d, p, page=n, total_pages=t, safe_category=s, **ctx
                )

            generate_paginated_listing(
                self.site_config,
                category_posts,
                base_url,
                category_base_dir,
                self.POSTS_PER_PAGE_CATEGORY,
                context,
                render_category,
                self._write_html,
                self._canonical_url_for_path,
            )

    def _generate_categories_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the categories overview page with word cloud."""
        from blogmore.generator.grouping import (
            calculate_cloud_font_sizes,
            group_posts_by_category,
        )

        posts_by_category = group_posts_by_category(posts)
        if not posts_by_category:
            return

        category_data = [
            {
                "display_name": category_display,
                "safe_category": sanitize_for_url(category_lower),
                "count": len(category_posts),
                "category_lower": category_lower,
            }
            for category_lower, (
                category_display,
                category_posts,
            ) in posts_by_category.items()
        ]

        def sort_key(x: dict[str, Any]) -> str:
            return str(x["display_name"]).lower()

        category_data.sort(key=sort_key)
        calculate_cloud_font_sizes(category_data)

        context = self._get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.categories_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        categories_url = get_configured_url(self.site_config, "categories_path")
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{categories_url}"
                if self.site_config.site_url
                else categories_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)
        html = self.renderer.render_categories_page(category_data, **context)
        self._write_html(output_path, html)

    def _generate_feeds(self, posts: list[Post]) -> None:
        """Generate RSS and Atom feeds."""
        feed_gen = BlogFeedGenerator(
            output_dir=self.site_config.output_dir,
            site_title=self.site_config.site_title,
            site_url=self.site_config.site_url,
            max_posts=self.site_config.posts_per_feed,
        )
        feed_gen.generate_index_feeds(posts)
        from blogmore.generator.grouping import group_posts_by_category

        posts_by_category = group_posts_by_category(posts)
        for _category_lower, (
            _category_display,
            category_posts,
        ) in posts_by_category.items():
            category_posts.sort(key=post_sort_key, reverse=True)
        feed_gen.generate_category_feeds(posts_by_category)

    def _generate_search_page(self, sidebar_pages: list[Page]) -> None:
        """Generate the search page."""
        context = self._get_global_context()
        context["pages"] = sidebar_pages
        output_path = (
            self.site_config.output_dir / self.site_config.search_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        search_url = get_configured_url(self.site_config, "search_path")
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{search_url}"
                if self.site_config.site_url
                else search_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)
        html = self.renderer.render_search_page(**context)
        self._write_html(output_path, html)

    def _generate_stats_page(
        self,
        posts: list[Post],
        sidebar_pages: list[Page],
        backlink_map: "dict[str, list[Backlink]] | None" = None,
    ) -> None:
        """Generate the blog statistics page."""
        context = self._get_global_context()
        context["pages"] = sidebar_pages
        output_path = (
            self.site_config.output_dir / self.site_config.stats_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        stats_url = get_configured_url(self.site_config, "stats_path")
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{stats_url}"
                if self.site_config.site_url
                else stats_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)
        blog_stats: BlogStats = compute_blog_stats(
            posts, self.site_config.site_url, backlink_map
        )
        html = self.renderer.render_stats_page(stats=blog_stats, **context)
        self._write_html(output_path, html)

    def _generate_calendar_page(
        self, posts: list[Post], sidebar_pages: list[Page]
    ) -> None:
        """Generate the calendar view page."""
        context = self._get_global_context()
        context["pages"] = sidebar_pages
        output_path = (
            self.site_config.output_dir / self.site_config.calendar_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        calendar_url = get_configured_url(self.site_config, "calendar_path")
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{calendar_url}"
                if self.site_config.site_url
                else calendar_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)

        page1_suffix = self.site_config.page_1_path.lstrip("/")
        if self.site_config.clean_urls:
            page1_suffix = make_url_clean(f"/{page1_suffix}").lstrip("/")
        calendar_years: list[CalendarYear] = build_calendar(
            posts, page1_suffix, forward=self.site_config.forward_calendar
        )
        html = self.renderer.render_calendar_page(
            calendar_years=calendar_years, **context
        )
        self._write_html(output_path, html)

    def _generate_graph_page(
        self, posts: list[Post], sidebar_pages: list[Page]
    ) -> None:
        """Generate the post-relationship graph page."""
        context = self._get_global_context()
        context["pages"] = sidebar_pages
        output_path = (
            self.site_config.output_dir / self.site_config.graph_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        graph_url = get_configured_url(self.site_config, "graph_path")
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{graph_url}"
                if self.site_config.site_url
                else graph_url
            )
        else:
            context["canonical_url"] = self._canonical_url_for_path(output_path)
        graph_data: GraphData = build_graph_data(
            posts,
            tag_dir=self.TAG_DIR,
            category_dir=self.CATEGORY_DIR,
            site_url=self.site_config.site_url,
        )
        html = self.renderer.render_graph_page(
            graph_data_json=graph_data.to_json(), **context
        )
        self._write_html(output_path, html)

    def _remove_stale_search_files(self) -> None:
        """Remove search-related files left over from a previous build."""
        stale_json = self.site_config.output_dir / "search_index.json"
        if stale_json.exists():
            stale_json.unlink()
        stale_page = (
            self.site_config.output_dir / self.site_config.search_path.lstrip("/")
        ).resolve()
        if stale_page.exists():
            stale_page.unlink()
        default_page = (self.site_config.output_dir / "search.html").resolve()
        if default_page.exists() and default_page != stale_page:
            default_page.unlink()

    def _generate_sitemap(self) -> None:
        """Generate the XML sitemap file."""
        write_sitemap(
            self.site_config.output_dir,
            self.site_config.site_url,
            clean_urls=self.site_config.clean_urls,
            search_path=self.site_config.search_path,
            extra_excluded_paths=self._extras_html_paths,
            extra_urls=self.site_config.sitemap_extras,
        )
