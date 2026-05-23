from pathlib import Path

from blogmore.generator.site import SiteGenerator
from blogmore.site_config import SiteConfig


def test_generate_with_default_author_url(
    posts_dir: Path, temp_output_dir: Path
) -> None:
    """Test that default_author_url is applied and appears in JSON-LD."""
    generator = SiteGenerator(
        site_config=SiteConfig(
            content_dir=posts_dir,
            output_dir=temp_output_dir,
            default_author="Default Author",
            default_author_url="https://example.com/default-author",
        )
    )

    generator.generate()

    # The first-post.md fixture doesn't have an author_url, so it should get the default
    post_file = temp_output_dir / "2024" / "01" / "15" / "first-post.html"
    assert post_file.exists()

    content = post_file.read_text()
    # Check JSON-LD
    assert '"author": {' in content
    assert '"name": "Default Author"' in content
    assert '"url": "https://example.com/default-author"' in content


def test_author_url_override_in_post(tmp_path: Path, temp_output_dir: Path) -> None:
    """Test that post-specific author_url overrides default_author_url."""
    posts_dir = tmp_path / "posts"
    posts_dir.mkdir()
    post_file = posts_dir / "2024-01-01-test.md"
    post_file.write_text("""---
title: Test Post
author: Specific Author
author_url: https://example.com/specific-author
date: 2024-01-01
---
Content
""")

    generator = SiteGenerator(
        site_config=SiteConfig(
            content_dir=tmp_path,  # SiteGenerator expects content_dir to contain posts/ and pages/
            output_dir=temp_output_dir,
            default_author="Default Author",
            default_author_url="https://example.com/default-author",
        )
    )

    generator.generate()

    output_file = temp_output_dir / "2024" / "01" / "01" / "test.html"
    assert output_file.exists()

    content = output_file.read_text()
    assert '"name": "Specific Author"' in content
    assert '"url": "https://example.com/specific-author"' in content
    assert "https://example.com/default-author" not in content


def test_author_url_in_page(tmp_path: Path, temp_output_dir: Path) -> None:
    """Test that page-specific author_url works."""
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()
    page_file = pages_dir / "about.md"
    page_file.write_text("""---
title: About
author: Page Author
author_url: https://example.com/page-author
---
Content
""")

    # We need a dummy post to avoid SiteGenerator error if no posts found?
    # Actually SiteGenerator should handle empty posts.
    (tmp_path / "posts").mkdir(exist_ok=True)

    generator = SiteGenerator(
        site_config=SiteConfig(
            content_dir=tmp_path,
            output_dir=temp_output_dir,
            default_author="Default Author",
            default_author_url="https://example.com/default-author",
        )
    )

    generator.generate()

    output_file = temp_output_dir / "about.html"
    assert output_file.exists()

    content = output_file.read_text()
    assert '"name": "Page Author"' in content
    assert '"url": "https://example.com/page-author"' in content
