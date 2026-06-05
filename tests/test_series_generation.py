"""Integration and unit tests for the series feature in BlogMore."""

from pathlib import Path

import pytest

from blogmore.generator.site import SiteGenerator
from blogmore.parser import PostParser
from blogmore.site_config import SiteConfig


def test_parse_series_frontmatter(tmp_path: Path) -> None:
    """The parser correctly extracts series metadata in various formats."""
    # 1. Single string series
    post_1_path = tmp_path / "post-1.md"
    post_1_path.write_text(
        "---\ntitle: Post 1\ndate: 2024-01-01\nseries: My Series\n---\n\nContent 1."
    )

    # 2. List of series
    post_2_path = tmp_path / "post-2.md"
    post_2_path.write_text(
        "---\ntitle: Post 2\ndate: 2024-01-02\nseries: [My Series, Another Series]\n---\n\nContent 2."
    )

    # 3. Absent series
    post_3_path = tmp_path / "post-3.md"
    post_3_path.write_text("---\ntitle: Post 3\ndate: 2024-01-03\n---\n\nContent 3.")

    parser = PostParser(site_url="")
    post_1 = parser.parse_file(post_1_path)
    post_2 = parser.parse_file(post_2_path)
    post_3 = parser.parse_file(post_3_path)

    assert post_1.series == ["My Series"]
    assert post_2.series == ["My Series", "Another Series"]
    assert post_3.series == []


def test_parse_series_invalid_raises(tmp_path: Path) -> None:
    """An invalid series type (e.g. an integer or dict) in frontmatter raises ValueError."""
    post_path = tmp_path / "invalid-series.md"
    post_path.write_text("---\ntitle: Post\nseries: {key: value}\n---\n\nContent.")
    parser = PostParser(site_url="")
    with pytest.raises(
        ValueError, match="Post 'series' in frontmatter must be a string or list"
    ):
        parser.parse_file(post_path)


def test_series_navigation_info(tmp_path: Path, temp_output_dir: Path) -> None:
    """Series navigation info (prev/next links) is correctly calculated chronologically."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create 3 posts in chronological order
    (content_dir / "post-a.md").write_text(
        "---\ntitle: Part 1\ndate: 2024-01-01\nseries: Static Site\n---\n\nContent 1."
    )
    (content_dir / "post-b.md").write_text(
        "---\ntitle: Part 2\ndate: 2024-01-02\nseries: Static Site\n---\n\nContent 2."
    )
    (content_dir / "post-c.md").write_text(
        "---\ntitle: Part 3\ndate: 2024-01-03\nseries: Static Site\n---\n\nContent 3."
    )

    # Create an unrelated post in the same series with an older date to verify chronological sorting
    (content_dir / "post-early.md").write_text(
        "---\ntitle: Prologue\ndate: 2023-12-25\nseries: Static Site\n---\n\nContent 0."
    )

    # Create a post in a single-post series
    (content_dir / "post-solo.md").write_text(
        "---\ntitle: Solo Post\ndate: 2024-01-04\nseries: Solo Series\n---\n\nContent."
    )

    generator = SiteGenerator(
        site_config=SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
        )
    )
    # Generate the site
    generator.generate()
    # Inspect the generated posts
    posts = generator.posts

    # Find posts in list
    posts_by_title = {p.title: p for p in posts}
    prologue = posts_by_title["Prologue"]
    part_1 = posts_by_title["Part 1"]
    part_2 = posts_by_title["Part 2"]
    part_3 = posts_by_title["Part 3"]
    solo = posts_by_title["Solo Post"]

    # Assert prologue (first post)
    assert len(prologue.series_info) == 1
    info_pro = prologue.series_info[0]
    assert info_pro["name"] == "Static Site"
    assert info_pro["prev_post"] is None
    assert info_pro["next_post"] == part_1

    # Assert part 1 (second post)
    assert len(part_1.series_info) == 1
    info_p1 = part_1.series_info[0]
    assert info_p1["prev_post"] == prologue
    assert info_p1["next_post"] == part_2

    # Assert part 2 (third post)
    assert len(part_2.series_info) == 1
    info_p2 = part_2.series_info[0]
    assert info_p2["prev_post"] == part_1
    assert info_p2["next_post"] == part_3

    # Assert part 3 (last post)
    assert len(part_3.series_info) == 1
    info_p3 = part_3.series_info[0]
    assert info_p3["prev_post"] == part_2
    assert info_p3["next_post"] is None

    # Assert solo post (only post in series)
    assert len(solo.series_info) == 1
    info_solo = solo.series_info[0]
    assert info_solo["name"] == "Solo Series"
    assert info_solo["prev_post"] is None
    assert info_solo["next_post"] is None


def test_series_pages_generation(tmp_path: Path, temp_output_dir: Path) -> None:
    """The generator writes correct paginated series archive files."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Generate 12 posts to force pagination (since posts per page is 10)
    for i in range(1, 13):
        (content_dir / f"post-{i}.md").write_text(
            f"---\ntitle: Post {i}\ndate: 2024-01-{i:02d}\nseries: My Big Series\n---\n\nContent {i}."
        )

    generator = SiteGenerator(
        site_config=SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
            series_path="custom-series/{slug}/first-page.html",
            page_1_path="first-page.html",
            page_n_path="page-{page}.html",
        )
    )
    generator.generate()

    # Check page 1 output
    page_1_file = (
        temp_output_dir / "custom-series" / "my-big-series" / "first-page.html"
    )
    assert page_1_file.exists()
    page_1_content = page_1_file.read_text()
    assert 'Posts in series "My Big Series"' in page_1_content
    # Check that it renders post summaries
    assert "Post 1" in page_1_content
    assert "Post 10" in page_1_content
    # Since page size is 10, Post 11 and 12 should not be on page 1
    assert "Post 11" not in page_1_content

    # Check page 2 output
    page_2_file = temp_output_dir / "custom-series" / "my-big-series" / "page-2.html"
    assert page_2_file.exists()
    page_2_content = page_2_file.read_text()
    assert "Post 11" in page_2_content
    assert "Post 12" in page_2_content


