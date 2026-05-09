"""Tests for the linter module."""

##############################################################################
# Standard-library imports.
import datetime as dt
from pathlib import Path

##############################################################################
# Third-party imports.
import pytest

##############################################################################
# Application imports.
from blogmore.linter import (
    IssueKind,
    LintIssue,
    LintResult,
    SiteLinter,
    _find_image_links,
    _find_regular_links,
    lint_site,
)


##############################################################################
# Helper utilities.


def _make_content_dir(tmp_path: Path, posts: dict[str, str]) -> Path:
    """Create a temporary content directory with the given posts.

    Args:
        tmp_path: Base temporary directory.
        posts: Mapping from filename (relative to content dir) to frontmatter + body.

    Returns:
        The path to the created content directory.
    """
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    for filename, text in posts.items():
        post_path = content_dir / filename
        post_path.parent.mkdir(parents=True, exist_ok=True)
        post_path.write_text(text, encoding="utf-8")
    return content_dir


def _make_page(tmp_path: Path, content_dir: Path, name: str, body: str) -> Path:
    """Write a static page file in ``content_dir/pages/``.

    Args:
        tmp_path: Unused; kept for API consistency.
        content_dir: The content directory to write into.
        name: The filename for the page (e.g. ``about.md``).
        body: Full file content (frontmatter + body).

    Returns:
        Path to the created page file.
    """
    pages_dir = content_dir / "pages"
    pages_dir.mkdir(exist_ok=True)
    page_path = pages_dir / name
    page_path.write_text(body, encoding="utf-8")
    return page_path


##############################################################################
# _find_regular_links tests.


class TestFindRegularLinks:
    """Tests for the `_find_regular_links` helper."""

    def test_inline_link_returned(self) -> None:
        """A plain inline link is returned."""
        links = _find_regular_links("[text](/path/to/page.html)")
        assert "/path/to/page.html" in links

    def test_image_link_excluded(self) -> None:
        """An inline image link is not returned as a regular link."""
        links = _find_regular_links("![alt](/image.png)")
        assert "/image.png" not in links

    def test_mixed_links(self) -> None:
        """Regular links are found alongside image links."""
        content = "See [the page](/page.html) and ![an image](/img.png)."
        links = _find_regular_links(content)
        assert "/page.html" in links
        assert "/img.png" not in links

    def test_reference_link_returned(self) -> None:
        """A reference-style link is resolved and returned."""
        content = "[text][ref]\n\n[ref]: /ref-page.html"
        links = _find_regular_links(content)
        assert "/ref-page.html" in links

    def test_external_link_included(self) -> None:
        """External links are returned (filtering is done upstream)."""
        links = _find_regular_links("[ext](https://example.com)")
        assert "https://example.com" in links

    def test_empty_content(self) -> None:
        """Empty content returns an empty list."""
        assert _find_regular_links("") == []


##############################################################################
# _find_image_links tests.


class TestFindImageLinks:
    """Tests for the `_find_image_links` helper."""

    def test_inline_image_returned(self) -> None:
        """An inline image link URL is returned."""
        links = _find_image_links("![alt](/images/photo.jpg)")
        assert "/images/photo.jpg" in links

    def test_regular_link_excluded(self) -> None:
        """A regular (non-image) link is not returned."""
        links = _find_image_links("[text](/page.html)")
        assert "/page.html" not in links

    def test_reference_image_returned(self) -> None:
        """A reference-style image link is resolved and returned."""
        content = "![alt][img-ref]\n\n[img-ref]: /ref-image.png"
        links = _find_image_links(content)
        assert "/ref-image.png" in links

    def test_external_image_included(self) -> None:
        """External image URLs are returned (filtering is done upstream)."""
        links = _find_image_links("![alt](https://example.com/img.png)")
        assert "https://example.com/img.png" in links

    def test_empty_content(self) -> None:
        """Empty content returns an empty list."""
        assert _find_image_links("") == []


##############################################################################
# LintResult tests.


class TestLintResult:
    """Tests for the `LintResult` data class."""

    def test_empty_result_has_no_issues(self) -> None:
        """An empty LintResult reports no issues."""
        result = LintResult()
        assert not result.has_issues
        assert result.issue_count == 0

    def test_result_with_issues(self) -> None:
        """A LintResult with issues reports them correctly."""
        issue = LintIssue(
            source_path=Path("post.md"),
            kind=IssueKind.BROKEN_INTERNAL_LINK,
            message="Broken link",
        )
        result = LintResult(issues=[issue])
        assert result.has_issues
        assert result.issue_count == 1


##############################################################################
# Frontmatter error detection tests.


