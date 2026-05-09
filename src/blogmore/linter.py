"""Linting logic for blogmore."""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlparse

from blogmore.generator.constants import CATEGORY_DIR, TAG_DIR
from blogmore.generator.context import ContextBuilder
from blogmore.generator.grouping import group_posts_by_category, group_posts_by_tag
from blogmore.generator.paths import (
    resolve_page_output_paths,
    resolve_post_output_paths,
)
from blogmore.parser import PostParser, sanitize_for_url

if TYPE_CHECKING:
    from blogmore.site_config import SiteConfig


class Linter:
    """Checks a blogmore site for common issues."""

    def __init__(self, site_config: SiteConfig) -> None:
        """Initialize the linter.

        Args:
            site_config: The site configuration.
        """
        self.site_config = site_config
        self.parser = PostParser(site_url=site_config.site_url)
        self.errors = 0
        self.warnings = 0

        # Parse the site URL to get the domain for external link detection
        self.site_domain: str | None = None
        if site_config.site_url:
            parsed = urlparse(site_config.site_url)
            self.site_domain = parsed.netloc.lower()

    def report_error(self, message: str, path: Path | None = None) -> None:
        """Report an error.

        Args:
            message: The error message.
            path: Optional path to the file with the error.
        """
        prefix = f"{path}: " if path else ""
        print(f"ERROR: {prefix}{message}", file=sys.stderr)
        self.errors += 1

    def report_warning(self, message: str, path: Path | None = None) -> None:
        """Report a warning.

        Args:
            message: The warning message.
            path: Optional path to the file with the warning.
        """
        prefix = f"{path}: " if path else ""
        print(f"WARNING: {prefix}{message}", file=sys.stderr)
        self.warnings += 1

    def _is_external_link(self, href: str) -> bool:
        """Determine if a link is external."""
        # Relative links (starting with /, #, or no scheme) are internal
        if href.startswith(("/", "#")):
            return False

        # Parse the URL
        parsed = urlparse(href)

        # If there's no scheme and no netloc, it's a relative link (internal)
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

    def lint(self) -> int:
        """Perform linting on the site.

        Returns:
            0 if no errors, 1 if errors were found.
        """
        content_dir = self.site_config.content_dir
        assert content_dir is not None

        print(f"Linting site in {content_dir}...")

        # 1. Parse all pages & posts
        pages_dir = content_dir / "pages"

        # We'll parse manually to catch errors
        pages = []
        if pages_dir.exists():
            for md_file in pages_dir.rglob("*.md"):
                try:
                    page = self.parser.parse_page(md_file)
                    pages.append(page)
                except (ValueError, FileNotFoundError) as e:
                    self.report_error(f"Malformed frontmatter: {e}", md_file)

        page_404 = None
        path_404 = pages_dir / "404.md"
        if path_404.exists():
            try:
                page_404 = self.parser.parse_page(path_404)
            except (ValueError, FileNotFoundError) as e:
                self.report_error(f"Malformed 404 page frontmatter: {e}", path_404)

        posts = []
        for md_file in content_dir.rglob("*.md"):
            # Skip pages directory
            if md_file.resolve().is_relative_to(pages_dir.resolve()):
                continue
            # Skip 404.md if it's in the root (though it should be in pages/)
            if md_file.name == "404.md":
                continue

            try:
                post = self.parser.parse_file(md_file)
                posts.append(post)
            except (ValueError, FileNotFoundError) as e:
                self.report_error(f"Malformed frontmatter: {e}", md_file)

        if not posts and not pages:
            print("No posts or pages found to lint.")
            return 1 if self.errors > 0 else 0

        # Resolve paths to set .url_path on posts/pages
        resolve_post_output_paths(self.site_config, posts)
        resolve_page_output_paths(self.site_config, pages)

        # 2. Check for future dates
        now = dt.datetime.now(dt.UTC)
        for post in posts:
            if post.date:
                post_date = post.date
                if post_date.tzinfo is None:
                    post_date = post_date.replace(tzinfo=dt.UTC)
                if post_date > now:
                    self.report_warning(
                        f"Post date is in the future: {post.date}", post.path
                    )

            if post.modified_date:
                mod_date = post.modified_date
                if mod_date.tzinfo is None:
                    mod_date = mod_date.replace(tzinfo=dt.UTC)
                if mod_date > now:
                    self.report_warning(
                        f"Post modified date is in the future: {post.modified_date}",
                        post.path,
                    )

        # 3. Build set of valid internal URLs
        valid_urls: set[str] = set()

        # Posts and Pages
        for post in posts:
            valid_urls.add(post.url)
        for page in pages:
            valid_urls.add(page.url)
        if page_404:
            valid_urls.add(page_404.url)

        # Special pages
        cb = ContextBuilder(self.site_config)
        valid_urls.add(cb.get_archive_url())
        valid_urls.add(cb.get_tags_url())
        valid_urls.add(cb.get_categories_url())
        if self.site_config.with_search:
            valid_urls.add(cb.get_search_url())
        if self.site_config.with_stats:
            valid_urls.add(cb.get_stats_url())
        if self.site_config.with_calendar:
            valid_urls.add(cb.get_calendar_url())
        if self.site_config.with_graph:
            valid_urls.add(cb.get_graph_url())

        # Main index and archive
        valid_urls.add("/index.html")
        valid_urls.add("/archive.html")
        if self.site_config.clean_urls:
            valid_urls.add("/")
            valid_urls.add("/archive/")

        # Tag and Category pages
        posts_by_tag = group_posts_by_tag(posts)
        for tag_lower in posts_by_tag:
            safe_tag = sanitize_for_url(tag_lower)
            url = (
                f"/{TAG_DIR}/{safe_tag}/"
                if self.site_config.clean_urls
                else f"/{TAG_DIR}/{safe_tag}.html"
            )
            valid_urls.add(url)

        posts_by_category = group_posts_by_category(posts)
        for cat_lower in posts_by_category:
            safe_cat = sanitize_for_url(cat_lower)
            url = (
                f"/{CATEGORY_DIR}/{safe_cat}/"
                if self.site_config.clean_urls
                else f"/{CATEGORY_DIR}/{safe_cat}.html"
            )
            valid_urls.add(url)

        # Date archives (Year, Month, Day)
        for post in posts:
            if post.date:
                y, m, d = post.date.year, post.date.month, post.date.day
                urls = [f"/{y}/", f"/{y}/{m:02d}/", f"/{y}/{m:02d}/{d:02d}/"]
                if not self.site_config.clean_urls:
                    urls = [f"{u}index.html" for u in urls]
                valid_urls.update(urls)

        # Feeds
        valid_urls.add("/feed.xml")
        valid_urls.add("/atom.xml")
        for cat_lower in posts_by_category:
            safe_cat = sanitize_for_url(cat_lower)
            valid_urls.add(f"/{CATEGORY_DIR}/{safe_cat}/feed.xml")
            valid_urls.add(f"/{CATEGORY_DIR}/{safe_cat}/atom.xml")

        # Sitemap
        if self.site_config.with_sitemap:
            valid_urls.add("/sitemap.xml")

        # Ignored URLs from config
        if self.site_config.linting_ignore:
            valid_urls.update(self.site_config.linting_ignore)

        # Extras
        extras_dir = content_dir / "extras"
        if extras_dir.exists():
            for p in extras_dir.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(extras_dir)
                    url = "/" + rel.as_posix()
                    valid_urls.add(url)
                    # If it's an index.html, also add the directory URL if clean_urls
                    if self.site_config.clean_urls and rel.name == "index.html":
                        valid_urls.add("/" + rel.parent.as_posix() + "/")

        # Static assets (bundled and custom)
        # We'll just assume /static/* is mostly valid if it exists in templates or bundled
        # but let's be a bit more specific for common ones.
        valid_urls.add("/static/style.css")
        valid_urls.add("/static/theme.js")
        # ... and others from ContextBuilder
        for _key, value in cb.get_global_context().items():
            if isinstance(value, str) and value.startswith("/static/"):
                # Remove cache bust token for matching
                url = value.split("?")[0]
                valid_urls.add(url)

        # 4. Check links in posts and pages
        all_items = [(p, "post") for p in posts] + [(p, "page") for p in pages]
        if page_404:
            all_items.append((page_404, "page"))

        for item, _type in all_items:
            html = item.html_content
            # Extract <a> hrefs
            links = re.findall(r'<a\s+(?:[^>]*?\s+)?href=["\']([^"\']*)["\']', html)
            # Extract <img> srcs
            images = re.findall(r'<img\s+(?:[^>]*?\s+)?src=["\']([^"\']*)["\']', html)

            for href in links:
                self._check_link(href, item, valid_urls)

            for src in images:
                self._check_link(src, item, valid_urls, is_image=True)

        print(f"Linting complete: {self.errors} error(s), {self.warnings} warning(s).")
        return 1 if self.errors > 0 else 0

    def _check_link(
        self, href: str, item: Any, valid_urls: set[str], is_image: bool = False
    ) -> None:
        """Check a single link or image source."""
        # Skip empty or external links
        if not href or self._is_external_link(href):
            return

        # Skip fragments
        if href.startswith("#"):
            return

        # Resolve relative link
        # item.url is something like /2024/01/01/my-post/ or /about.html
        base_url = item.url
        resolved = urljoin(base_url, href)

        # Remove query params and fragments from resolved URL
        parsed_resolved = urlparse(resolved)
        path_only = parsed_resolved.path

        # Normalization: if clean_urls is enabled, /some/path/index.html should be /some/path/
        if self.site_config.clean_urls and path_only.endswith("/index.html"):
            path_only = path_only[:-10]  # Remove index.html
            if not path_only.endswith("/"):
                path_only += "/"

        if path_only not in valid_urls:
            # Try with or without trailing slash
            alt_path = path_only[:-1] if path_only.endswith("/") else path_only + "/"
            if alt_path in valid_urls:
                return

            link_type = "Image" if is_image else "Link"
            self.report_error(
                f"{link_type} points to non-existent internal path: {href} (resolved to {path_only})",
                item.path,
            )


def lint_site(site_config: SiteConfig) -> int:
    """Convenience function to run the linter.

    Args:
        site_config: The site configuration.

    Returns:
        0 if no errors, 1 if errors were found.
    """
    linter = Linter(site_config)
    return linter.lint()
