"""Tests for the lint command."""

import datetime as dt
import sys
from pathlib import Path
from unittest.mock import patch

from blogmore.__main__ import main
from blogmore.linter import lint_site
from blogmore.site_config import SiteConfig


class TestLintCommand:
    """Tests for the lint command."""

    def test_lint_success(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test linting a site with no issues."""
        site_config = SiteConfig(
            content_dir=posts_dir,
            output_dir=temp_output_dir,
            linting_ignore=[
                "/images/relative-cover.jpg",
                "/2024/04/02/images/no-slash-cover.jpg",
            ],
        )
        result = lint_site(site_config)
        assert result == 0

    def test_lint_future_date(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test that future dates are reported as warnings."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        future_date = (dt.datetime.now(dt.UTC) + dt.timedelta(days=365)).strftime(
            "%Y-%m-%d"
        )

        post_path = content_dir / "future-post.md"
        post_path.write_text(
            f"---\ntitle: Future Post\ndate: {future_date}\n---\nFuture content.\n"
        )

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        with patch("sys.stderr"):
            result = lint_site(site_config)
            # Warnings don't cause failure (result 0)
            assert result == 0

    def test_lint_broken_link(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test that broken internal links are reported as errors."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        post_path = content_dir / "broken-link.md"
        post_path.write_text(
            "---\ntitle: Broken Link Post\ndate: 2024-01-01\n---\n[Broken Link](/non-existent.html)\n"
        )

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        result = lint_site(site_config)
        assert result == 1

    def test_lint_broken_image(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test that broken internal image links are reported as errors."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        post_path = content_dir / "broken-image.md"
        post_path.write_text(
            "---\ntitle: Broken Image Post\ndate: 2024-01-01\n---\n![Broken Image](/images/missing.png)\n"
        )

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        result = lint_site(site_config)
        assert result == 1

    def test_lint_missing_alt_text(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test that images missing or having empty alt text are reported as warnings."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        post_path = content_dir / "missing-alt.md"
        post_path.write_text(
            "---\n"
            "title: Missing Alt Post\n"
            "date: 2024-01-01\n"
            "---\n"
            '<img src="/images/logo.png">\n'
            '<img src="/images/logo.png" alt="">\n'
            '<img src="/images/logo.png" alt="   ">\n'
        )

        site_config = SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
            linting_ignore=["/images/logo.png"],
        )

        result = lint_site(site_config)
        # Warning doesn't cause failure
        assert result == 0

    def test_lint_broken_cover(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test that broken internal cover images are reported as errors."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        post_path = content_dir / "broken-cover.md"
        post_path.write_text(
            "---\ntitle: Broken Cover Post\ndate: 2024-01-01\ncover: /images/missing-cover.png\n---\nContent\n"
        )

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        result = lint_site(site_config)
        assert result == 1

    def test_lint_valid_relative_link(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that valid relative links are accepted."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "post1.md").write_text(
            "---\ntitle: Post 1\ndate: 2024-01-01\n---\n[Link to Post 2](post2.html)\n"
        )
        (content_dir / "post2.md").write_text(
            "---\ntitle: Post 2\ndate: 2024-01-01\n---\nI am post 2.\n"
        )

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        result = lint_site(site_config)
        assert result == 0

    def test_lint_valid_extra_link(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test that links to files in extras are accepted."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        (extras_dir / "about.html").write_text("About")

        post_path = content_dir / "post.md"
        post_path.write_text(
            "---\ntitle: Post\ndate: 2024-01-01\n---\n[About](/about.html)\n"
        )

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        result = lint_site(site_config)
        assert result == 0

    def test_lint_trailing_slash_insensitivity(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that links are valid regardless of trailing slash."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-01\n---\n[Tag](/tag/python)\n[Archive](/archive)\n"
        )

        # Site config with clean URLs (so /tag/python/ and /archive/ are in valid_urls)
        site_config = SiteConfig(
            content_dir=content_dir, output_dir=temp_output_dir, clean_urls=True
        )

        # Mock some posts to generate tags
        mock_post = content_dir / "real-post.md"
        mock_post.write_text(
            "---\ntitle: Real Post\ndate: 2024-01-01\ntags: [python]\n---\nContent\n"
        )

        result = lint_site(site_config)
        assert result == 0

    def test_lint_clean_url_suggestion(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that explicit index.html is suggested as a clean URL."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-01\n---\n[Home](/index.html)\n"
        )

        site_config = SiteConfig(
            content_dir=content_dir, output_dir=temp_output_dir, clean_urls=True
        )

        # This should report a warning but result in 0
        result = lint_site(site_config)
        assert result == 0

    def test_lint_absolute_local_link(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that absolute links to the local site are flagged as warnings."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-01\n---\n[About](https://mysite.com/about.html)\n"
        )

        site_config = SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
            site_url="https://mysite.com",
        )

        # Mock about.html existing in extras
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        (extras_dir / "about.html").write_text("About")

        # Should warn about absolute URL
        result = lint_site(site_config)
        assert result == 0

    def test_lint_ignored_absolute_local_link(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that ignored absolute links to the local site do NOT warn."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-01\n---\n[About](https://mysite.com/about.html)\n"
        )

        site_config = SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
            site_url="https://mysite.com",
            linting_ignore=["/about.html"],
        )

        # Mock about.html existing
        extras_dir = content_dir / "extras"
        extras_dir.mkdir()
        (extras_dir / "about.html").write_text("About")

        # Should NOT warn because it's ignored
        result = lint_site(site_config)
        assert result == 0

    def test_lint_ignored_links(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test that ignored links are treated as valid."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-01\n---\n[Ignored Link](/ignored-path/)\n"
        )

        site_config = SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
            linting_ignore=["/ignored-path/"],
        )

        result = lint_site(site_config)
        assert result == 0

    def test_lint_ignored_cover(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test that ignored cover images are treated as valid."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "post.md").write_text(
            "---\ntitle: Post\ndate: 2024-01-01\ncover: /ignored-cover.png\n---\nContent\n"
        )

        site_config = SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
            linting_ignore=["/ignored-cover.png"],
        )

        result = lint_site(site_config)
        assert result == 0

    def test_lint_malformed_frontmatter(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that malformed frontmatter is reported as an error."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        post_path = content_dir / "malformed.md"
        post_path.write_text(
            "---\ntitle: Malformed Post\ntags: [unclosed\n---\nContent\n"
        )

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        result = lint_site(site_config)
        assert result == 1

    def test_lint_metadata_health_warnings(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that missing metadata and inconsistent dates are reported as warnings."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Post with no category, no tags, and no date
        post_path = content_dir / "bare-post.md"
        post_path.write_text("---\ntitle: Bare Post\n---\nBare content.\n")

        # Post with modified date earlier than date
        invalid_dates_path = content_dir / "invalid-dates.md"
        invalid_dates_path.write_text(
            "---\ntitle: Invalid Dates\ndate: 2024-01-10\nmodified: 2024-01-01\n---\nContent.\n"
        )

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        result = lint_site(site_config)
        # Warnings don't cause failure
        assert result == 0

    def test_lint_duplicate_titles(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test that duplicate post titles are reported as warnings."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "post1.md").write_text(
            "---\ntitle: Duplicate Title\ndate: 2024-01-01\n---\nContent 1\n"
        )
        (content_dir / "post2.md").write_text(
            "---\ntitle: Duplicate Title\ndate: 2024-01-02\n---\nContent 2\n"
        )

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        result = lint_site(site_config)
        # Warnings don't cause failure
        assert result == 0

    def test_lint_sidebar_pages_error(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that non-existent sidebar pages are reported as errors."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        site_config = SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
            sidebar_pages=["non-existent"],
        )

        result = lint_site(site_config)
        assert result == 1

    def test_lint_sidebar_links_error(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that broken sidebar links are reported as errors."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        site_config = SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
            sidebar_config={"links": [{"title": "Broken", "url": "/missing.html"}]},
        )

        result = lint_site(site_config)
        assert result == 1

    def test_main_lint_command(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test lint command via main()."""
        with (
            patch.object(
                sys,
                "argv",
                [
                    "blogmore",
                    "lint",
                    str(posts_dir),
                    "-o",
                    str(temp_output_dir),
                ],
            ),
            # Patch lint_site directly to avoid fixture issues in main command tests
            patch("blogmore.__main__.lint_site", return_value=0) as mock_lint,
        ):
            result = main()
            assert result == 0
            assert mock_lint.called

    def test_main_check_alias(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test check alias via main()."""
        with (
            patch.object(
                sys,
                "argv",
                [
                    "blogmore",
                    "check",
                    str(posts_dir),
                    "-o",
                    str(temp_output_dir),
                ],
            ),
            patch("blogmore.__main__.lint_site", return_value=0) as mock_lint,
        ):
            result = main()
            assert result == 0
            assert mock_lint.called