class TestFrontmatterErrors:
    """Linter detects frontmatter parse errors."""

    def test_missing_title_reported(self, tmp_path: Path) -> None:
        """A post missing the required `title` field generates a frontmatter issue."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": "---\ndate: 2024-01-15\n---\nContent without a title.",
            },
        )
        result = lint_site(content_dir)
        assert result.has_issues
        assert any(i.kind == IssueKind.FRONTMATTER_ERROR for i in result.issues)

    def test_valid_post_no_frontmatter_issue(self, tmp_path: Path) -> None:
        """A well-formed post does not generate any frontmatter issues."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": "---\ntitle: Valid Post\ndate: 2024-01-15\n---\nContent.",
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.FRONTMATTER_ERROR for i in result.issues)

    def test_malformed_yaml_reported(self, tmp_path: Path) -> None:
        """A post with malformed YAML frontmatter generates a frontmatter issue."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": "---\ntitle: My Post: the sequel\n---\nContent.",
            },
        )
        result = lint_site(content_dir)
        assert any(i.kind == IssueKind.FRONTMATTER_ERROR for i in result.issues)

    def test_page_missing_title_reported(self, tmp_path: Path) -> None:
        """A page missing the required `title` field generates a frontmatter issue."""
        content_dir = _make_content_dir(tmp_path, {})
        _make_page(
            tmp_path,
            content_dir,
            "about.md",
            "---\ndescription: No title here\n---\nPage content.",
        )
        result = lint_site(content_dir)
        assert any(i.kind == IssueKind.FRONTMATTER_ERROR for i in result.issues)

    def test_source_path_recorded(self, tmp_path: Path) -> None:
        """The source path of a frontmatter error is correctly recorded."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "broken.md": "---\ndate: 2024-01-01\n---\nNo title.",
            },
        )
        result = lint_site(content_dir)
        frontmatter_issues = [
            i for i in result.issues if i.kind == IssueKind.FRONTMATTER_ERROR
        ]
        assert frontmatter_issues
        assert frontmatter_issues[0].source_path.name == "broken.md"


##############################################################################
# Future date detection tests.


class TestFutureDates:
    """Linter detects posts with future `date` or `modified` fields."""

    def test_future_date_reported(self, tmp_path: Path) -> None:
        """A post with a `date` in the future triggers a FUTURE_DATE issue."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "future.md": "---\ntitle: Future Post\ndate: 2099-12-31\n---\nContent.",
            },
        )
        result = lint_site(content_dir)
        assert any(i.kind == IssueKind.FUTURE_DATE for i in result.issues)

    def test_future_modified_reported(self, tmp_path: Path) -> None:
        """A post with a `modified` date in the future triggers a FUTURE_DATE issue."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\nmodified: 2099-06-15\n---\nContent."
                ),
            },
        )
        result = lint_site(content_dir)
        future_issues = [i for i in result.issues if i.kind == IssueKind.FUTURE_DATE]
        assert future_issues
        assert "modified" in future_issues[0].message

    def test_past_date_not_reported(self, tmp_path: Path) -> None:
        """A post with a past `date` does not trigger a FUTURE_DATE issue."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "old.md": "---\ntitle: Old Post\ndate: 2000-01-01\n---\nContent.",
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.FUTURE_DATE for i in result.issues)

    def test_no_date_not_reported(self, tmp_path: Path) -> None:
        """A post without a `date` does not trigger a FUTURE_DATE issue."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "no-date-post.md": "---\ntitle: No Date Post\n---\nContent.",
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.FUTURE_DATE for i in result.issues)

    def test_future_date_message_includes_date(self, tmp_path: Path) -> None:
        """The FUTURE_DATE issue message includes the date value."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "future-post.md": "---\ntitle: Future\ndate: 2099-12-31\n---\nContent.",
            },
        )
        result = lint_site(content_dir)
        future_issues = [i for i in result.issues if i.kind == IssueKind.FUTURE_DATE]
        assert future_issues
        assert "2099" in future_issues[0].message


##############################################################################
# Broken internal link detection tests.


class TestBrokenInternalLinks:
    """Linter detects internal links that have no matching post or page."""

    def test_broken_link_to_nonexistent_post(self, tmp_path: Path) -> None:
        """A link to a non-existent post path triggers a BROKEN_INTERNAL_LINK issue."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "See [this page](/nonexistent/post.html)."
                ),
            },
        )
        result = lint_site(content_dir)
        assert any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_valid_internal_link_not_reported(self, tmp_path: Path) -> None:
        """A link to a post that exists is not reported as broken."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "2024-01-15-target.md": (
                    "---\ntitle: Target Post\ndate: 2024-01-15\n---\nI am the target."
                ),
                "2024-02-01-linker.md": (
                    "---\ntitle: Linker\ndate: 2024-02-01\n---\n"
                    "See [target](/2024/01/15/target.html)."
                ),
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_external_link_not_reported(self, tmp_path: Path) -> None:
        """A link to an external URL is not reported as broken."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "See [external](https://example.com/page)."
                ),
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_page_valid(self, tmp_path: Path) -> None:
        """A link from a post to an existing static page is not reported as broken."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "See [about](/about.html)."
                ),
            },
        )
        _make_page(tmp_path, content_dir, "about.md", "---\ntitle: About\n---\nAbout.")
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_broken_link_message_contains_url(self, tmp_path: Path) -> None:
        """The broken-link issue message includes the broken URL."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "See [missing](/this/does/not/exist.html)."
                ),
            },
        )
        result = lint_site(content_dir)
        link_issues = [
            i for i in result.issues if i.kind == IssueKind.BROKEN_INTERNAL_LINK
        ]
        assert link_issues
        assert "/this/does/not/exist.html" in link_issues[0].message

    def test_clean_url_link_recognised(self, tmp_path: Path) -> None:
        """A link using clean URLs is recognised as valid when `clean_urls` is enabled."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "target.md": "---\ntitle: Target\n---\nI am the target.",
                "linker.md": (
                    "---\ntitle: Linker\n---\n"
                    "See [target](/target/)."
                ),
            },
        )
        result = lint_site(
            content_dir,
            post_path_template="{slug}/index.html",
            clean_urls=True,
        )
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_site_url_links_to_self_recognised(self, tmp_path: Path) -> None:
        """A full URL pointing back at the site is recognised as an internal link."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "2024-01-01-target.md": "---\ntitle: Target\ndate: 2024-01-01\n---\nTarget.",
                "2024-02-01-linker.md": (
                    "---\ntitle: Linker\ndate: 2024-02-01\n---\n"
                    "See [target](https://example.com/2024/01/01/target.html)."
                ),
            },
        )
        result = lint_site(content_dir, site_url="https://example.com")
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)


