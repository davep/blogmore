"""Tests for URL Aliases / Path Redirects (Migration Helper)."""

from pathlib import Path

from blogmore.generator import SiteGenerator
from blogmore.site_config import SiteConfig


def test_redirect_generation(tmp_path: Path) -> None:
    """Test that post and page redirects are correctly generated.

    Args:
        tmp_path: The temporary path fixture provided by pytest.
    """
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create a post with redirects
    post_file = content_dir / "2024-01-01-redirect-post.md"
    post_file.write_text(
        "---\n"
        "title: My Redirect Post\n"
        "date: 2024-01-01\n"
        "redirect_from:\n"
        "  - /old-post/path\n"
        "  - /old-post/path-with-slash/\n"
        "  - /old-post/file.html\n"
        "---\n"
        "Post content."
    )

    # Create a page with redirects
    pages_dir = content_dir / "pages"
    pages_dir.mkdir()
    page_file = pages_dir / "redirect-page.md"
    page_file.write_text(
        "---\n"
        "title: My Redirect Page\n"
        "redirect_from:\n"
        "  - /old-page/path\n"
        "  - /old-page/file.html\n"
        "---\n"
        "Page content."
    )

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    generator = SiteGenerator(
        site_config=SiteConfig(
            content_dir=content_dir,
            output_dir=output_dir,
            site_url="https://example.com",
        )
    )
    generator.generate()

    # Verify that the post and page themselves were generated
    assert (output_dir / "2024" / "01" / "01" / "redirect-post.html").exists()
    assert (output_dir / "redirect-page.html").exists()

    # Verify the redirect paths:
    # 1. Post redirect: /old-post/path -> old-post/path/index.html (directory format)
    redirect1_path = output_dir / "old-post" / "path" / "index.html"
    assert redirect1_path.exists()
    html1 = redirect1_path.read_text()
    assert (
        '<meta http-equiv="refresh" content="0; url=/2024/01/01/redirect-post.html">'
        in html1
    )
    assert (
        '<link rel="canonical" href="https://example.com/2024/01/01/redirect-post.html">'
        in html1
    )

    # 2. Post redirect: /old-post/path-with-slash/ -> old-post/path-with-slash/index.html (directory format)
    redirect2_path = output_dir / "old-post" / "path-with-slash" / "index.html"
    assert redirect2_path.exists()
    html2 = redirect2_path.read_text()
    assert (
        '<meta http-equiv="refresh" content="0; url=/2024/01/01/redirect-post.html">'
        in html2
    )
    assert (
        '<link rel="canonical" href="https://example.com/2024/01/01/redirect-post.html">'
        in html2
    )

    # 3. Post redirect: /old-post/file.html -> old-post/file.html (file format)
    redirect3_path = output_dir / "old-post" / "file.html"
    assert redirect3_path.exists()
    html3 = redirect3_path.read_text()
    assert (
        '<meta http-equiv="refresh" content="0; url=/2024/01/01/redirect-post.html">'
        in html3
    )
    assert (
        '<link rel="canonical" href="https://example.com/2024/01/01/redirect-post.html">'
        in html3
    )

    # 4. Page redirect: /old-page/path -> old-page/path/index.html
    redirect4_path = output_dir / "old-page" / "path" / "index.html"
    assert redirect4_path.exists()
    html4 = redirect4_path.read_text()
    assert '<meta http-equiv="refresh" content="0; url=/redirect-page.html">' in html4
    assert (
        '<link rel="canonical" href="https://example.com/redirect-page.html">' in html4
    )

    # 5. Page redirect: /old-page/file.html -> old-page/file.html
    redirect5_path = output_dir / "old-page" / "file.html"
    assert redirect5_path.exists()
    html5 = redirect5_path.read_text()
    assert '<meta http-equiv="refresh" content="0; url=/redirect-page.html">' in html5
    assert (
        '<link rel="canonical" href="https://example.com/redirect-page.html">' in html5
    )
