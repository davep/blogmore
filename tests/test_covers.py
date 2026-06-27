"""Tests for the cover image generator module."""

import datetime as dt
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from PIL import Image

from blogmore.config import parse_site_config_from_dict
from blogmore.generator.covers import (
    CoverGenerator,
    _find_system_font,
    _get_font,
    _wrap_text,
)
from blogmore.parser import Post
from blogmore.site_config import SiteConfig


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Return a temporary directory Path."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


def test_wrap_text() -> None:
    """Test text wrapping helper."""
    font = _get_font("Inter", 16)
    text = "This is a very long post title that should be wrapped into multiple lines cleanly."
    wrapped = _wrap_text(text, font, max_width=200)
    assert len(wrapped) > 1
    assert " ".join(wrapped) == text


def test_find_system_font() -> None:
    """Test system font finding helper."""
    font_path = _find_system_font("Arial")
    # Arial might not exist on all test systems (e.g., bare Linux environments)
    # but the helper should either return a Path or None (no crashing)
    if font_path is not None:
        assert isinstance(font_path, Path)
        assert font_path.exists()


def test_get_font() -> None:
    """Test get_font fallback mechanisms."""
    font = _get_font("SomeNonExistentFontName-XYZ", 20)
    assert font is not None


def test_cover_generator_enabled_minimalist(temp_dir: Path) -> None:
    """Test generating a cover with minimalist template."""
    content_dir = temp_dir / "content"
    content_dir.mkdir()

    post_path = content_dir / "posts" / "my-test.md"
    post_path.parent.mkdir(parents=True, exist_ok=True)

    post = Post(
        path=post_path,
        title="Testing Minimalist Cover",
        content="This is the post content.",
        html_content="<p>This is the post content.</p>",
        date=dt.datetime(2026, 6, 27, 9, 0, 0),
        category="Python",
        tags=["pytest", "unit-test"],
        draft=False,
        metadata={"title": "Testing Minimalist Cover", "auto_cover": "minimalist"},
    )

    config_dict = {
        "auto_covers": {
            "enabled": False,  # disabled globally, but post auto_cover overrides it
            "layout": "minimalist",
            "background_type": "solid",
            "background_color": "#1e293b",
            "text_color": "#ffffff",
            "accent_color": "#38bdf8",
        }
    }

    kwargs, errors = parse_site_config_from_dict(config_dict, output_dir=temp_dir)
    assert not errors

    site_config = SiteConfig(output_dir=temp_dir, content_dir=content_dir, **kwargs)

    generator = CoverGenerator(site_config)
    generator.assign_cover_metadata([post])
    generator.generate_covers([post])

    # Verify metadata is updated
    assert post.metadata is not None
    assert post.metadata["cover"] == "static/images/auto_covers/posts-my-test.webp"

    # Check that file exists on disk
    expected_file = (
        temp_dir / "static" / "images" / "auto_covers" / "posts-my-test.webp"
    )
    assert expected_file.is_file()

    # Verify file dimensions
    with Image.open(expected_file) as img:
        assert img.size == (1200, 630)


def test_cover_generator_disabled_globally(temp_dir: Path) -> None:
    """Test cover generation is skipped if disabled and no local override."""
    content_dir = temp_dir / "content"
    content_dir.mkdir()

    post = Post(
        path=content_dir / "my-post.md",
        title="Test Post Title",
        content="Content.",
        html_content="<p>Content.</p>",
        date=dt.datetime(2026, 6, 27, 9, 0, 0),
        category="Python",
        tags=[],
        draft=False,
        metadata={"title": "Test Post Title"},  # no auto_cover override
    )

    config_dict = {
        "auto_covers": {
            "enabled": False,
        }
    }

    kwargs, errors = parse_site_config_from_dict(config_dict, output_dir=temp_dir)
    site_config = SiteConfig(output_dir=temp_dir, content_dir=content_dir, **kwargs)

    generator = CoverGenerator(site_config)
    generator.assign_cover_metadata([post])
    generator.generate_covers([post])

    # Should not have cover metadata
    assert post.metadata is None or "cover" not in post.metadata

    # No file generated
    expected_file = temp_dir / "static" / "images" / "auto_covers" / "my-post.webp"
    assert not expected_file.exists()


def test_custom_cover_precedence(temp_dir: Path) -> None:
    """Test that custom cover in post frontmatter takes absolute precedence."""
    content_dir = temp_dir / "content"
    content_dir.mkdir()

    post = Post(
        path=content_dir / "my-post.md",
        title="Test Post Title",
        content="Content.",
        html_content="<p>Content.</p>",
        date=dt.datetime(2026, 6, 27, 9, 0, 0),
        category="Python",
        tags=[],
        draft=False,
        metadata={
            "title": "Test Post Title",
            "cover": "images/custom.png",
            "auto_cover": "split",
        },
    )

    config_dict = {
        "auto_covers": {
            "enabled": True,
        }
    }

    kwargs, errors = parse_site_config_from_dict(config_dict, output_dir=temp_dir)
    site_config = SiteConfig(output_dir=temp_dir, content_dir=content_dir, **kwargs)

    generator = CoverGenerator(site_config)
    generator.assign_cover_metadata([post])
    generator.generate_covers([post])

    # Cover metadata must remain the custom cover
    assert post.metadata is not None
    assert post.metadata["cover"] == "images/custom.png"

    # No file generated in auto_covers
    expected_file = temp_dir / "static" / "images" / "auto_covers" / "my-post.webp"
    assert not expected_file.exists()