##############################################################################
# Missing image asset tests.


class TestMissingImages:
    """Linter detects internal image links with no matching file in extras/."""

    def test_missing_image_reported(self, tmp_path: Path) -> None:
        """An internal image link with no matching file in extras/ is reported."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "![photo](/images/missing.png)"
                ),
            },
        )
        result = lint_site(content_dir)
        assert any(i.kind == IssueKind.MISSING_IMAGE for i in result.issues)

    def test_present_image_not_reported(self, tmp_path: Path) -> None:
        """An internal image link that has a matching file in extras/ is not reported."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "![photo](/images/present.png)"
                ),
            },
        )
        # Create the matching extras file.
        extras_dir = content_dir / "extras" / "images"
        extras_dir.mkdir(parents=True)
        (extras_dir / "present.png").write_bytes(b"PNG")

        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.MISSING_IMAGE for i in result.issues)

    def test_external_image_not_reported(self, tmp_path: Path) -> None:
        """An image link pointing to an external URL is not reported."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "![photo](https://example.com/photo.jpg)"
                ),
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.MISSING_IMAGE for i in result.issues)

    def test_missing_image_message_contains_url(self, tmp_path: Path) -> None:
        """The missing-image issue message includes the image URL."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "![photo](/img/missing.jpg)"
                ),
            },
        )
        result = lint_site(content_dir)
        image_issues = [i for i in result.issues if i.kind == IssueKind.MISSING_IMAGE]
        assert image_issues
        assert "/img/missing.jpg" in image_issues[0].message

    def test_image_in_page_checked(self, tmp_path: Path) -> None:
        """Missing image links in static pages are also reported."""
        content_dir = _make_content_dir(tmp_path, {})
        _make_page(
            tmp_path,
            content_dir,
            "about.md",
            "---\ntitle: About\n---\n![missing](/no-image.png)",
        )
        result = lint_site(content_dir)
        assert any(i.kind == IssueKind.MISSING_IMAGE for i in result.issues)


##############################################################################
# Draft post handling tests.


