"""Static site generator for blog content."""

import datetime as dt
import shutil
import time
import urllib.error
from collections import defaultdict
from importlib.resources import files
from pathlib import Path
from typing import Any

import minify_html
import rcssmin  # type: ignore[import-untyped]
import rjsmin  # type: ignore[import-untyped]

from blogmore import __version__
from blogmore.clean_url import make_url_clean
from blogmore.feeds import BlogFeedGenerator
from blogmore.fontawesome import (
    FONTAWESOME_CDN_BRANDS_WOFF2_URL,
    FONTAWESOME_CDN_CSS_URL,
    FONTAWESOME_LOCAL_CSS_MINIFIED_PATH,
    FONTAWESOME_LOCAL_CSS_PATH,
    FontAwesomeOptimizer,
)
from blogmore.icons import IconGenerator, detect_source_icon
from blogmore.page_path import compute_page_output_path
from blogmore.pagination_path import resolve_pagination_page_path
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

CSS_FILENAME = "style.css"
CSS_MINIFIED_FILENAME = "styles.min.css"
THEME_JS_FILENAME = "theme.js"
THEME_JS_MINIFIED_FILENAME = "theme.min.js"
SEARCH_JS_FILENAME = "search.js"
SEARCH_JS_MINIFIED_FILENAME = "search.min.js"
CODEBLOCKS_JS_FILENAME = "codeblocks.js"
CODEBLOCKS_JS_MINIFIED_FILENAME = "codeblocks.min.js"


