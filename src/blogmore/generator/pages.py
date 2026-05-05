"""Core HTML page generation for the site generator."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

from blogmore.backlinks import Backlink
from blogmore.clean_url import make_url_clean
from blogmore.comment_invite import build_mailto_url, get_invite_email_for_post
from blogmore.generator.html import write_html
from blogmore.generator.paths import (
    canonical_url_for_path,
    get_pagination_output_path,
    get_pagination_url,
    pagination_prev_next,
)
from blogmore.generator.utils import paginate_posts
from blogmore.parser import CUSTOM_404_HTML, Page, Post

if TYPE_CHECKING:
    from blogmore.generator.context import ContextBuilder
    from blogmore.renderer import TemplateRenderer
    from blogmore.site_config import SiteConfig


class PageGenerator:
    """Generates each type of HTML page written to the output directory."""

    POSTS_PER_PAGE_INDEX: Final[int] = 10
    """The number of posts to show per page on the main index page."""

    def __init__(
        self,
        site_config: SiteConfig,
        renderer: TemplateRenderer,
        context_builder: ContextBuilder,
    ) -> None:
        """Initialize the page generator.

        Args:
            site_config: The site configuration.
            renderer: The template renderer.
            context_builder: The context builder.
        """
        self.site_config = site_config
        self.renderer = renderer
        self.context_builder = context_builder

    def generate_post_page(
        self,
        post: Post,
        all_posts: list[Post],
        pages: list[Page],
        output_path: Path,
        backlinks_map: dict[str, list[Backlink]] | None = None,
    ) -> None:
        """Generate a single post page.

        Args:
            post: The post to generate a page for.
            all_posts: All posts (sorted newest first), used for prev/next navigation.
            pages: All static pages, passed to the template context.
            output_path: The pre-resolved absolute output file path for this post.
            backlinks_map: Optional mapping from post URL to list of Backlink
                objects, built when ``with_backlinks`` is enabled.
        """
        context = self.context_builder.get_global_context()
        context["all_posts"] = all_posts
        context["pages"] = pages

        # Attach the backlinks list for this post to the template context.
        context["backlinks"] = backlinks_map.get(post.url, []) if backlinks_map else []

        # Compute the comment invitation mailto URL for this post.
        invite_email = get_invite_email_for_post(
            post,
            self.site_config.invite_comments,
            self.site_config.invite_comments_to,
        )
        context["invite_comments_mailto"] = (
            build_mailto_url(invite_email, post.title) if invite_email else None
        )

        # Find previous and next posts in chronological order
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
            context["canonical_url"] = canonical_url_for_path(
                self.site_config, output_path
            )

        html = self.renderer.render_post(post, **context)
        write_html(output_path, html, self.site_config.minify_html)

    def generate_page(self, page: Page, pages: list[Page], output_path: Path) -> None:
        """Generate a single static page.

        Args:
            page: The static page to generate.
            pages: All static pages, passed to the template context.
            output_path: The pre-resolved absolute output file path for this page.
        """
        context = self.context_builder.get_global_context()
        context["pages"] = pages

        output_path.parent.mkdir(parents=True, exist_ok=True)
        context["canonical_url"] = canonical_url_for_path(self.site_config, output_path)

        html = self.renderer.render_page(page, **context)
        write_html(output_path, html, self.site_config.minify_html)

    def generate_404_page(self, page: Page, pages: list[Page]) -> None:
        """Generate the custom 404 page in the root of the output directory.

        Args:
            page: The 404 page content to render.
            pages: All static pages, passed to the template context.
        """
        context = self.context_builder.get_global_context()
        context["pages"] = pages
        output_path = self.site_config.output_dir / CUSTOM_404_HTML
        context["canonical_url"] = canonical_url_for_path(self.site_config, output_path)

        html = self.renderer.render_page(page, **context)
        write_html(output_path, html, self.site_config.minify_html)

    def generate_index_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the main index page with pagination.

        Page 1 of the main index is always written to ``index.html`` at the
        output root, regardless of the ``page_1_path`` configuration.

        Args:
            posts: All published posts, sorted newest first.
            pages: All static pages, for sidebar navigation.
        """
        context = self.context_builder.get_global_context()
        context["pages"] = pages

        # Paginate posts
        paginated_posts = paginate_posts(posts, self.POSTS_PER_PAGE_INDEX)
        if not paginated_posts:
            paginated_posts = [[]]  # Empty page if no posts

        total_pages = len(paginated_posts)

        # Page 1 of the main index is always /index.html (with clean_urls: /)
        page1_url: str = "/index.html"
        if self.site_config.clean_urls:
            page1_url = make_url_clean(page1_url)

        page_urls = [page1_url] + [
            get_pagination_url(self.site_config, "", page_num)
            for page_num in range(2, total_pages + 1)
        ]

        # Generate each page
        for page_num, page_posts in enumerate(paginated_posts, start=1):
            if page_num == 1:
                output_path = self.site_config.output_dir / "index.html"
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = get_pagination_output_path(
                    self.site_config, self.site_config.output_dir, page_num
                )

            context["canonical_url"] = canonical_url_for_path(
                self.site_config, output_path
            )
            prev_url, next_url = pagination_prev_next(page_num, page_urls)
            context["prev_page_url"] = prev_url
            context["next_page_url"] = next_url
            context["pagination_page_urls"] = page_urls
            html = self.renderer.render_index(
                page_posts, page=page_num, total_pages=total_pages, **context
            )

            write_html(output_path, html, self.site_config.minify_html)

    def generate_archive_page(self, posts: list[Post], pages: list[Page]) -> None:
        """Generate the archive page.

        Args:
            posts: All published posts.
            pages: All static pages, for sidebar navigation.
        """
        context = self.context_builder.get_global_context()
        context["pages"] = pages
        output_path = (
            self.site_config.output_dir / self.site_config.archive_path.lstrip("/")
        ).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        archive_url = self.context_builder.get_archive_url()
        if self.site_config.clean_urls:
            context["canonical_url"] = (
                f"{self.site_config.site_url}{archive_url}"
                if self.site_config.site_url
                else archive_url
            )
        else:
            context["canonical_url"] = canonical_url_for_path(
                self.site_config, output_path
            )

        html = self.renderer.render_archive(
            posts, page=1, total_pages=1, base_path="/archive", **context
        )
        write_html(output_path, html, self.site_config.minify_html)