class TestDraftHandling:
    """Linter respects the `include_drafts` flag."""

    def test_draft_excluded_by_default(self, tmp_path: Path) -> None:
        """Draft posts are not linted when `include_drafts` is False."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "draft.md": (
                    "---\ntitle: Draft\ndate: 2099-01-01\ndraft: true\n---\nDraft content."
                ),
            },
        )
        result = lint_site(content_dir, include_drafts=False)
        # Future date in draft should not be reported when drafts are excluded.
        assert not any(i.kind == IssueKind.FUTURE_DATE for i in result.issues)

    def test_draft_included_when_requested(self, tmp_path: Path) -> None:
        """Draft posts are linted when `include_drafts` is True."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "draft.md": (
                    "---\ntitle: Draft\ndate: 2099-01-01\ndraft: true\n---\nDraft content."
                ),
            },
        )
        result = lint_site(content_dir, include_drafts=True)
        assert any(i.kind == IssueKind.FUTURE_DATE for i in result.issues)


##############################################################################
# lint_site convenience function tests.


class TestLintSite:
    """Tests for the `lint_site` convenience function."""

    def test_clean_content_returns_no_issues(self, tmp_path: Path) -> None:
        """A directory of well-formed posts with no issues returns an empty result."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": "---\ntitle: Good Post\ndate: 2024-01-01\n---\nAll good.",
            },
        )
        result = lint_site(content_dir)
        assert not result.has_issues

    def test_missing_content_dir_raises(self) -> None:
        """Passing a non-existent directory to `SiteLinter` does not crash.

        The linter gracefully handles a missing content directory by returning
        an empty result (no issues) rather than raising an exception.
        """
        linter = SiteLinter(content_dir=Path("/nonexistent/path"))
        result = linter.lint()
        assert not result.has_issues

    def test_multiple_issues_in_one_run(self, tmp_path: Path) -> None:
        """Multiple issues of different kinds are all collected in one lint run."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "future.md": (
                    "---\ntitle: Future\ndate: 2099-01-01\n---\n"
                    "See [broken](/no-such-post.html) and ![img](/missing.png)."
                ),
            },
        )
        result = lint_site(content_dir)
        kinds = {i.kind for i in result.issues}
        assert IssueKind.FUTURE_DATE in kinds
        assert IssueKind.BROKEN_INTERNAL_LINK in kinds
        assert IssueKind.MISSING_IMAGE in kinds

    def test_custom_post_path_template_respected(self, tmp_path: Path) -> None:
        """Custom `post_path` template is used when computing known post URLs."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "target.md": "---\ntitle: Target\ndate: 2024-03-15\n---\nTarget.",
                "linker.md": (
                    "---\ntitle: Linker\ndate: 2024-04-01\n---\n"
                    "See [target](/posts/target.html)."
                ),
            },
        )
        # With the custom template the target URL is /posts/target.html.
        result = lint_site(
            content_dir,
            post_path_template="posts/{slug}.html",
        )
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)


##############################################################################
# Known-URL coverage for generator-created pages.


class TestKnownUrlCoverage:
    """Linter recognises URLs for all pages the generator would create."""

    def test_link_to_archive_not_reported(self, tmp_path: Path) -> None:
        """A link to the archive page is not flagged as broken."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "See [archive](/archive.html)."
                ),
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_tags_page_not_reported(self, tmp_path: Path) -> None:
        """A link to the tags overview page is not flagged as broken."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "See [tags](/tags.html)."
                ),
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_categories_page_not_reported(self, tmp_path: Path) -> None:
        """A link to the categories overview page is not flagged as broken."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "See [categories](/categories.html)."
                ),
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_stats_page_with_feature_enabled(self, tmp_path: Path) -> None:
        """A link to the stats page is valid when `with_stats=True`."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "See [stats](/stats.html)."
                ),
            },
        )
        result = lint_site(content_dir, with_stats=True)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_stats_page_without_feature_flagged(self, tmp_path: Path) -> None:
        """A link to the stats page is broken when `with_stats=False`."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "See [stats](/stats.html)."
                ),
            },
        )
        result = lint_site(content_dir, with_stats=False)
        assert any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_calendar_page_with_feature_enabled(self, tmp_path: Path) -> None:
        """A link to the calendar page is valid when `with_calendar=True`."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "See [calendar](/calendar.html)."
                ),
            },
        )
        result = lint_site(content_dir, with_calendar=True)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_graph_page_with_feature_enabled(self, tmp_path: Path) -> None:
        """A link to the graph page is valid when `with_graph=True`."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "See [graph](/graph.html)."
                ),
            },
        )
        result = lint_site(content_dir, with_graph=True)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_search_page_with_feature_enabled(self, tmp_path: Path) -> None:
        """A link to the search page is valid when `with_search=True`."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "See [search](/search.html)."
                ),
            },
        )
        result = lint_site(content_dir, with_search=True)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_individual_tag_page_not_reported(self, tmp_path: Path) -> None:
        """A link to a tag's listing page is not flagged as broken."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\ntags:\n  - Python\n---\n"
                    "See [python tag](/tag/python)."
                ),
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_individual_category_page_not_reported(self, tmp_path: Path) -> None:
        """A link to a category's listing page is not flagged as broken."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\ncategory: News\n---\n"
                    "See [news](/category/news)."
                ),
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_year_archive_not_reported(self, tmp_path: Path) -> None:
        """A link to a year's archive page is not flagged as broken."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-03-10\n---\n"
                    "See [2024 posts](/2024/)."
                ),
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_month_archive_not_reported(self, tmp_path: Path) -> None:
        """A link to a month archive page is not flagged as broken."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-03-10\n---\n"
                    "See [March 2024](/2024/03/)."
                ),
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_day_archive_not_reported(self, tmp_path: Path) -> None:
        """A link to a day archive page is not flagged as broken."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-03-10\n---\n"
                    "See [10 March 2024](/2024/03/10/)."
                ),
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_root_index_not_reported(self, tmp_path: Path) -> None:
        """A link to the site root `/` is not flagged as broken."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "Go [home](/)."
                ),
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)

    def test_link_to_main_feed_not_reported(self, tmp_path: Path) -> None:
        """A link to the main RSS feed is not flagged as broken."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "Subscribe via [RSS](/feed.xml)."
                ),
            },
        )
        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.BROKEN_INTERNAL_LINK for i in result.issues)


