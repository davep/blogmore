"""The [`SiteGenerator`][blogmore.generator.site.SiteGenerator] class and its top-level `generate` orchestration."""

from __future__ import annotations

import shutil
import time
from typing import TYPE_CHECKING

from blogmore.backlinks import build_backlink_map
from blogmore.generator.assets import AssetManager
from blogmore.generator.context import ContextBuilder
from blogmore.generator.features import FeatureGenerator
from blogmore.generator.listings import ListingGenerator
from blogmore.generator.pages import PageGenerator
from blogmore.generator.paths import (
    resolve_page_output_paths,
    resolve_post_output_paths,
    resolve_sidebar_pages,
)
from blogmore.parser import PostParser
from blogmore.renderer import TemplateRenderer

if TYPE_CHECKING:
    from blogmore.backlinks import Backlink
    from blogmore.site_config import SiteConfig


class SiteGenerator:
    """Generate a static blog site from markdown posts."""

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

        self.parser = PostParser(site_url=site_config.site_url)
        self.renderer = TemplateRenderer(
            site_config.templates_dir,
            site_config.extra_stylesheets,
            site_config.site_url,
        )

    def generate(self) -> None:
        """Generate the complete static site."""
        content_dir = self.site_config.content_dir
        assert content_dir is not None

        # Mint a fresh cache-busting token for this generation.
        cache_bust_token = str(int(time.time()))

        # Instantiate the asset manager first to discover site assets.
        asset_manager = AssetManager(self.site_config)

        # Instantiate the context builder; it will be used by all generators.
        # We'll update its discovery state once assets are processed.
        context_builder = ContextBuilder(
            self.site_config,
            cache_bust_token=cache_bust_token,
        )

        # Apply cache-busting to any local extra stylesheets.
        extra_stylesheets = self.site_config.extra_stylesheets or []
        self.renderer.extra_stylesheets = [
            context_builder.with_cache_bust(url) for url in extra_stylesheets
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

        # Parse all pages & posts
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

        for post in posts:
            post.words_per_minute = self.site_config.read_time_wpm
        if self.site_config.default_author:
            for post in posts:
                if post.metadata is not None and "author" not in post.metadata:
                    post.metadata["author"] = self.site_config.default_author
        if pages:
            print(f"Found {len(pages)} pages")

        sidebar_pages = resolve_sidebar_pages(self.site_config, pages)

        # Create output directory
        self.site_config.output_dir.mkdir(parents=True, exist_ok=True)

        # Process assets
        asset_manager.generate_icons()
        fontawesome_css_content = asset_manager.prepare_fontawesome_css()

        # Update context builder with discovered asset state.
        context_builder.favicon_url = asset_manager.detect_favicon()
        context_builder.has_platform_icons = asset_manager.detect_generated_icons()
        context_builder.fontawesome_css_url = asset_manager.fontawesome_css_url

        # Resolve paths
        page_output_paths = resolve_page_output_paths(self.site_config, pages)
        post_output_paths = resolve_post_output_paths(self.site_config, posts)

        # Build backlink map
        backlinks_map: dict[str, list[Backlink]] = {}
        if self.site_config.with_backlinks:
            print("Building backlink map...")
            backlinks_map = build_backlink_map(
                posts,
                site_url=self.site_config.site_url,
            )

        # Instantiate specialized generators
        page_gen = PageGenerator(self.site_config, self.renderer, context_builder)
        listing_gen = ListingGenerator(self.site_config, self.renderer, context_builder)
        feature_gen = FeatureGenerator(self.site_config, self.renderer, context_builder)

        # Generate individual post pages
        print("Generating post pages...")
        generated_paths: set[str] = set()
        for post in posts:
            output_path = post_output_paths[id(post)]
            path_key = str(output_path)
            if path_key in generated_paths:
                continue
            generated_paths.add(path_key)
            page_gen.generate_post_page(
                post, posts, sidebar_pages, output_path, backlinks_map
            )

        # Generate static pages
        if pages:
            print("Generating static pages...")
            for page in pages:
                page_gen.generate_page(page, sidebar_pages, page_output_paths[id(page)])

        # Generate custom 404 page
        if page_404 is not None:
            print("Generating custom 404 page...")
            page_gen.generate_404_page(page_404, sidebar_pages)

        # Generate core index/archive pages
        print("Generating index page...")
        page_gen.generate_index_page(posts, sidebar_pages)
        print("Generating archive page...")
        page_gen.generate_archive_page(posts, sidebar_pages)

        # Generate listing pages
        print("Generating date-based archive pages...")
        listing_gen.generate_date_archives(posts, sidebar_pages)
        print("Generating tag pages...")
        listing_gen.generate_tag_pages(posts, sidebar_pages)
        print("Generating tags overview page...")
        listing_gen.generate_tags_page(posts, sidebar_pages)
        print("Generating category pages...")
        listing_gen.generate_category_pages(posts, sidebar_pages)
        print("Generating categories overview page...")
        listing_gen.generate_categories_page(posts, sidebar_pages)

        # Generate optional feature pages
        print("Generating RSS and Atom feeds...")
        feature_gen.generate_feeds(posts)

        if self.site_config.with_search:
            print("Generating search index and search page...")
            feature_gen.generate_search_index(posts)
            feature_gen.generate_search_page(sidebar_pages)
        else:
            feature_gen.remove_stale_search_files()

        if self.site_config.with_stats:
            print("Generating blog statistics page...")
            feature_gen.generate_stats_page(
                posts,
                sidebar_pages,
                backlinks_map if self.site_config.with_backlinks else None,
            )

        if self.site_config.with_calendar:
            print("Generating calendar page...")
            feature_gen.generate_calendar_page(posts, sidebar_pages)

        if self.site_config.with_graph:
            print("Generating graph page...")
            feature_gen.generate_graph_page(posts, sidebar_pages)

        # Finalize static assets & sitemap
        asset_manager.copy_static_assets()
        if fontawesome_css_content is not None:
            asset_manager.write_fontawesome_css(fontawesome_css_content)
        asset_manager.copy_extras()

        if self.site_config.with_sitemap:
            print("Generating XML sitemap...")
            feature_gen.generate_sitemap(asset_manager.extras_html_paths)

        print(f"Site generation complete! Output: {self.site_config.output_dir}")