def test_auto_cover_none_explicit(temp_dir: Path) -> None:
    """Test post setting auto_cover: none overrides global enabled: true."""
    content_dir = temp_dir / "content"
    content_dir.mkdir()

    post = Post(
        path=content_dir / "my-post.md",
        title="Test Post Title",
        content="Content.",
        html_content="<p>Content.</p>",
        date=dt.datetime(2026, 6, 27, 9, 0, 0),
        category="Python",
        tags=[],
        draft=False,
        metadata={"title": "Test Post Title", "auto_cover": "none"},
    )

    config_dict = {
        "auto_covers": {
            "enabled": True,
        }
    }

    kwargs, errors = parse_site_config_from_dict(config_dict, output_dir=temp_dir)
    site_config = SiteConfig(output_dir=temp_dir, content_dir=content_dir, **kwargs)

    generator = CoverGenerator(site_config)
    generator.assign_cover_metadata([post])
    generator.generate_covers([post])

    # Cover metadata must be unchanged (no cover generated)
    assert post.metadata is not None
    assert "cover" not in post.metadata

    # No file generated in auto_covers
    expected_file = temp_dir / "static" / "images" / "auto_covers" / "my-post.webp"
    assert not expected_file.exists()


def test_split_and_editorial_layouts(temp_dir: Path) -> None:
    """Test split and editorial templates generate images correctly."""
    content_dir = temp_dir / "content"
    content_dir.mkdir()

    post_split = Post(
        path=content_dir / "post-split.md",
        title="Testing Split Layout Style",
        content="Content.",
        html_content="<p>Content.</p>",
        date=dt.datetime(2026, 6, 27, 9, 0, 0),
        category="Python",
        tags=[],
        draft=False,
        metadata={"title": "Testing Split Layout Style", "auto_cover": "split"},
    )

    post_edit = Post(
        path=content_dir / "post-edit.md",
        title="Testing Editorial Layout Style",
        content="Content.",
        html_content="<p>Content.</p>",
        date=dt.datetime(2026, 6, 27, 9, 0, 0),
        category="Python",
        tags=["tag1", "tag2"],
        draft=False,
        metadata={"title": "Testing Editorial Layout Style", "auto_cover": "editorial"},
    )

    config_dict = {
        "auto_covers": {
            "enabled": False,
            "gradient_colors": ["#000000", "#111111"],
        }
    }

    kwargs, errors = parse_site_config_from_dict(config_dict, output_dir=temp_dir)
    site_config = SiteConfig(output_dir=temp_dir, content_dir=content_dir, **kwargs)

    generator = CoverGenerator(site_config)
    generator.assign_cover_metadata([post_split, post_edit])
    generator.generate_covers([post_split, post_edit])

    assert post_split.metadata is not None
    assert post_edit.metadata is not None
    assert post_split.metadata["cover"] == "static/images/auto_covers/post-split.webp"
    assert post_edit.metadata["cover"] == "static/images/auto_covers/post-edit.webp"

    assert (
        temp_dir / "static" / "images" / "auto_covers" / "post-split.webp"
    ).is_file()
    assert (temp_dir / "static" / "images" / "auto_covers" / "post-edit.webp").is_file()


def test_cover_generator_caching(temp_dir: Path) -> None:
    """Test that cover generation correctly caches and reuses files."""
    content_dir = temp_dir / "content"
    content_dir.mkdir()

    post = Post(
        path=content_dir / "cache-test.md",
        title="Cache Test Post",
        content="Some content.",
        html_content="<p>Some content.</p>",
        date=dt.datetime(2026, 6, 27, 9, 0, 0),
        category="Python",
        tags=[],
        draft=False,
        metadata={"title": "Cache Test Post"},
    )

    config_dict = {
        "auto_covers": {
            "enabled": True,
        }
    }

    kwargs, errors = parse_site_config_from_dict(config_dict, output_dir=temp_dir)
    site_config = SiteConfig(output_dir=temp_dir, content_dir=content_dir, **kwargs)

    generator = CoverGenerator(site_config)
    assert generator.cache_dir is not None

    # First run: cache miss, renders image
    generator.assign_cover_metadata([post])
    generator.generate_covers([post])

    # Check cache directory contains the hashed file
    state_hash = generator._compute_state_hash(post, "minimalist")
    cached_file = generator.cache_dir / f"{state_hash}.webp"
    assert cached_file.is_file()

    # Destination file should also exist
    dest_file = temp_dir / "static" / "images" / "auto_covers" / "cache-test.webp"
    assert dest_file.is_file()

    # Get first mtime of cached file
    first_mtime = cached_file.stat().st_mtime

    # Second run: cache hit, should NOT regenerate (mtime remains unchanged)
    generator.generate_covers([post])
    assert cached_file.stat().st_mtime == first_mtime
