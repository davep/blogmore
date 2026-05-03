"""The [`SiteGenerator`][blogmore.generator.site.SiteGenerator] class and its top-level `generate` orchestration."""

import shutil
import time
from pathlib import Path

from blogmore.backlinks import Backlink, build_backlink_map
from blogmore.fontawesome import FONTAWESOME_CDN_CSS_URL
from blogmore.generator._assets import AssetsMixin
from blogmore.generator._context import ContextMixin
from blogmore.generator._grouping import GroupingMixin
from blogmore.generator._listing import ListingMixin
from blogmore.generator._pages import PagesMixin
from blogmore.generator._paths import PathsMixin
from blogmore.parser import Page, Post, PostParser
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
        self._prepare_generation()

        # Parse all content
        posts, pages, page_404 = self._parse_content()

        # Resolve sidebar and paths
        sidebar_pages = self._resolve_sidebar_pages(pages)
        page_output_paths = self._resolve_page_output_paths(pages)
        post_output_paths = self._resolve_post_output_paths(posts)

        # Build cross-post metadata
        backlinks_map = self._build_backlinks(posts)

        # Prepare assets and directories
        self.site_config.output_dir.mkdir(parents=True, exist_ok=True)
        self._generate_icons()
        fontawesome_css_content = self._prepare_fontawesome_css()

        # Generate all HTML pages
        self._generate_content_pages(
            posts,
            pages,
            page_404,
            sidebar_pages,
            post_output_paths,
            page_output_paths,
            backlinks_map,
        )
        self._generate_listing_pages(posts, sidebar_pages)
        self._generate_optional_pages(posts, sidebar_pages, backlinks_map)

        # Finalize assets and site metadata
        self._finalize_site(fontawesome_css_content)

        print(f"Site generation complete! Output: {self.site_config.output_dir}")

    def _prepare_generation(self) -> None:
        """Initialize generation state and clean output directory if requested."""
        # Mint a fresh cache-busting token for this generation.
        self._cache_bust_token = str(int(time.time()))

        # Apply cache-busting to any local extra stylesheets.
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
                time.sleep(0.1)
                try:
                    shutil.rmtree(self.site_config.output_dir)
                except OSError:
                    shutil.rmtree(self.site_config.output_dir, ignore_errors=True)
                    print(
                        "Warning: Some files could not be removed from output directory"
                    )

    def _parse_content(self) -> tuple[list[Post], list[Page], Page | None]:
        """Parse all posts and pages from the content directory.

        Returns:
            Tuple of (posts, pages, page_404).
        """
        content_dir = self._content_dir
        pages_dir = content_dir / "pages"

        pages = self.parser.parse_pages_directory(pages_dir)
        page_404 = self.parser.parse_404_page(pages_dir)

        print(f"Parsing posts from {content_dir}...")
        posts = self.parser.parse_directory(
            content_dir,
            include_drafts=self.site_config.include_drafts,
            exclude_dirs=[pages_dir],
        )
        print(f"Found {len(posts)} posts")

        # Apply configured reading-speed and default author
        for post in posts:
            post.words_per_minute = self.site_config.read_time_wpm
            if self.site_config.default_author and (
                post.metadata is None or "author" not in post.metadata
            ):
                if post.metadata is None:
                    post.metadata = {}
                post.metadata["author"] = self.site_config.default_author

        if pages:
            print(f"Found {len(pages)} pages")

        return posts, pages, page_404

    def _build_backlinks(self, posts: list[Post]) -> dict[str, list[Backlink]]:
        """Build the backlink map if the feature is enabled.

        Args:
            posts: All published posts.

        Returns:
            Mapping from post URL to list of backlinks.
        """
        if self.site_config.with_backlinks:
            print("Building backlink map...")
            return build_backlink_map(posts, site_url=self.site_config.site_url)
        return {}

    def _generate_content_pages(
        self,
        posts: list[Post],
        pages: list[Page],
        page_404: Page | None,
        sidebar_pages: list[Page],
        post_output_paths: dict[int, Path],
        page_output_paths: dict[int, Path],
        backlinks_map: dict[str, list[Backlink]],
    ) -> None:
        """Generate individual post and static pages.

        Args:
            posts: All published posts.
            pages: All static pages.
            page_404: Custom 404 page if present.
            sidebar_pages: Pages to display in the sidebar.
            post_output_paths: Pre-resolved output paths for posts.
            page_output_paths: Pre-resolved output paths for pages.
            backlinks_map: Mapping of posts to their incoming links.
        """
        print("Generating post pages...")
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

        if pages:
            print("Generating static pages...")
            for page in pages:
                self._generate_page(page, sidebar_pages, page_output_paths[id(page)])

        if page_404 is not None:
            print("Generating custom 404 page...")
            self._generate_404_page(page_404, sidebar_pages)

    def _generate_listing_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate all index and listing pages (archives, tags, categories).

        Args:
            posts: All published posts.
            pages: Sidebar pages.
        """
        print("Generating index page...")
        self._generate_index_page(posts, pages)

        print("Generating archive pages...")
        self._generate_archive_page(posts, pages)
        self._generate_date_archives(posts, pages)

        print("Generating tag pages...")
        self._generate_tag_pages(posts, pages)
        self._generate_tags_page(posts, pages)

        print("Generating category pages...")
        self._generate_category_pages(posts, pages)
        self._generate_categories_page(posts, pages)

    def _generate_optional_pages(
        self,
        posts: list[Post],
        pages: list[Page],
        backlinks_map: dict[str, list[Backlink]],
    ) -> None:
        """Generate optional feature pages (feeds, search, stats, etc.).

        Args:
            posts: All published posts.
            pages: Sidebar pages.
            backlinks_map: Backlink mapping.
        """
        print("Generating RSS and Atom feeds...")
        self._generate_feeds(posts)

        if self.site_config.with_search:
            print("Generating search index and search page...")
            self._generate_search_index(posts)
            self._generate_search_page(pages)
        else:
            self._remove_stale_search_files()

        if self.site_config.with_stats:
            print("Generating blog statistics page...")
            self._generate_stats_page(
                posts,
                pages,
                backlinks_map if self.site_config.with_backlinks else None,
            )

        if self.site_config.with_calendar:
            print("Generating calendar page...")
            self._generate_calendar_page(posts, pages)

        if self.site_config.with_graph:
            print("Generating graph page...")
            self._generate_graph_page(posts, pages)

    def _finalize_site(self, fontawesome_css_content: str | None) -> None:
        """Finalize site by copying assets and generating sitemap.

        Args:
            fontawesome_css_content: Optimized FontAwesome CSS if generated.
        """
        self._copy_static_assets()

        if fontawesome_css_content is not None:
            self._write_fontawesome_css(fontawesome_css_content)

        self._copy_extras()

        if self.site_config.with_sitemap:
            print("Generating XML sitemap...")
            self._generate_sitemap()


### site.py ends here