def test_series_rendering_in_post_pages(tmp_path: Path, temp_output_dir: Path) -> None:
    """The generated post pages include top and bottom series boxes linking to archives."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    (content_dir / "post-1.md").write_text(
        "---\ntitle: Part 1\ndate: 2024-01-01\nseries: Designing Site\n---\n\nContent 1."
    )
    (content_dir / "post-2.md").write_text(
        "---\ntitle: Part 2\ndate: 2024-01-02\nseries: Designing Site\n---\n\nContent 2."
    )

    generator = SiteGenerator(
        site_config=SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
        )
    )
    generator.generate()

    # Read Part 1 post page
    post_1_file = temp_output_dir / "2024" / "01" / "01" / "post-1.html"
    assert post_1_file.exists()
    post_1_content = post_1_file.read_text()

    # It must contain the top and bottom series info boxes (with clean_urls = False)
    expected_non_clean = (
        'This post is part of the <a href="/series/designing-site/index.html" '
        'class="post-series-link">"Designing Site"</a> series.'
    )
    assert post_1_content.count(expected_non_clean) == 2
    # Since it's the first post, it should only show "Next" (not "Previous")
    assert "Next »" in post_1_content
    assert "« Previous" not in post_1_content


def test_series_rendering_in_post_pages_clean_urls(
    tmp_path: Path, temp_output_dir: Path
) -> None:
    """The generated post pages include top/bottom series boxes linking to clean URLs when enabled."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    (content_dir / "post-1.md").write_text(
        "---\ntitle: Part 1\ndate: 2024-01-01\nseries: Designing Site\n---\n\nContent 1."
    )

    generator = SiteGenerator(
        site_config=SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
            clean_urls=True,
        )
    )
    generator.generate()

    # Read Part 1 post page
    post_1_file = temp_output_dir / "2024" / "01" / "01" / "post-1.html"
    assert post_1_file.exists()
    post_1_content = post_1_file.read_text()

    # It must contain the top and bottom series info boxes (with clean_urls = True)
    expected_clean = (
        'This post is part of the <a href="/series/designing-site/" '
        'class="post-series-link">"Designing Site"</a> series.'
    )
    assert post_1_content.count(expected_clean) == 2


