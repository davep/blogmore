"""The [`SiteGenerator`][blogmore.generator.site.SiteGenerator] class and its top-level `generate` orchestration."""

import shutil
import time

from blogmore.backlinks import Backlink, build_backlink_map
from blogmore.fontawesome import FONTAWESOME_CDN_CSS_URL
from blogmore.generator._assets import AssetsMixin
from blogmore.generator._context import ContextMixin
from blogmore.generator._grouping import GroupingMixin
from blogmore.generator._listing import ListingMixin
from blogmore.generator._pages import PagesMixin
from blogmore.generator._paths import PathsMixin
from blogmore.parser import PostParser
from blogmore.renderer import TemplateRenderer
from blogmore.site_config import SiteConfig


class SiteGenerator(
    AssetsMixin,
    ContextMixin,
    GroupingMixin,
    ListingMixin,
    PagesMixin,
    PathsMixin,
):
    """Generate a static blog site from markdown posts."""

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

    def generate(self) -> None:
        """Generate the complete static site."""
        content_dir = self._content_dir

        # Mint a fresh cache-busting token for this generation.  All pages
        # rendered during this run will share the same token so that once a
        # visitor downloads a stylesheet it stays cached for the lifetime of
        # this deployment.  A new generation produces a new token, which forces
        # browsers to re-fetch any updated stylesheets.
        self._cache_bust_token = str(int(time.time()))

        # Apply cache-busting to any local extra stylesheets so they are also
        # re-fetched after a new site generation.  Always reassign the list so
        # that removing extra_stylesheets from the config correctly clears the
        # renderer's list on the next build.
        extra_stylesheets = self.site_config.extra_stylesheets or []
        self.renderer.extra_stylesheets = [
            self._with_cache_bust(url) for url in extra_stylesheets
        ]

        # Clean output directory if requested
        if self.site_config.clean_first and self.site_config.output_dir.exists():
            print(f"Removing output directory: {self.site_config.output_dir}")
            try:
                shutil.rmtree(self.site_config.output_dir)
            except OSError:
                # On Linux with concurrent operations the directory may not be
                # fully empty yet.  Wait briefly and retry once before falling
                # back to a best-effort removal.
                time.sleep(0.1)
                try:
                    shutil.rmtree(self.site_config.output_dir)
                except OSError:
                    shutil.rmtree(self.site_config.output_dir, ignore_errors=True)
                    print(
                        "Warning: Some files could not be removed from output directory"
                    )

        # Parse all pages from the pages subdirectory (must be done first so we
        # can exclude them when scanning for posts)
        pages_dir = content_dir / "pages"
        pages = self.parser.parse_pages_directory(pages_dir)
        page_404 = self.parser.parse_404_page(pages_dir)

        # Parse all posts, excluding the pages subdirectory
        print(f"Parsing posts from {content_dir}...")
        posts = self.parser.parse_directory(
            content_dir,
            include_drafts=self.site_config.include_drafts,
            exclude_dirs=[pages_dir],
        )
        print(f"Found {len(posts)} posts")

        # Apply configured reading-speed to every post so that reading_time
        # reflects the user's read_time_wpm setting.
        for post in posts:
            post.words_per_minute = self.site_config.read_time_wpm

        # Apply default author to posts that don't have one
        if self.site_config.default_author:
            for post in posts:
                if post.metadata is not None and "author" not in post.metadata:
                    post.metadata["author"] = self.site_config.default_author
        if pages:
            print(f"Found {len(pages)} pages")

        # Resolve the list of pages to display in the sidebar.  This may be a
        # filtered/reordered subset when the user has configured ``pages:`` in
        # the config file; otherwise it equals ``pages`` unchanged.
        sidebar_pages = self._resolve_sidebar_pages(pages)

        # Create output directory
        self.site_config.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate icons from source image BEFORE generating HTML pages
        # so that the has_apple_touch_icons flag is correctly set
        self._generate_icons()

        # Prepare the FontAwesome CSS URL (and content if optimisation succeeds).
        # Must be done before any HTML is rendered so the correct URL is embedded
        # in every page, but the CSS file itself is written after _copy_static_assets()
        # so it is not overwritten by that step.
        fontawesome_css_content = self._prepare_fontawesome_css()

        # Resolve page output paths before generating any HTML so that
        # page.url_path is set correctly for all pages (including when they
        # appear in the sidebar of individual post pages).
        page_output_paths = self._resolve_page_output_paths(pages)

        # Generate individual post pages
        print("Generating post pages...")
        post_output_paths = self._resolve_post_output_paths(posts)

        # Build the backlink map only when the feature is enabled.  This
        # must happen after _resolve_post_output_paths() so that every
        # post.url_path is set to its final value before link matching.
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
                # A newer post has already claimed this path; skip this older one.
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
            self._generate_search_index(posts)
            self._generate_search_page(sidebar_pages)
        else:
            # Remove any stale search files left over from a previous build
            # that had search enabled.
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
        self._copy_static_assets()

        # Write the optimised FontAwesome CSS file after static assets have been
        # copied so it is not overwritten by _copy_static_assets().
        if fontawesome_css_content is not None:
            self._write_fontawesome_css(fontawesome_css_content)

        # Copy extra files from extras directory
        self._copy_extras()

        # Generate XML sitemap (only when enabled)
        if self.site_config.with_sitemap:
            print("Generating XML sitemap...")
            self._generate_sitemap()

        print(f"Site generation complete! Output: {self.site_config.output_dir}")


### site.py ends here