##############################################################################
# Image URL-decoding tests.


class TestImageUrlDecoding:
    """Linter handles percent-encoded filenames in image links."""

    def test_percent_encoded_space_matches_file(self, tmp_path: Path) -> None:
        """An image URL with %20 matches a file whose name contains a space."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "![photo](/images/my%20photo.png)"
                ),
            },
        )
        extras_dir = content_dir / "extras" / "images"
        extras_dir.mkdir(parents=True)
        (extras_dir / "my photo.png").write_bytes(b"PNG")

        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.MISSING_IMAGE for i in result.issues)

    def test_missing_percent_encoded_image_still_reported(
        self, tmp_path: Path
    ) -> None:
        """A %20-encoded image URL with no matching file is still reported as missing."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "![photo](/images/no%20such%20file.png)"
                ),
            },
        )
        result = lint_site(content_dir)
        assert any(i.kind == IssueKind.MISSING_IMAGE for i in result.issues)

    def test_literal_space_in_filename_matches_file(self, tmp_path: Path) -> None:
        """An image URL with a literal space matches a file whose name contains a space."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "![screenshot](/attachments/Screen Shot 2015-06-19.png)"
                ),
            },
        )
        extras_dir = content_dir / "extras" / "attachments"
        extras_dir.mkdir(parents=True)
        (extras_dir / "Screen Shot 2015-06-19.png").write_bytes(b"PNG")

        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.MISSING_IMAGE for i in result.issues)

    def test_literal_space_with_fragment_matches_file(self, tmp_path: Path) -> None:
        """An image URL with a literal space and a fragment still resolves to the correct file."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "![screenshot](/attachments/Screenshot 2015-06-19 at 09.03.58.png#centre)"
                ),
            },
        )
        extras_dir = content_dir / "extras" / "attachments"
        extras_dir.mkdir(parents=True)
        (extras_dir / "Screenshot 2015-06-19 at 09.03.58.png").write_bytes(b"PNG")

        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.MISSING_IMAGE for i in result.issues)

    def test_missing_literal_space_image_still_reported(self, tmp_path: Path) -> None:
        """An image URL with a literal space whose file does not exist is still reported."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    "---\ntitle: Post\ndate: 2024-01-01\n---\n"
                    "![screenshot](/attachments/No Such File.png)"
                ),
            },
        )
        result = lint_site(content_dir)
        assert any(i.kind == IssueKind.MISSING_IMAGE for i in result.issues)

    def test_image_title_attribute_not_treated_as_url(self, tmp_path: Path) -> None:
        """A Markdown image title (`![alt](/url "title")`) does not include the title in the URL."""
        content_dir = _make_content_dir(
            tmp_path,
            {
                "post.md": (
                    '---\ntitle: Post\ndate: 2024-01-01\n---\n'
                    '![photo](/images/photo.png "My photo")'
                ),
            },
        )
        extras_dir = content_dir / "extras" / "images"
        extras_dir.mkdir(parents=True)
        (extras_dir / "photo.png").write_bytes(b"PNG")

        result = lint_site(content_dir)
        assert not any(i.kind == IssueKind.MISSING_IMAGE for i in result.issues)


### test_linter.py ends here
