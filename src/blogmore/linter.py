"""Content linting and validation for BlogMore.

Scans posts and pages for common issues before building, including broken
internal links, future dates, missing image assets, and frontmatter errors.
This module is used by the `blogmore lint` CLI command.
"""

##############################################################################
# Python imports.
import datetime as dt
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from urllib.parse import unquote

##############################################################################
# Local imports.
from blogmore.backlinks import extract_link_url, normalize_url_path, to_path
from blogmore.clean_url import make_url_clean
from blogmore.feeds import FEEDS_DIR
from blogmore.generator.constants import CATEGORY_DIR, TAG_DIR
from blogmore.generator.grouping import group_posts_by_category, group_posts_by_tag
from blogmore.markdown.link_patterns import (
    INLINE_IMAGE_RE as _INLINE_IMAGE_RE,
    INLINE_LINK_RE as _INLINE_LINK_RE,
    LINK_DEF_RE as _LINK_DEF_RE,
    REF_IMAGE_RE as _REF_IMAGE_RE,
    REF_LINK_RE as _REF_LINK_RE,
)
from blogmore.page_path import resolve_page_path
from blogmore.parser import Page, Post, PostParser, post_sort_key, sanitize_for_url
from blogmore.post_path import resolve_post_path
from blogmore.site_config import SiteConfig


##############################################################################
class IssueKind(StrEnum):
    """The kind of lint issue found in a content file.

    Each variant corresponds to one of the checks performed by
    [`SiteLinter`][blogmore.linter.SiteLinter].
    """

    FRONTMATTER_ERROR = "frontmatter-error"
    """A post or page failed to parse due to a frontmatter error."""

    BROKEN_INTERNAL_LINK = "broken-internal-link"
    """An internal link points to a URL that has no matching post or page."""

    FUTURE_DATE = "future-date"
    """A `date` or `modified` frontmatter value is in the future."""

    MISSING_IMAGE = "missing-image"
    """An internal image link has no corresponding file in the `extras/` directory."""


##############################################################################
@dataclass
class LintIssue:
    """A single lint issue found in a content file.

    Attributes:
        source_path: Absolute path to the file containing the issue.
        kind: The category of the issue.
        message: Human-readable description of the issue.
    """

    source_path: Path
    kind: IssueKind
    message: str


##############################################################################
@dataclass
class LintResult:
    """The aggregated result of linting a site's content.

    Attributes:
        issues: All lint issues found, in the order they were discovered.
    """

    issues: list[LintIssue] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        """Return `True` if any lint issues were found."""
        return bool(self.issues)

    @property
    def issue_count(self) -> int:
        """Return the total number of lint issues found."""
        return len(self.issues)


##############################################################################
def _is_relative_path(raw_url: str) -> bool:
    """Return `True` if *raw_url* is a bare relative path.

    A bare relative path is a URL that:

    - Does not start with `/` (not root-relative).
    - Does not start with `#` (not a same-page fragment anchor).
    - Does not contain `://` (not a full URL such as `https://`).
    - Does not look like a URI scheme (e.g. `mailto:`, `tel:`) — detected
      by the presence of `:` before the first `/`.

    Such paths resolve relative to the current page's URL in a browser,
    which almost always produces broken links in a static-site context where
    the content file's location does not match the output URL.

    Args:
        raw_url: The raw URL string as extracted from Markdown source.

    Returns:
        `True` if *raw_url* is a bare relative path, `False` otherwise.
    """
    # Strip fragment and query string before classification.
    without_fragment = raw_url.strip().split("#")[0]
    url = without_fragment.split("?")[0]
    if not url:
        return False
    if url.startswith("/") or url.startswith("#"):
        return False
    if "://" in url:
        return False
    # Reject URI schemes such as mailto:, tel:, javascript: — these have a
    # colon before the first slash (or have no slash at all).
    slash_pos = url.find("/")
    colon_pos = url.find(":")
    return not (colon_pos >= 0 and (slash_pos < 0 or colon_pos < slash_pos))