def paginate_posts(posts: list[Post], posts_per_page: int) -> list[list[Post]]:
    """Split a list of posts into pages.

    Args:
        posts: List of posts to paginate
        posts_per_page: Number of posts per page

    Returns:
        List of pages, where each page is a list of posts
    """
    if not posts:
        return []
    if posts_per_page <= 0:
        return [posts]

    pages = []
    for i in range(0, len(posts), posts_per_page):
        pages.append(posts[i : i + posts_per_page])
    return pages


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
                ``content_dir`` field must not be ``None``.
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

    @property
    def _content_dir(self) -> Path:
        """Return the content directory as a ``Path``, guaranteed non-``None``.

        ``__init__`` validates that ``site_config.content_dir`` is not ``None``,
        so this property is always safe to call on a constructed instance.

        Returns:
            The resolved content directory path.
        """
        assert self.site_config.content_dir is not None
        return self.site_config.content_dir

    def _detect_favicon(self) -> str | None:
        """Detect if a favicon file exists in the icons or extras directory.

        Checks for favicon files with common extensions in priority order.
        First checks the icons directory (for generated icons), then falls back
        to the extras directory (for manually provided icons).

        Returns:
            The favicon URL (relative to site root) if found, None otherwise
        """
        # First check icons directory (generated icons)
        icons_dir = self.site_config.output_dir / "icons"
        if icons_dir.exists():
            favicon_path = icons_dir / "favicon.ico"
            if favicon_path.is_file():
                return "/icons/favicon.ico"

        # Fall back to extras directory (existing behavior)
        extras_dir = self._content_dir / "extras"
        if not extras_dir.exists():
            return None

        # Common favicon extensions in priority order
        favicon_extensions = [".ico", ".png", ".svg", ".gif", ".jpg", ".jpeg"]

        # Check for favicon files
        for ext in favicon_extensions:
            favicon_path = extras_dir / f"favicon{ext}"
            if favicon_path.is_file():
                return f"/favicon{ext}"

        return None

    def _detect_generated_icons(self) -> bool:
        """Detect if generated platform icons exist in the icons directory.

        Returns:
            True if generated icons exist, False otherwise
        """
        icons_dir = self.site_config.output_dir / "icons"
        if not icons_dir.exists():
            return False

        # Check if the main Apple touch icon exists as an indicator
        apple_icon_path = icons_dir / "apple-touch-icon.png"
        return apple_icon_path.is_file()

    def _generate_icons(self) -> None:
        """Generate icons from a source image if present."""
        extras_dir = self._content_dir / "extras"

        # Look for a source icon (using configured name if provided)
        source_icon = detect_source_icon(extras_dir, self.site_config.icon_source)

        if source_icon:
            print(f"Found source icon: {source_icon.name}")
            print("Generating favicon and Apple touch icons...")

            # Generate to /icons subdirectory
            icons_output_dir = self.site_config.output_dir / "icons"
            generator = IconGenerator(source_icon, icons_output_dir)
            generated = generator.generate_all()

            if generated:
                print(f"Generated {len(generated)} icon file(s):")
                for icon_name in generated:
                    print(f"  - icons/{icon_name}")

                # Copy favicon.ico to the root for backward compatibility
                if favicon_ico := generated.get("favicon.ico"):
                    shutil.copy2(
                        favicon_ico, self.site_config.output_dir / "favicon.ico"
                    )
                    print("  - favicon.ico (root copy for backward compatibility)")
            else:
                print("Warning: No icons were generated")

    def _with_cache_bust(self, url: str) -> str:
        """Return a URL with a cache-busting query parameter appended.

        External URLs (i.e. those that start with ``http://`` or ``https://``)
        are returned unchanged.  Local URLs (starting with ``/``) have
        ``?v=<token>`` appended so that browsers re-fetch them when the site is
        regenerated.  If no cache-busting token has been set (e.g. before
        :meth:`generate` is called) the URL is returned as-is.

        Args:
            url: The URL to process.

        Returns:
            The URL with a cache-busting query parameter appended, or the
            original URL if it is external or the token has not been set.
        """
        if (
            not self._cache_bust_token
            or not url
            or url.startswith(("http://", "https://"))
        ):
            return url
        return f"{url}?v={self._cache_bust_token}"

    def _get_search_url(self) -> str:
        """Return the URL path for the configured search page.

        Derives the URL from the ``search_path`` configuration option.  When
        ``clean_urls`` is enabled and the path ends in ``index.html``, the
        index filename is stripped so the URL ends with a trailing slash.

        Returns:
            The URL path for the search page, always starting with ``/``.
        """
        url = "/" + self.site_config.search_path.lstrip("/")
        if self.site_config.clean_urls:
            url = make_url_clean(url)
        return url

    def _get_archive_url(self) -> str:
        """Return the URL path for the configured archive page.

        Derives the URL from the ``archive_path`` configuration option.  When
        ``clean_urls`` is enabled and the path ends in ``index.html``, the
        index filename is stripped so the URL ends with a trailing slash.

        Returns:
            The URL path for the archive page, always starting with ``/``.
        """
        url = "/" + self.site_config.archive_path.lstrip("/")
        if self.site_config.clean_urls:
            url = make_url_clean(url)
        return url

    def _get_tags_url(self) -> str:
        """Return the URL path for the configured tags overview page.

        Derives the URL from the ``tags_path`` configuration option.  When
        ``clean_urls`` is enabled and the path ends in ``index.html``, the
        index filename is stripped so the URL ends with a trailing slash.

        Returns:
            The URL path for the tags page, always starting with ``/``.
        """
        url = "/" + self.site_config.tags_path.lstrip("/")
        if self.site_config.clean_urls:
            url = make_url_clean(url)
        return url

    def _get_categories_url(self) -> str:
        """Return the URL path for the configured categories overview page.

        Derives the URL from the ``categories_path`` configuration option.  When
        ``clean_urls`` is enabled and the path ends in ``index.html``, the
        index filename is stripped so the URL ends with a trailing slash.

        Returns:
            The URL path for the categories page, always starting with ``/``.
        """
        url = "/" + self.site_config.categories_path.lstrip("/")
        if self.site_config.clean_urls:
            url = make_url_clean(url)
        return url

    def _get_global_context(self) -> dict[str, Any]:
        """Get the global context available to all templates."""
        styles_css_url = self._with_cache_bust(
            f"/static/{CSS_MINIFIED_FILENAME}"
            if self.site_config.minify_css
            else f"/static/{CSS_FILENAME}"
        )
        theme_js_url = (
            f"/static/{THEME_JS_MINIFIED_FILENAME}"
            if self.site_config.minify_js
            else f"/static/{THEME_JS_FILENAME}"
        )
        search_js_url = (
            f"/static/{SEARCH_JS_MINIFIED_FILENAME}"
            if self.site_config.minify_js
            else f"/static/{SEARCH_JS_FILENAME}"
        )
        codeblocks_js_url = (
            f"/static/{CODEBLOCKS_JS_MINIFIED_FILENAME}"
            if self.site_config.minify_js
            else f"/static/{CODEBLOCKS_JS_FILENAME}"
        )
        page1_suffix = resolve_pagination_page_path(self.site_config.page_1_path, 1)
        if self.site_config.clean_urls:
            page1_suffix = make_url_clean(page1_suffix)
        context = {
            "site_title": self.site_config.site_title,
            "site_subtitle": self.site_config.site_subtitle,
            "site_description": self.site_config.site_description,
            "site_keywords": self.site_config.site_keywords,
            "site_url": self.site_config.site_url,
            "tag_dir": self.TAG_DIR,
            "category_dir": self.CATEGORY_DIR,
            "favicon_url": self._detect_favicon(),
            "has_platform_icons": self._detect_generated_icons(),
            "blogmore_version": __version__,
            "with_search": self.site_config.with_search,
            "search_url": self._get_search_url(),
            "archive_url": self._get_archive_url(),
            "tags_url": self._get_tags_url(),
            "categories_url": self._get_categories_url(),
            "with_read_time": self.site_config.with_read_time,
            "with_advert": self.site_config.with_advert,
            "default_author": self.site_config.default_author,
            "extra_head_tags": self.site_config.head,
            "fontawesome_css_url": self._with_cache_bust(self._fontawesome_css_url),
            "fontawesome_woff2_url": FONTAWESOME_CDN_BRANDS_WOFF2_URL,
            "styles_css_url": styles_css_url,
            "theme_js_url": theme_js_url,
            "search_js_url": search_js_url,
            "codeblocks_js_url": codeblocks_js_url,
            "pagination_page1_suffix": page1_suffix,
        }
        # Merge sidebar config into context
        context.update(self.site_config.sidebar_config)
        return context

    def _get_pagination_url(self, base_url: str, page_num: int) -> str:
        """Compute the URL for a given pagination page.

        Joins *base_url* with the path resolved from the configured
        ``page_1_path`` or ``page_n_path`` template.  When ``clean_urls``
        is enabled and the resolved URL ends in ``index.html``, that
        suffix is stripped.

        Args:
            base_url: The URL prefix for the paginated section (e.g.
                ``/2024`` for a year archive).  May be an empty string
                for the main index.
            page_num: The 1-based page number.

        Returns:
            The fully-formed URL for the requested page.
        """
        if page_num == 1:
            relative = resolve_pagination_page_path(self.site_config.page_1_path, 1)
        else:
            relative = resolve_pagination_page_path(
                self.site_config.page_n_path, page_num
            )
        url = f"{base_url}/{relative}"
        # Collapse any double slashes introduced when base_url is empty.
        url = url.replace("//", "/")
        if self.site_config.clean_urls:
            url = make_url_clean(url)
        return url

    def _build_pagination_page_urls(self, base_url: str, total_pages: int) -> list[str]:
        """Build the full list of page URLs for a paginated section.

        Args:
            base_url: The URL prefix for the paginated section.
            total_pages: The total number of pages.

        Returns:
            A list of URLs, one per page, ordered from page 1 to
            *total_pages*.
        """
        return [
            self._get_pagination_url(base_url, page_num)
            for page_num in range(1, total_pages + 1)
        ]

    def _get_pagination_output_path(self, base_dir: Path, page_num: int) -> Path:
        """Compute the output file path for a given pagination page.

        Resolves the appropriate path template from the site configuration
        and joins it onto *base_dir*.  Any required parent directories are
        created automatically.

        Args:
            base_dir: The base directory for this paginated section.
            page_num: The 1-based page number.

        Returns:
            The absolute output file path for the given page.
        """
        if page_num == 1:
            relative = resolve_pagination_page_path(self.site_config.page_1_path, 1)
        else:
            relative = resolve_pagination_page_path(
                self.site_config.page_n_path, page_num
            )
        output_path = base_dir / relative
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    @staticmethod
    def _pagination_prev_next(
        page_num: int,
        page_urls: list[str],
    ) -> tuple[str | None, str | None]:
        """Return the previous and next page URLs for a paginated page.

        Args:
            page_num: The current page number (1-based).
            page_urls: Ordered list of all page URLs (index 0 = page 1).

        Returns:
            A tuple of ``(prev_url, next_url)`` where each element is
            ``None`` when there is no adjacent page.
        """
        prev_url: str | None = page_urls[page_num - 2] if page_num > 1 else None
        next_url: str | None = (
            page_urls[page_num] if page_num < len(page_urls) else None
        )
        return prev_url, next_url

    def _canonical_url_for_path(self, output_path: Path) -> str:
        """Compute the fully-qualified canonical URL for a given output file path.

        Args:
            output_path: Absolute path to the output file within the output directory.

        Returns:
            The fully-qualified canonical URL for the given file.
        """
        relative = output_path.relative_to(self.site_config.output_dir)
        return f"{self.site_config.site_url}/{relative.as_posix()}"

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

        # Generate individual post pages
        print("Generating post pages...")
        post_output_paths = self._resolve_post_output_paths(posts)
        generated_paths: set[str] = set()
        for post in posts:
            output_path = post_output_paths[id(post)]
            path_key = str(output_path)
            if path_key in generated_paths:
                # A newer post has already claimed this path; skip this older one.
                continue
            generated_paths.add(path_key)
            self._generate_post_page(post, posts, sidebar_pages, output_path)

        # Generate static pages
        if pages:
            print("Generating static pages...")
            page_output_paths = self._resolve_page_output_paths(pages)
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

    def _prepare_fontawesome_css(self) -> str | None:
        """Determine the FontAwesome CSS URL and optionally build optimised CSS.

        Extracts the social icon names from the sidebar configuration and
        attempts to fetch the FontAwesome metadata from GitHub to build a
        minimal CSS file.  Updates ``self._fontawesome_css_url`` with the URL
        that every rendered page will reference.

        Returns:
            The CSS content string to write to disk if optimisation succeeded,
            or ``None`` if no social icons are configured or if the metadata
            fetch failed (in the latter case the full CDN URL is used instead).
        """
        socials: list[Any] = self.site_config.sidebar_config.get("socials", [])
        if not socials:
            # No social icons — no FontAwesome CSS needed at all.
            self._fontawesome_css_url = ""
            return None

        icon_names = [
            str(social["site"])
            for social in socials
            if isinstance(social, dict) and "site" in social
        ]
        optimizer = FontAwesomeOptimizer(icon_names)

        try:
            metadata = optimizer.fetch_icon_metadata()
        except (urllib.error.URLError, ValueError, OSError) as error:
            print(f"Warning: Could not fetch FontAwesome metadata: {error}")
            print("Falling back to full FontAwesome CDN stylesheet.")
            self._fontawesome_css_url = FONTAWESOME_CDN_CSS_URL
            return None

        print("Optimizing FontAwesome CSS...")
        self._fontawesome_css_url = (
            FONTAWESOME_LOCAL_CSS_MINIFIED_PATH
            if self.site_config.minify_css
            else FONTAWESOME_LOCAL_CSS_PATH
        )
        return optimizer.build_css(metadata)

    def _write_fontawesome_css(self, css_content: str) -> None:
        """Write the optimised FontAwesome CSS file to the static directory.

        Must be called *after* :meth:`_copy_static_assets` so the file is not
        overwritten.  When ``minify_css`` is enabled the content is minified
        and written as ``fontawesome.min.css``; otherwise it is written as
        ``fontawesome.css``.

        Args:
            css_content: CSS text to write.
        """
        static_dir = self.site_config.output_dir / "static"
        static_dir.mkdir(parents=True, exist_ok=True)
        if self.site_config.minify_css:
            minified = rcssmin.cssmin(css_content)
            css_path = static_dir / "fontawesome.min.css"
            css_path.write_text(minified, encoding="utf-8")
            print("Generated minified FontAwesome CSS as fontawesome.min.css")
        else:
            css_path = static_dir / "fontawesome.css"
            css_path.write_text(css_content, encoding="utf-8")
            print("Generated optimized FontAwesome CSS")

    def _write_html(self, output_path: Path, html: str) -> None:
        """Write an HTML string to a file, minifying it when configured to do so.

        When ``minify_html`` is enabled the HTML content is passed through the
        ``minify-html`` library before being written.  The output file name is
        not changed — only the content is minified.

        Args:
            output_path: Destination file path.
            html: HTML content to write.
        """
        if self.site_config.minify_html:
            html = minify_html.minify(html, minify_js=False, minify_css=False)
        output_path.write_text(html, encoding="utf-8")

    def _write_minified_css(self, output_static: Path) -> None:
        """Read the source CSS, minify it, and write it as ``styles.min.css``.

        The source CSS is read from the custom templates directory (if
        available) or from the bundled templates.  The minified output is
        written to ``output_static/styles.min.css``.

        Args:
            output_static: Path to the output static directory.
        """
        css_source: str | None = None

        # Prefer custom style.css if a templates directory is configured
        if self.site_config.templates_dir is not None:
            custom_css = self.site_config.templates_dir / "static" / CSS_FILENAME
            if custom_css.is_file():
                css_source = custom_css.read_text(encoding="utf-8")

        # Fall back to bundled style.css
        if css_source is None:
            try:
                bundled_css = files("blogmore").joinpath(
                    "templates", "static", CSS_FILENAME
                )
                css_source = bundled_css.read_text(encoding="utf-8")
            except Exception as e:
                print(
                    f"Warning: Could not read bundled {CSS_FILENAME} for minification: {e}"
                )
                return

        minified = rcssmin.cssmin(css_source)
        output_path = output_static / CSS_MINIFIED_FILENAME
        output_path.write_text(minified, encoding="utf-8")
        print(f"Generated minified CSS as {CSS_MINIFIED_FILENAME}")

    def _write_minified_js(
        self, output_static: Path, js_filename: str, js_minified_filename: str
    ) -> None:
        """Read a source JavaScript file, minify it, and write it with the minified name.

        The source JS is read from the custom templates directory (if
        available) or from the bundled templates.  The minified output is
        written to ``output_static/<js_minified_filename>``.

        Args:
            output_static: Path to the output static directory.
            js_filename: The original JavaScript filename (e.g. ``theme.js``).
            js_minified_filename: The minified output filename (e.g. ``theme.min.js``).
        """
        js_source: str | None = None

        # Prefer custom JS file if a templates directory is configured
        if self.site_config.templates_dir is not None:
            custom_js = self.site_config.templates_dir / "static" / js_filename
            if custom_js.is_file():
                js_source = custom_js.read_text(encoding="utf-8")

        # Fall back to bundled JS file
        if js_source is None:
            try:
                bundled_js = files("blogmore").joinpath(
                    "templates", "static", js_filename
                )
                js_source = bundled_js.read_text(encoding="utf-8")
            except Exception as e:
                print(
                    f"Warning: Could not read bundled {js_filename} for minification: {e}"
                )
                return

        minified = rjsmin.jsmin(js_source)
        output_path = output_static / js_minified_filename
        output_path.write_text(minified, encoding="utf-8")
        print(f"Generated minified JS as {js_minified_filename}")

    def _resolve_post_output_paths(self, posts: list[Post]) -> dict[int, Path]:
        """Resolve the output path for every post and detect path clashes.

        For each post the method:

        1. Computes the absolute output file path using the configured
           ``post_path`` template.
        2. Sets ``post.url_path`` so that templates and feeds always use the
           correct URL regardless of the configured format.
        3. Groups posts by output path and emits a prominent ``WARNING`` for
           any group that contains more than one post (i.e. a path clash).
           The *newest* post (first in the already-sorted list) wins; older
           posts that share the same path will be skipped during generation.

        Args:
            posts: All posts sorted by date, newest first.

        Returns:
            Mapping from ``id(post)`` to the post's resolved output path.
        """
        post_output_paths: dict[int, Path] = {}
        # Preserve insertion order so we can identify the winner easily.
        path_to_post_ids: dict[str, list[int]] = defaultdict(list)
        post_by_id: dict[int, Post] = {id(post): post for post in posts}

        for post in posts:
            output_path = compute_output_path(
                self.site_config.output_dir, post, self.site_config.post_path
            )
            post_output_paths[id(post)] = output_path

            # Set the post's URL so all templates/feeds reflect the configured scheme.
            relative = output_path.relative_to(self.site_config.output_dir)
            url_path = "/" + relative.as_posix()

            # Apply clean URL transformation: strip index filenames (e.g.
            # "index.html") from paths so the URL ends with a trailing slash.
            if self.site_config.clean_urls:
                url_path = make_url_clean(url_path)

            post.url_path = url_path

            path_to_post_ids[str(output_path)].append(id(post))

        # Detect and warn about path clashes.
        for path_str, clashing_ids in path_to_post_ids.items():
            if len(clashing_ids) > 1:
                clashing_posts = [post_by_id[pid] for pid in clashing_ids]
                winner = clashing_posts[0]  # newest (list is sorted newest-first)
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
    ) -> None:
        """Generate a single post page.

        Args:
            post: The post to generate a page for.
            all_posts: All posts (sorted newest first), used for prev/next navigation.
            pages: All static pages, passed to the template context.
            output_path: The pre-resolved absolute output file path for this post.
        """
        context = self._get_global_context()
        context["all_posts"] = all_posts
        context["pages"] = pages

        # Find previous and next posts in chronological order
        # all_posts is already sorted by date (newest first)
        try:
            current_index = all_posts.index(post)
            # Previous post is older (higher index)
            context["prev_post"] = (
                all_posts[current_index + 1]
                if current_index + 1 < len(all_posts)
                else None
            )
            # Next post is newer (lower index)
            context["next_post"] = (
                all_posts[current_index - 1] if current_index > 0 else None
            )
        except ValueError:
            # Post not in list, no navigation
            context["prev_post"] = None
            context["next_post"] = None

        output_path.parent.mkdir(parents=True, exist_ok=True)
        # When clean URLs are enabled, post.url already has index.html stripped;
        # use it directly so the canonical URL matches what we advertise everywhere.
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

    def _resolve_sidebar_pages(self, pages: list[Page]) -> list[Page]:
        """Resolve which pages appear in the sidebar and in what order.

        When ``site_config.sidebar_pages`` is ``None`` or empty every page in
        ``pages`` is returned unchanged (the default behaviour).  When a list
        of slugs is provided, only pages whose slug appears in that list are
        returned, in the order defined by the list.  Slugs that do not match
        any existing page are silently ignored.

        Args:
            pages: All parsed static pages.

        Returns:
            The ordered list of pages to display in the sidebar.
        """
        if not self.site_config.sidebar_pages:
            return pages

        pages_by_slug: dict[str, Page] = {page.slug: page for page in pages}
        return [
            pages_by_slug[slug]
            for slug in self.site_config.sidebar_pages
            if slug in pages_by_slug
        ]

    def _resolve_page_output_paths(self, pages: list[Page]) -> dict[int, Path]:
        """Resolve the output path for every static page.

        For each page the method:

        1. Computes the absolute output file path using the configured
           ``page_path`` template.
        2. Sets ``page.url_path`` so that templates always use the correct URL
           regardless of the configured format.

        Args:
            pages: All static pages to resolve paths for.

        Returns:
            Mapping from ``id(page)`` to the page's resolved output path.
        """
        page_output_paths: dict[int, Path] = {}

        for page in pages:
            output_path = compute_page_output_path(
                self.site_config.output_dir, page, self.site_config.page_path
            )
            page_output_paths[id(page)] = output_path

            # Set the page's URL so all templates reflect the configured scheme.
            relative = output_path.relative_to(self.site_config.output_dir)
            url_path = "/" + relative.as_posix()

            # Apply clean URL transformation: strip index filenames (e.g.
            # "index.html") from paths so the URL ends with a trailing slash.
            if self.site_config.clean_urls:
                url_path = make_url_clean(url_path)

            page.url_path = url_path

        return page_output_paths

    def _generate_page(self, page: Page, pages: list[Page], output_path: Path) -> None:
        """Generate a single static page.

        Args:
            page: The static page to generate.
            pages: All static pages, passed to the template context.
            output_path: The pre-resolved absolute output file path for this page.
        """
        context = self._get_global_context()
        context["pages"] = pages

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # When clean URLs are enabled, page.url already has index.html stripped;
        # use it directly so the canonical URL matches what we advertise everywhere.
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{page.url}"
                if self.site_config.site_url
                else page.url
            )
        else:
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
        """Generate the main index page with pagination.

        Page 1 of the main index is always written to ``index.html`` at the
        output root, regardless of the ``page_1_path`` configuration.  This
        guarantees that the site always has a root ``index.html``.  The
        ``page_1_path`` setting still applies to all other paginated sections
        (archives, tags, categories).  Pages 2 and above of the main index
        use ``page_n_path`` as configured.
        """
        context = self._get_global_context()
        context["pages"] = pages

        # Paginate posts
        paginated_posts = paginate_posts(posts, self.POSTS_PER_PAGE_INDEX)
        if not paginated_posts:
            paginated_posts = [[]]  # Empty page if no posts

        total_pages = len(paginated_posts)

        # Page 1 of the main index is always /index.html (with clean_urls: /)
        # regardless of page_1_path, so that the site root is never displaced.
        page1_url: str = "/index.html"
        if self.site_config.clean_urls:
            page1_url = make_url_clean(page1_url)
        page_urls = [page1_url] + [
            self._get_pagination_url("", page_num)
            for page_num in range(2, total_pages + 1)
        ]

        # Generate each page
        for page_num, page_posts in enumerate(paginated_posts, start=1):
            if page_num == 1:
                output_path = self.site_config.output_dir / "index.html"
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = self._get_pagination_output_path(
                    self.site_config.output_dir, page_num
                )
            context["canonical_url"] = self._canonical_url_for_path(output_path)
            prev_url, next_url = self._pagination_prev_next(page_num, page_urls)
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
        archive_url = self._get_archive_url()
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
        """Generate date-based archive pages (year, month, day) with pagination."""
        # Group posts by year, month, and day
        posts_by_year: dict[int, list[Post]] = defaultdict(list)
        posts_by_month: dict[tuple[int, int], list[Post]] = defaultdict(list)
        posts_by_day: dict[tuple[int, int, int], list[Post]] = defaultdict(list)

        for post in posts:
            if post.date:
                year = post.date.year
                month = post.date.month
                day = post.date.day

                posts_by_year[year].append(post)
                posts_by_month[(year, month)].append(post)
                posts_by_day[(year, month, day)].append(post)

        context = self._get_global_context()
        context["pages"] = pages

        # Generate year archives with pagination
        for year, year_posts in posts_by_year.items():
            year_dir = self.site_config.output_dir / str(year)
            year_dir.mkdir(parents=True, exist_ok=True)

            # Paginate posts
            paginated_posts = paginate_posts(year_posts, self.POSTS_PER_PAGE_ARCHIVE)
            total_pages = len(paginated_posts)
            base_path = f"/{year}"
            page_urls = self._build_pagination_page_urls(base_path, total_pages)

            # Generate each page
            for page_num, page_posts in enumerate(paginated_posts, start=1):
                output_path = self._get_pagination_output_path(year_dir, page_num)
                context["canonical_url"] = self._canonical_url_for_path(output_path)
                prev_url, next_url = self._pagination_prev_next(page_num, page_urls)
                context["prev_page_url"] = prev_url
                context["next_page_url"] = next_url
                context["pagination_page_urls"] = page_urls
                html = self.renderer.render_archive(
                    page_posts,
                    archive_title=f"Posts from {year}",
                    page=page_num,
                    total_pages=total_pages,
                    base_path=base_path,
                    **context,
                )

                self._write_html(output_path, html)

        # Generate month archives with pagination
        for (year, month), month_posts in posts_by_month.items():
            month_dir = self.site_config.output_dir / str(year) / f"{month:02d}"
            month_dir.mkdir(parents=True, exist_ok=True)

            month_name = dt.datetime(year, month, 1).strftime("%B %Y")

            # Paginate posts
            paginated_posts = paginate_posts(month_posts, self.POSTS_PER_PAGE_ARCHIVE)
            total_pages = len(paginated_posts)
            base_path = f"/{year}/{month:02d}"
            page_urls = self._build_pagination_page_urls(base_path, total_pages)

            # Generate each page
            for page_num, page_posts in enumerate(paginated_posts, start=1):
                output_path = self._get_pagination_output_path(month_dir, page_num)
                context["canonical_url"] = self._canonical_url_for_path(output_path)
                prev_url, next_url = self._pagination_prev_next(page_num, page_urls)
                context["prev_page_url"] = prev_url
                context["next_page_url"] = next_url
                context["pagination_page_urls"] = page_urls
                html = self.renderer.render_archive(
                    page_posts,
                    archive_title=f"Posts from {month_name}",
                    page=page_num,
                    total_pages=total_pages,
                    base_path=base_path,
                    **context,
                )

                self._write_html(output_path, html)

        # Generate day archives with pagination
        for (year, month, day), day_posts in posts_by_day.items():
            day_dir = (
                self.site_config.output_dir / str(year) / f"{month:02d}" / f"{day:02d}"
            )
            day_dir.mkdir(parents=True, exist_ok=True)

            date_str = dt.datetime(year, month, day).strftime("%B %d, %Y")

            # Paginate posts
            paginated_posts = paginate_posts(day_posts, self.POSTS_PER_PAGE_ARCHIVE)
            total_pages = len(paginated_posts)
            base_path = f"/{year}/{month:02d}/{day:02d}"
            page_urls = self._build_pagination_page_urls(base_path, total_pages)

            # Generate each page
            for page_num, page_posts in enumerate(paginated_posts, start=1):
                output_path = self._get_pagination_output_path(day_dir, page_num)
                context["canonical_url"] = self._canonical_url_for_path(output_path)
                prev_url, next_url = self._pagination_prev_next(page_num, page_urls)
                context["prev_page_url"] = prev_url
                context["next_page_url"] = next_url
                context["pagination_page_urls"] = page_urls
                html = self.renderer.render_archive(
                    page_posts,
                    archive_title=f"Posts from {date_str}",
                    page=page_num,
                    total_pages=total_pages,
                    base_path=base_path,
                    **context,
                )

                self._write_html(output_path, html)

    def _generate_tag_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each tag with pagination."""
        # Group posts by tag (case-insensitive)
        # Key is lowercase tag, value is (display_name, posts)
        posts_by_tag = self._group_posts_by_tag(posts)

        # Create tag directory
        tag_dir = self.site_config.output_dir / self.TAG_DIR
        tag_dir.mkdir(exist_ok=True)

        # Generate paginated pages for each tag
        for tag_lower, (tag_display, tag_posts) in posts_by_tag.items():
            # Sort tag posts by date (newest first)
            tag_posts.sort(key=post_sort_key, reverse=True)

            # Sanitize tag for filename (use lowercase version)
            safe_tag = sanitize_for_url(tag_lower)

            # Paginate posts
            paginated_posts = paginate_posts(tag_posts, self.POSTS_PER_PAGE_TAG)
            total_pages = len(paginated_posts)

            base_url = f"/{self.TAG_DIR}/{safe_tag}"
            # Each tag's pages live inside tag/{safe_tag}/ directory.
            tag_base_dir = tag_dir / safe_tag
            page_urls = self._build_pagination_page_urls(base_url, total_pages)

            context = self._get_global_context()
            context["pages"] = pages

            # Generate each page
            for page_num, page_posts in enumerate(paginated_posts, start=1):
                output_path = self._get_pagination_output_path(tag_base_dir, page_num)
                context["canonical_url"] = self._canonical_url_for_path(output_path)
                prev_url, next_url = self._pagination_prev_next(page_num, page_urls)
                context["prev_page_url"] = prev_url
                context["next_page_url"] = next_url
                context["pagination_page_urls"] = page_urls
                html = self.renderer.render_tag_page(
                    tag_display,  # Use display name for rendering
                    page_posts,
                    page=page_num,
                    total_pages=total_pages,
                    safe_tag=safe_tag,
                    **context,
                )

                self._write_html(output_path, html)

    def _group_posts_by_tag(
        self, posts: list[Post]
    ) -> dict[str, tuple[str, list[Post]]]:
        """Group posts by tag (case-insensitive).

        Args:
            posts: List of posts to group

        Returns:
            Dictionary mapping lowercase tag to (display_name, posts)
        """
        posts_by_tag: dict[str, tuple[str, list[Post]]] = {}
        for post in posts:
            if post.tags:
                for tag in post.tags:
                    tag_lower = tag.lower()
                    if tag_lower not in posts_by_tag:
                        # Store the first occurrence as the display name
                        posts_by_tag[tag_lower] = (tag, [])
                    posts_by_tag[tag_lower][1].append(post)
        return posts_by_tag

    def _generate_tags_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the tags overview page with word cloud."""
        # Group posts by tag to get counts
        posts_by_tag = self._group_posts_by_tag(posts)

        if not posts_by_tag:
            # No tags, skip generation
            return

        # Calculate tag counts and prepare data
        tag_data: list[dict[str, Any]] = []
        min_count: int | None = None
        max_count: int | None = None

        for tag_lower, (tag_display, tag_posts) in posts_by_tag.items():
            count = len(tag_posts)
            safe_tag = sanitize_for_url(tag_lower)
            tag_data.append(
                {
                    "display_name": tag_display,
                    "safe_tag": safe_tag,
                    "count": count,
                    "tag_lower": tag_lower,
                }
            )
            if min_count is None or count < min_count:
                min_count = count
            if max_count is None or count > max_count:
                max_count = count

        # Sort alphabetically by display name
        tag_data.sort(key=lambda x: x["display_name"].lower())

        # Calculate font sizes for word cloud effect
        # Font sizes range from 1.0em to 2.5em
        min_font_size = 1.0
        max_font_size = 2.5

        # min_count and max_count are guaranteed to be set since posts_by_tag is non-empty
        assert min_count is not None
        assert max_count is not None

        if max_count > min_count:
            # Scale based on count
            for tag_info in tag_data:
                # Linear interpolation between min and max font size
                ratio = (tag_info["count"] - min_count) / (max_count - min_count)
                tag_info["font_size"] = min_font_size + ratio * (
                    max_font_size - min_font_size
                )
        else:
            # All tags have the same count, use middle size
            for tag_info in tag_data:
                tag_info["font_size"] = (min_font_size + max_font_size) / 2

        # Render the tags page
        context = self._get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.tags_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tags_url = self._get_tags_url()
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

    def _generate_categories_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the categories overview page with word cloud."""
        # Group posts by category to get counts
        posts_by_category = self._group_posts_by_category(posts)

        if not posts_by_category:
            # No categories, skip generation
            return

        # Calculate category counts and prepare data
        category_data: list[dict[str, Any]] = []
        min_count: int | None = None
        max_count: int | None = None

        for category_lower, (
            category_display,
            category_posts,
        ) in posts_by_category.items():
            count = len(category_posts)
            safe_category = sanitize_for_url(category_lower)
            category_data.append(
                {
                    "display_name": category_display,
                    "safe_category": safe_category,
                    "count": count,
                    "category_lower": category_lower,
                }
            )
            if min_count is None or count < min_count:
                min_count = count
            if max_count is None or count > max_count:
                max_count = count

        # Sort alphabetically by display name
        category_data.sort(key=lambda x: x["display_name"].lower())

        # Calculate font sizes for word cloud effect
        # Font sizes range from 1.0em to 2.5em
        min_font_size = 1.0
        max_font_size = 2.5

        # min_count and max_count are guaranteed to be set since posts_by_category is non-empty
        assert min_count is not None
        assert max_count is not None

        if max_count > min_count:
            # Scale based on count
            for category_info in category_data:
                # Linear interpolation between min and max font size
                ratio = (category_info["count"] - min_count) / (max_count - min_count)
                category_info["font_size"] = min_font_size + ratio * (
                    max_font_size - min_font_size
                )
        else:
            # All categories have the same count, use middle size
            for category_info in category_data:
                category_info["font_size"] = (min_font_size + max_font_size) / 2

        # Render the categories page
        context = self._get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.categories_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        categories_url = self._get_categories_url()
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

    def _generate_category_pages(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate pages for each category with pagination."""
        # Group posts by category (case-insensitive)
        # Key is lowercase category, value is (display_name, posts)
        posts_by_category = self._group_posts_by_category(posts)

        # Create category directory
        category_dir = self.site_config.output_dir / self.CATEGORY_DIR
        category_dir.mkdir(exist_ok=True)

        # Generate paginated pages for each category
        for category_lower, (
            category_display,
            category_posts,
        ) in posts_by_category.items():
            # Sort category posts by date (newest first)
            category_posts.sort(key=post_sort_key, reverse=True)

            # Sanitize category for filename (use lowercase version)
            safe_category = sanitize_for_url(category_lower)

            # Paginate posts
            paginated_posts = paginate_posts(
                category_posts, self.POSTS_PER_PAGE_CATEGORY
            )
            total_pages = len(paginated_posts)

            base_url = f"/{self.CATEGORY_DIR}/{safe_category}"
            # Each category's pages live inside category/{safe_category}/ directory.
            category_base_dir = category_dir / safe_category
            page_urls = self._build_pagination_page_urls(base_url, total_pages)

            context = self._get_global_context()
            context["pages"] = pages

            # Generate each page
            for page_num, page_posts in enumerate(paginated_posts, start=1):
                output_path = self._get_pagination_output_path(
                    category_base_dir, page_num
                )
                context["canonical_url"] = self._canonical_url_for_path(output_path)
                prev_url, next_url = self._pagination_prev_next(page_num, page_urls)
                context["prev_page_url"] = prev_url
                context["next_page_url"] = next_url
                context["pagination_page_urls"] = page_urls
                html = self.renderer.render_category_page(
                    category_display,  # Use display name for rendering
                    page_posts,
                    page=page_num,
                    total_pages=total_pages,
                    safe_category=safe_category,
                    **context,
                )

                self._write_html(output_path, html)

    def _group_posts_by_category(
        self, posts: list[Post]
    ) -> dict[str, tuple[str, list[Post]]]:
        """Group posts by category (case-insensitive).

        Args:
            posts: List of posts to group

        Returns:
            Dictionary mapping lowercase category to (display_name, posts)
        """
        posts_by_category: dict[str, tuple[str, list[Post]]] = {}
        for post in posts:
            if post.category:
                category_lower = post.category.lower()
                if category_lower not in posts_by_category:
                    # Store the first occurrence as the display name
                    posts_by_category[category_lower] = (post.category, [])
                posts_by_category[category_lower][1].append(post)
        return posts_by_category

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
        posts_by_category = self._group_posts_by_category(posts)
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
        context = self._get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.search_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        search_url = self._get_search_url()
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
        containing an entry for every generated HTML page except
        ``search.html``.
        """
        write_sitemap(
            self.site_config.output_dir,
            self.site_config.site_url,
            clean_urls=self.site_config.clean_urls,
        )

    def _copy_static_assets(self) -> None:
        """Copy static assets (CSS, JS, images) to output directory.

        When ``minify_css`` is enabled, the ``style.css`` file is minified and
        written as ``styles.min.css``; the original ``style.css`` is not written.

        When ``minify_js`` is enabled, the ``theme.js`` file is minified and
        written as ``theme.min.js`` (and ``search.js`` as ``search.min.js`` if
        search is enabled); the originals are not written.
        """
        output_static = self.site_config.output_dir / "static"

        # Clear output static directory if it exists
        if output_static.exists():
            shutil.rmtree(output_static)
        output_static.mkdir(parents=True, exist_ok=True)

        # First, copy bundled static assets
        try:
            # Get bundled static directory
            bundled_static = files("blogmore").joinpath("templates", "static")
            if bundled_static.is_dir():
                for item in bundled_static.iterdir():
                    if item.is_file():
                        # Only copy search.js when search is enabled
                        if (
                            item.name == SEARCH_JS_FILENAME
                            and not self.site_config.with_search
                        ):
                            continue
                        # When minifying CSS, skip the original style.css
                        if item.name == CSS_FILENAME and self.site_config.minify_css:
                            continue
                        # When minifying JS, skip original JS files
                        if (
                            item.name == THEME_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            item.name == SEARCH_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            item.name == CODEBLOCKS_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        # Read content and write to output
                        content = item.read_bytes()
                        output_file = output_static / item.name
                        output_file.write_bytes(content)
                print("Copied bundled static assets")
        except Exception as e:
            print(f"Warning: Could not copy bundled static assets: {e}")

        # Then, copy custom static assets (if provided), which will override bundled ones
        if self.site_config.templates_dir is not None:
            custom_static_dir = self.site_config.templates_dir / "static"
            if custom_static_dir.exists():
                for item in custom_static_dir.rglob("*"):
                    if item.is_file():
                        relative_path = item.relative_to(custom_static_dir)
                        # When minifying CSS, skip the original style.css from custom dir too
                        if (
                            relative_path.name == CSS_FILENAME
                            and self.site_config.minify_css
                        ):
                            continue
                        # When minifying JS, skip original JS files from custom dir too
                        if (
                            relative_path.name == THEME_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            relative_path.name == SEARCH_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        if (
                            relative_path.name == CODEBLOCKS_JS_FILENAME
                            and self.site_config.minify_js
                        ):
                            continue
                        output_file = output_static / relative_path
                        output_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, output_file)
                print(f"Copied custom static assets from {custom_static_dir}")

        # Minify CSS if requested
        if self.site_config.minify_css:
            self._write_minified_css(output_static)

        # Minify JS if requested
        if self.site_config.minify_js:
            self._write_minified_js(
                output_static, THEME_JS_FILENAME, THEME_JS_MINIFIED_FILENAME
            )
            self._write_minified_js(
                output_static, CODEBLOCKS_JS_FILENAME, CODEBLOCKS_JS_MINIFIED_FILENAME
            )
            if self.site_config.with_search:
                self._write_minified_js(
                    output_static, SEARCH_JS_FILENAME, SEARCH_JS_MINIFIED_FILENAME
                )

    def _copy_extras(self) -> None:
        """Copy extra files from the extras directory to the output directory.

        Files in the extras directory are copied to the output root, preserving
        directory structure relative to the extras directory. If a file would
        override an existing file, it is allowed but a message is printed.
        """
        extras_dir = self._content_dir / "extras"

        if not extras_dir.exists():
            return

        # Count how many extras we copy
        extras_count = 0
        override_count = 0
        failed_count = 0

        # Recursively copy all files from the extras directory
        for file_path in extras_dir.rglob("*"):
            # Skip directories
            if file_path.is_file():
                try:
                    # Calculate relative path from extras directory to preserve structure
                    relative_path = file_path.relative_to(extras_dir)
                    # Copy to output_dir root, preserving directory structure
                    output_path = self.site_config.output_dir / relative_path

                    # Check if file already exists
                    file_exists = output_path.exists()

                    # Create parent directories if they don't exist
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file preserving metadata
                    shutil.copy2(file_path, output_path)
                    extras_count += 1

                    # Print message if we overrode an existing file
                    if file_exists:
                        print(f"Overriding existing file: {relative_path}")
                        override_count += 1
                except (OSError, PermissionError) as e:
                    print(f"Warning: Failed to copy extra file {file_path}: {e}")
                    failed_count += 1
                    continue

        if extras_count > 0:
            print(f"Copied {extras_count} extra file(s) from {extras_dir}")
        if override_count > 0:
            print(f"Overrode {override_count} existing file(s)")
        if failed_count > 0:
            print(f"Warning: Failed to copy {failed_count} extra file(s)")
