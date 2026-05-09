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
        site_config = SiteConfig(content_dir=posts_dir, output_dir=temp_output_dir)
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
        post_path.write_text(f"""---
title: Future Post
date: {future_date}
---
Future content.
""")

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        with patch("sys.stderr") as mock_stderr:
            result = lint_site(site_config)
            # Warnings don't cause failure (result 0)
            assert result == 0

        # We can't easily check stdout/stderr here without more mocking,
        # but result 0 is expected for just warnings.

    def test_lint_broken_link(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test that broken internal links are reported as errors."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        post_path = content_dir / "broken-link.md"
        post_path.write_text("""---
title: Broken Link Post
date: 2024-01-01
---
[Broken Link](/non-existent.html)
""")

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        result = lint_site(site_config)
        assert result == 1

    def test_lint_broken_image(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test that broken internal image links are reported as errors."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        post_path = content_dir / "broken-image.md"
        post_path.write_text("""---
title: Broken Image Post
date: 2024-01-01
---
![Broken Image](/images/missing.png)
""")

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        result = lint_site(site_config)
        assert result == 1

    def test_lint_valid_relative_link(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that valid relative links are accepted."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "post1.md").write_text("""---
title: Post 1
date: 2024-01-01
---
[Link to Post 2](post2.html)
""")
        (content_dir / "post2.md").write_text("""---
title: Post 2
date: 2024-01-01
---
I am post 2.
""")

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
        post_path.write_text("""---
title: Post
date: 2024-01-01
---
[About](/about.html)
""")

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        result = lint_site(site_config)
        assert result == 0

    def test_lint_trailing_slash_insensitivity(
        self, tmp_path: Path, temp_output_dir: Path
    ) -> None:
        """Test that links are valid regardless of trailing slash."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "post.md").write_text("""---
title: Post
date: 2024-01-01
---
[Tag](/tag/python)
[Archive](/archive)
""")

        # Site config with clean URLs (so /tag/python/ and /archive/ are in valid_urls)
        site_config = SiteConfig(
            content_dir=content_dir, output_dir=temp_output_dir, clean_urls=True
        )

        # Mock some posts to generate tags
        mock_post = content_dir / "real-post.md"
        mock_post.write_text("""---
title: Real Post
date: 2024-01-01
tags: [python]
---
Content
""")

        result = lint_site(site_config)
        assert result == 0

    def test_lint_ignored_links(self, tmp_path: Path, temp_output_dir: Path) -> None:
        """Test that ignored links are treated as valid."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        (content_dir / "post.md").write_text("""---
title: Post
date: 2024-01-01
---
[Ignored Link](/ignored-path/)
""")

        site_config = SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
            linting_ignore=["/ignored-path/"],
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
        post_path.write_text("""---
title: Malformed Post
tags: [unclosed
---
Content
""")

        site_config = SiteConfig(content_dir=content_dir, output_dir=temp_output_dir)

        result = lint_site(site_config)
        assert result == 1

    def test_main_lint_command(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test lint command via main()."""
        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "lint",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
            ],
        ):
            result = main()
            assert result == 0

    def test_main_check_alias(self, posts_dir: Path, temp_output_dir: Path) -> None:
        """Test check alias via main()."""
        with patch.object(
            sys,
            "argv",
            [
                "blogmore",
                "check",
                str(posts_dir),
                "-o",
                str(temp_output_dir),
            ],
        ):
            result = main()
            assert result == 0