##############################################################################
def _find_regular_links(content: str) -> list[str]:
    """Extract all non-image internal-link candidate URLs from Markdown content.

    Finds inline links (`[text](url)`) and reference-style links
    (`[text][ref]`), excluding any that are image links (`![alt](url)`).

    Args:
        content: Raw Markdown source to scan.

    Returns:
        A list of raw URL strings extracted from non-image links.
    """
    results: list[str] = []

    # Collect reference link definitions first.
    refs: dict[str, str] = {}
    for definition in _LINK_DEF_RE.finditer(content):
        refs[definition.group(1).lower()] = definition.group(2).strip()

    # Inline (non-image) links: use negative lookbehind to skip ![…](url).
    for match in _INLINE_LINK_RE.finditer(content):
        url = extract_link_url(match.group(2))
        if url:
            results.append(url)

    # Reference-style (non-image) links: [text][ref] or [text][].
    for match in _REF_LINK_RE.finditer(content):
        ref_id = match.group(2).lower() or match.group(1).lower()
        url = refs.get(ref_id, "")
        if url:
            results.append(url)

    return results


##############################################################################
def _find_image_links(content: str) -> list[str]:
    """Extract all image link URLs from Markdown content.

    Finds inline image links (`![alt](url)`) and reference-style image links
    (`![alt][ref]`).

    Args:
        content: Raw Markdown source to scan.

    Returns:
        A list of raw URL strings extracted from image links (both inline and
        reference-style).
    """
    results: list[str] = []

    # Collect reference link definitions.
    refs: dict[str, str] = {}
    for definition in _LINK_DEF_RE.finditer(content):
        refs[definition.group(1).lower()] = definition.group(2).strip()

    # Inline image links: ![alt](url)
    for match in _INLINE_IMAGE_RE.finditer(content):
        url = extract_link_url(match.group(2))
        if url:
            results.append(url)

    # Reference-style image links: ![alt][ref] or ![alt][]
    for match in _REF_IMAGE_RE.finditer(content):
        ref_id = match.group(2).lower() or match.group(1).lower()
        url = refs.get(ref_id, "")
        if url:
            results.append(url)

    return results


##############################################################################
def _post_url(post: Post, post_path_template: str, clean_urls: bool) -> str:
    """Compute the URL path for a post using the configured path template.

    Args:
        post: The post to compute the URL for.
        post_path_template: The configured `post_path` format string.
        clean_urls: Whether to apply the clean-URL transformation.

    Returns:
        The root-relative URL for the post (always starts with `/`).
    """
    url_path = "/" + resolve_post_path(post, post_path_template)
    if clean_urls:
        url_path = make_url_clean(url_path)
    return url_path


##############################################################################
def _page_url(page: Page, page_path_template: str, clean_urls: bool) -> str:
    """Compute the URL path for a static page using the configured path template.

    Args:
        page: The page to compute the URL for.
        page_path_template: The configured `page_path` format string.
        clean_urls: Whether to apply the clean-URL transformation.

    Returns:
        The root-relative URL for the page (always starts with `/`).
    """
    url_path = "/" + resolve_page_path(page, page_path_template)
    if clean_urls:
        url_path = make_url_clean(url_path)
    return url_path