def test_series_index_generation(tmp_path: Path, temp_output_dir: Path) -> None:
    """The generator writes correct series index page and adds it to navigation and sitemap."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create posts in two different series
    (content_dir / "post-1.md").write_text(
        "---\ntitle: Post 1\ndate: 2024-01-01\nseries: B Series\n---\n\nContent 1."
    )
    (content_dir / "post-2.md").write_text(
        "---\ntitle: Post 2\ndate: 2024-01-02\nseries: A Series\n---\n\nContent 2."
    )
    (content_dir / "post-3.md").write_text(
        "---\ntitle: Post 3\ndate: 2024-01-03\nseries: B Series\n---\n\nContent 3."
    )

    # Test index generation with default series_index_path ("series.html") and clean_urls = False
    generator = SiteGenerator(
        site_config=SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
            with_sitemap=True,
        )
    )
    generator.generate()

    # Verify series index file is created at the default path
    index_file = temp_output_dir / "series.html"
    assert index_file.exists()
    index_content = index_file.read_text()

    # Verify header nav contains the Series link between Tags and Archive
    nav_start = index_content.find("<nav>")
    nav_end = index_content.find("</nav>")
    assert nav_start != -1 and nav_end != -1
    nav_content = index_content[nav_start:nav_end]

    tags_idx = nav_content.find('href="/tags.html"')
    series_idx = nav_content.find('href="/series.html"')
    archive_idx = nav_content.find('href="/archive.html"')
    assert tags_idx != -1
    assert series_idx != -1
    assert archive_idx != -1
    assert tags_idx < series_idx < archive_idx

    # Verify series are listed in alphabetical order (A Series first, B Series second)
    pos_a = index_content.find("A Series")
    pos_b = index_content.find("B Series")
    assert pos_a != -1 and pos_b != -1
    assert pos_a < pos_b

    # Verify post count format
    assert "A Series" in index_content
    assert "(1 post)" in index_content
    assert "B Series" in index_content
    assert "(2 posts)" in index_content

    # Verify links to the series pages
    assert '<a href="/series/a-series/index.html" class="series-link">' in index_content
    assert '<a href="/series/b-series/index.html" class="series-link">' in index_content

    # Verify it is present in sitemap.xml
    sitemap_file = temp_output_dir / "sitemap.xml"
    assert sitemap_file.exists()
    sitemap_content = sitemap_file.read_text()
    assert "/series.html" in sitemap_content


def test_series_index_generation_clean_urls_and_custom_path(
    tmp_path: Path, temp_output_dir: Path
) -> None:
    """The series index page respects custom path and clean_urls configuration."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    (content_dir / "post-1.md").write_text(
        "---\ntitle: Post 1\ndate: 2024-01-01\nseries: My Series\n---\n\nContent 1."
    )

    # Test custom series_index_path and clean_urls = True
    generator = SiteGenerator(
        site_config=SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
            series_index_path="custom-series/index.html",
            clean_urls=True,
            with_sitemap=True,
        )
    )
    generator.generate()

    index_file = temp_output_dir / "custom-series" / "index.html"
    assert index_file.exists()
    index_content = index_file.read_text()

    # Navigation link must be clean (points to "/custom-series/")
    assert '<li><a href="/custom-series/">Series</a></li>' in index_content

    # Link to series page must be clean (points to "/series/my-series/")
    assert '<a href="/series/my-series/" class="series-link">' in index_content

    # Verify sitemap URL is clean (points to "/custom-series/")
    sitemap_file = temp_output_dir / "sitemap.xml"
    assert sitemap_file.exists()
    sitemap_content = sitemap_file.read_text()
    assert "/custom-series/" in sitemap_content
    assert "/custom-series/index.html" not in sitemap_content


def test_no_series_index_when_no_series(tmp_path: Path, temp_output_dir: Path) -> None:
    """The series index page is not created and Series nav link is absent when there are no series."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    (content_dir / "post-1.md").write_text(
        "---\ntitle: Post 1\ndate: 2024-01-01\n---\n\nContent 1."
    )

    generator = SiteGenerator(
        site_config=SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
        )
    )
    generator.generate()

    # series.html must not exist
    assert not (temp_output_dir / "series.html").exists()

    # Index page navigation must not contain Series link
    post_file = temp_output_dir / "2024" / "01" / "01" / "post-1.html"
    assert post_file.exists()
    post_content = post_file.read_text()
    assert "Series" not in post_content


def test_series_index_with_read_time(tmp_path: Path, temp_output_dir: Path) -> None:
    """The series index page shows total reading time when with_read_time is enabled."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create post 1 with 400 words (2 mins at 200 wpm)
    words_1 = "word " * 400
    (content_dir / "post-1.md").write_text(
        f"---\ntitle: Post 1\ndate: 2024-01-01\nseries: My Series\n---\n\n{words_1}"
    )

    # Create post 2 with 600 words (3 mins at 200 wpm)
    words_2 = "word " * 600
    (content_dir / "post-2.md").write_text(
        f"---\ntitle: Post 2\ndate: 2024-01-02\nseries: My Series\n---\n\n{words_2}"
    )

    generator = SiteGenerator(
        site_config=SiteConfig(
            content_dir=content_dir,
            output_dir=temp_output_dir,
            with_read_time=True,
        )
    )
    generator.generate()

    index_file = temp_output_dir / "series.html"
    assert index_file.exists()
    index_content = index_file.read_text()

    # Verify post count and total reading time (2 + 3 = 5 min read)
    assert "(2 posts, 5 min read)" in index_content