##############################################################################
class SiteLinter:
    """Lints blog content for common issues without generating the site.

    Parses all posts and pages in the content directory and checks them for:

    - Frontmatter parse errors (YAML syntax errors, missing required fields,
      invalid field values).
    - Internal links that have no corresponding post or page.
    - `date` and `modified` frontmatter values that are in the future.
    - Internal image links that have no corresponding file in the
      `extras/` directory.

    External links (those pointing to other domains) are never checked.
    """

    def __init__(self, site_config: SiteConfig) -> None:
        """Initialise the linter with a site configuration.

        Args:
            site_config: The site configuration to use for all linting
                parameters (content directory, URL configuration, feature
                flags, etc.).  The `content_dir` field is used as the root
                of the content tree; it may be `None` but in that case the
                linter will produce an empty result.
        """
        self._config = site_config

    @property
    def content_dir(self) -> Path | None:
        """The content directory from the site configuration."""
        return self._config.content_dir

    @property
    def site_url(self) -> str:
        """The site URL from the site configuration."""
        return self._config.site_url

    @property
    def include_drafts(self) -> bool:
        """Whether to include draft posts."""
        return self._config.include_drafts

    @property
    def post_path_template(self) -> str:
        """The post path template from the site configuration."""
        return self._config.post_path

    @property
    def page_path_template(self) -> str:
        """The page path template from the site configuration."""
        return self._config.page_path

    @property
    def clean_urls(self) -> bool:
        """Whether clean URLs are enabled."""
        return self._config.clean_urls

    @property
    def archive_path(self) -> str:
        """The archive page path from the site configuration."""
        return self._config.archive_path

    @property
    def tags_path(self) -> str:
        """The tags overview page path from the site configuration."""
        return self._config.tags_path

    @property
    def categories_path(self) -> str:
        """The categories overview page path from the site configuration."""
        return self._config.categories_path

    @property
    def search_path(self) -> str:
        """The search page path from the site configuration."""
        return self._config.search_path

    @property
    def stats_path(self) -> str:
        """The statistics page path from the site configuration."""
        return self._config.stats_path

    @property
    def calendar_path(self) -> str:
        """The calendar page path from the site configuration."""
        return self._config.calendar_path

    @property
    def graph_path(self) -> str:
        """The graph page path from the site configuration."""
        return self._config.graph_path

    @property
    def page_1_path(self) -> str:
        """The first-page pagination path template from the site configuration."""
        return self._config.page_1_path

    @property
    def with_search(self) -> bool:
        """Whether the search page is generated."""
        return self._config.with_search

    @property
    def with_stats(self) -> bool:
        """Whether the statistics page is generated."""
        return self._config.with_stats

    @property
    def with_calendar(self) -> bool:
        """Whether the calendar page is generated."""
        return self._config.with_calendar

    @property
    def with_graph(self) -> bool:
        """Whether the graph page is generated."""
        return self._config.with_graph

    # ------------------------------------------------------------------
    def _parse_all(
        self,
    ) -> tuple[list[Post], list[Page], list[LintIssue]]:
        """Parse all posts and pages, collecting frontmatter errors.

        Returns:
            A 3-tuple of ``(posts, pages, issues)`` where *posts* and
            *pages* are the successfully parsed content objects and *issues*
            contains one [`LintIssue`][blogmore.linter.LintIssue] per file that
            failed to parse.
        """
        if self.content_dir is None:
            return [], [], []

        parser = PostParser(site_url=self.site_url)
        pages_dir = self.content_dir / "pages"
        issues: list[LintIssue] = []

        # Parse posts, collecting per-file errors instead of raising.
        posts: list[Post] = []
        if self.content_dir.exists():
            for md_file in self.content_dir.rglob("*.md"):
                if md_file.resolve().is_relative_to(pages_dir.resolve()):
                    continue
                try:
                    post = parser.parse_file(md_file)
                    if post.draft and not self.include_drafts:
                        continue
                    posts.append(post)
                except (ValueError, FileNotFoundError) as exc:
                    issues.append(
                        LintIssue(
                            source_path=md_file,
                            kind=IssueKind.FRONTMATTER_ERROR,
                            message=str(exc),
                        )
                    )
        posts.sort(key=post_sort_key, reverse=True)

        # Parse pages, collecting per-file errors.
        pages: list[Page] = []
        if pages_dir.exists():
            for md_file in pages_dir.rglob("*.md"):
                try:
                    pages.append(parser.parse_page(md_file))
                except (ValueError, FileNotFoundError) as exc:
                    issues.append(
                        LintIssue(
                            source_path=md_file,
                            kind=IssueKind.FRONTMATTER_ERROR,
                            message=str(exc),
                        )
                    )

        return posts, pages, issues

    # ------------------------------------------------------------------
    def _make_configured_url(self, path: str) -> str:
        """Build the root-relative URL for a configured page path.

        Mirrors the logic used by
        [`ContextBuilder.get_configured_url`][blogmore.generator.context.ContextBuilder.get_configured_url]:
        strips any leading slash from *path*, prepends a fresh ``/``, and
        optionally applies [`make_url_clean`][blogmore.clean_url.make_url_clean]
        when ``clean_urls`` is enabled.

        Args:
            path: A path string from the site configuration (e.g.
                ``"archive.html"`` or ``"archive/index.html"``).

        Returns:
            The root-relative URL for the page, always starting with ``/``.
        """
        url = "/" + path.lstrip("/")
        if self.clean_urls:
            url = make_url_clean(url)
        return url

    # ------------------------------------------------------------------
    def _build_known_url_set(
        self,
        posts: list[Post],
        pages: list[Page],
    ) -> set[str]:
        """Build a set of normalised known URLs from all generated content.

        Includes URLs for posts, static pages, the main index, the archive,
        tags and categories overview pages, individual tag and category listing
        pages, date-archive pages (year, month, day), any optional feature
        pages that are enabled in the configuration (search, stats, calendar,
        graph), and every file that would be copied verbatim from the
        ``extras/`` directory.

        Each URL is normalised via
        [`normalize_url_path`][blogmore.backlinks.normalize_url_path]
        (strips `.html`, `index.html`, and trailing slashes) so that
        comparisons are format-agnostic.

        Args:
            posts: Successfully parsed posts.
            pages: Successfully parsed pages.

        Returns:
            A set of normalised URL strings.
        """
        known: set[str] = set()

        # Posts and static pages.
        for post in posts:
            url = _post_url(post, self.post_path_template, self.clean_urls)
            known.add(normalize_url_path(url))
        for page in pages:
            url = _page_url(page, self.page_path_template, self.clean_urls)
            known.add(normalize_url_path(url))

        # Main index — "/" and "/index.html" both normalise to the empty string.
        known.add("")

        # Archive, tags overview, and categories overview pages — always
        # generated whenever there are posts / tags / categories.
        known.add(normalize_url_path(self._make_configured_url(self.archive_path)))
        known.add(normalize_url_path(self._make_configured_url(self.tags_path)))
        known.add(normalize_url_path(self._make_configured_url(self.categories_path)))

        # Optional feature pages — only included when the feature is enabled.
        if self.with_search:
            known.add(normalize_url_path(self._make_configured_url(self.search_path)))
        if self.with_stats:
            known.add(normalize_url_path(self._make_configured_url(self.stats_path)))
        if self.with_calendar:
            known.add(
                normalize_url_path(self._make_configured_url(self.calendar_path))
            )
        if self.with_graph:
            known.add(normalize_url_path(self._make_configured_url(self.graph_path)))

        # Individual tag pages — /tag/{safe_tag}/
        posts_by_tag = group_posts_by_tag(posts)
        for tag_lower in posts_by_tag:
            safe_tag = sanitize_for_url(tag_lower)
            known.add(normalize_url_path(f"/{TAG_DIR}/{safe_tag}"))

        # Individual category pages — /category/{safe_category}/
        posts_by_category = group_posts_by_category(posts)
        for category_lower in posts_by_category:
            safe_category = sanitize_for_url(category_lower)
            known.add(normalize_url_path(f"/{CATEGORY_DIR}/{safe_category}"))

        # Date archive pages — /{year}/, /{year}/{month}/, /{year}/{month}/{day}/
        for post in posts:
            if post.date is not None:
                year = post.date.year
                month = post.date.month
                day = post.date.day
                known.add(normalize_url_path(f"/{year}"))
                known.add(normalize_url_path(f"/{year}/{month:02d}"))
                known.add(normalize_url_path(f"/{year}/{month:02d}/{day:02d}"))

        # Feed files — always generated alongside the posts.
        known.add("/feed.xml")
        known.add(f"/{FEEDS_DIR}/all.atom.xml")
        for category_lower in posts_by_category:
            safe_category = sanitize_for_url(category_lower)
            known.add(f"/{FEEDS_DIR}/{safe_category}.rss.xml")
            known.add(f"/{FEEDS_DIR}/{safe_category}.atom.xml")

        # Extras files — every file under extras/ is copied verbatim to the
        # site root during a build, so links to those files are always valid.
        if self.content_dir is not None:
            extras_dir = self.content_dir / "extras"
            if extras_dir.is_dir():
                for extra_file in extras_dir.rglob("*"):
                    if extra_file.is_file():
                        relative = extra_file.relative_to(extras_dir)
                        # Use forward slashes regardless of the host OS.
                        url = "/" + "/".join(relative.parts)
                        known.add(url)

        return known

    # ------------------------------------------------------------------
    def _check_links(
        self,
        source_path: Path,
        content: str,
        known_urls: set[str],
    ) -> list[LintIssue]:
        """Check the non-image internal links in a content file.

        Each internal link (root-relative or pointing back to `site_url`) is
        normalised and compared against *known_urls*.  Links to external
        domains and fragment-only links are silently ignored.  Bare relative
        links (e.g. ``2016/08/page.html``) are always reported as broken
        because they resolve relative to the page's URL in a browser and
        almost always produce a broken URL in a static-site context.

        Args:
            source_path: Path to the content file being checked.
            content: Raw Markdown source.
            known_urls: Set of normalised URLs for all known posts and pages.

        Returns:
            A list of [`LintIssue`][blogmore.linter.LintIssue] objects for each broken link.
        """
        issues: list[LintIssue] = []
        for raw_url in _find_regular_links(content):
            path = to_path(raw_url, self.site_url)
            if path is None:
                # Bare relative paths (e.g. ``2016/08/page.html``) are never
                # valid in a static site — they resolve relative to the
                # current page URL and almost always produce a broken URL.
                if _is_relative_path(raw_url):
                    issues.append(
                        LintIssue(
                            source_path=source_path,
                            kind=IssueKind.BROKEN_INTERNAL_LINK,
                            message=(
                                f"Relative link {raw_url!r} — "
                                f"use a root-relative path starting with '/'"
                            ),
                        )
                    )
                continue
            normalised = normalize_url_path(path)
            if normalised not in known_urls:
                issues.append(
                    LintIssue(
                        source_path=source_path,
                        kind=IssueKind.BROKEN_INTERNAL_LINK,
                        message=(
                            f"Broken internal link {raw_url!r} — "
                            f"no matching post or page found"
                        ),
                    )
                )
        return issues

    # ------------------------------------------------------------------
    def _check_dates(self, post: Post) -> list[LintIssue]:
        """Check whether a post's `date` or `modified` values are in the future.

        Both values are compared against the current UTC time.  Timezone-aware
        datetimes are compared directly; naive datetimes are assumed to be UTC.

        Args:
            post: The post to check.

        Returns:
            A list of [`LintIssue`][blogmore.linter.LintIssue] objects (zero, one, or two) for
            any future date values.
        """
        issues: list[LintIssue] = []
        now_utc = dt.datetime.now(tz=dt.UTC)

        def _is_future(date: dt.datetime) -> bool:
            """Return `True` if *date* is later than the current UTC time."""
            if date.tzinfo is None:
                date = date.replace(tzinfo=dt.UTC)
            return date > now_utc

        if post.date is not None and _is_future(post.date):
            issues.append(
                LintIssue(
                    source_path=post.path,
                    kind=IssueKind.FUTURE_DATE,
                    message=(
                        f"Post `date` is in the future: "
                        f"{post.date.strftime('%Y-%m-%d %H:%M:%S')}"
                    ),
                )
            )

        modified = post.modified_date
        if modified is not None and _is_future(modified):
            issues.append(
                LintIssue(
                    source_path=post.path,
                    kind=IssueKind.FUTURE_DATE,
                    message=(
                        f"Post `modified` date is in the future: "
                        f"{modified.strftime('%Y-%m-%d %H:%M:%S')}"
                    ),
                )
            )

        return issues

    # ------------------------------------------------------------------
    def _check_images(
        self,
        source_path: Path,
        content: str,
        extras_dir: Path,
    ) -> list[LintIssue]:
        """Check internal image links for missing files in the `extras/` directory.

        Only internal image links (root-relative paths and full URLs pointing
        back to this site) are checked.  External image links are ignored.
        The check strips the leading `/` from the URL, URL-decodes the result
        (so that ``%20`` maps to a space, etc.), and looks for the resulting
        relative path inside *extras_dir*.

        Args:
            source_path: Path to the content file being checked.
            content: Raw Markdown source.
            extras_dir: Path to the `extras/` directory inside `content_dir`.

        Returns:
            A list of [`LintIssue`][blogmore.linter.LintIssue] objects for each image
            whose file is not found in *extras_dir*.
        """
        issues: list[LintIssue] = []
        for raw_url in _find_image_links(content):
            path = to_path(raw_url, self.site_url)
            if path is None:
                # External image — skip.
                continue
            # URL-decode so that percent-encoded filenames (e.g. %20 → space)
            # resolve to the actual file on disk.
            relative = unquote(path.lstrip("/"), encoding="utf-8")
            candidate = extras_dir / relative
            if not candidate.is_file():
                issues.append(
                    LintIssue(
                        source_path=source_path,
                        kind=IssueKind.MISSING_IMAGE,
                        message=(
                            f"Internal image {raw_url!r} not found in extras/ directory"
                        ),
                    )
                )
        return issues

    # ------------------------------------------------------------------
    def lint(self) -> LintResult:
        """Run all lint checks and return the aggregated result.

        The checks performed are:

        1. **Frontmatter errors** — files that failed to parse.
        2. **Broken internal links** — links with no matching post or page.
        3. **Future dates** — `date` or `modified` values after today.
        4. **Missing images** — internal image links with no file in `extras/`.

        Returns:
            A [`LintResult`][blogmore.linter.LintResult] containing every issue found.
        """
        result = LintResult()

        if self.content_dir is None:
            return result

        extras_dir = self.content_dir / "extras"

        # Step 1 — parse everything, collecting frontmatter errors.
        posts, pages, parse_issues = self._parse_all()
        result.issues.extend(parse_issues)

        # Step 2 — build the set of known (normalised) URLs.
        known_urls = self._build_known_url_set(posts, pages)

        # Step 3 — check each post.
        for post in posts:
            result.issues.extend(self._check_links(post.path, post.content, known_urls))
            result.issues.extend(self._check_dates(post))
            result.issues.extend(
                self._check_images(post.path, post.content, extras_dir)
            )

        # Step 4 — check each page (no date check — pages have no dates).
        for page in pages:
            result.issues.extend(self._check_links(page.path, page.content, known_urls))
            result.issues.extend(
                self._check_images(page.path, page.content, extras_dir)
            )

        return result


##############################################################################
def lint_site(site_config: SiteConfig) -> LintResult:
    """Lint all posts and pages described by *site_config* and return the result.

    Convenience wrapper around [`SiteLinter`][blogmore.linter.SiteLinter] that
    constructs the linter, runs all checks, and returns the
    [`LintResult`][blogmore.linter.LintResult].

    Args:
        site_config: The site configuration to lint.  All linting parameters
            (content directory, URL configuration, feature flags, path
            templates, etc.) are read from this object.

    Returns:
        A [`LintResult`][blogmore.linter.LintResult] containing all issues found.
    """
    return SiteLinter(site_config).lint()


### linter.py ends here
