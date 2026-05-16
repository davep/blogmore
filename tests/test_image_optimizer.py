"""Unit tests for the image_optimizer module."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from blogmore.image_optimizer import (
    DEFAULT_IMAGE_QUALITY,
    DEFAULT_IMAGE_WIDTHS,
    SUPPORTED_EXTENSIONS,
    ImageOptimizer,
    ImageVariant,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_image(path: Path, width: int = 1600, height: int = 900) -> Path:
    """Create a small test JPEG at *path* and return the path."""
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    img.save(path, format="JPEG")
    return path


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Test module-level constants."""

    def test_supported_extensions_contains_jpeg(self) -> None:
        """Test that JPEG is in supported extensions."""
        assert ".jpg" in SUPPORTED_EXTENSIONS
        assert ".jpeg" in SUPPORTED_EXTENSIONS

    def test_supported_extensions_contains_png(self) -> None:
        """Test that PNG is in supported extensions."""
        assert ".png" in SUPPORTED_EXTENSIONS

    def test_default_image_widths_are_positive(self) -> None:
        """Test that all default widths are positive integers."""
        assert all(isinstance(w, int) and w > 0 for w in DEFAULT_IMAGE_WIDTHS)

    def test_default_image_quality_in_range(self) -> None:
        """Test that the default quality is in the valid 1-95 range."""
        assert 1 <= DEFAULT_IMAGE_QUALITY <= 95


# ---------------------------------------------------------------------------
# ImageVariant
# ---------------------------------------------------------------------------


class TestImageVariant:
    """Test the ImageVariant dataclass."""

    def test_attributes(self) -> None:
        """Test that ImageVariant stores its fields correctly."""
        variant = ImageVariant(
            url="/images/photo-480w.webp", width=480, mime_type="image/webp"
        )
        assert variant.url == "/images/photo-480w.webp"
        assert variant.width == 480
        assert variant.mime_type == "image/webp"


# ---------------------------------------------------------------------------
# ImageOptimizer.process_image
# ---------------------------------------------------------------------------


class TestImageOptimizerProcessImage:
    """Test ImageOptimizer.process_image."""

    def test_generates_webp_variants(self, tmp_path: Path) -> None:
        """Test that WebP variant files are created on disk."""
        source = _make_image(tmp_path / "photo.jpg", width=1600)
        optimizer = ImageOptimizer(widths=[480, 768], quality=80)

        variants = optimizer.process_image(source, url_base="/images")

        assert len(variants) == 2
        assert (tmp_path / "photo-480w.webp").exists()
        assert (tmp_path / "photo-768w.webp").exists()

    def test_variant_urls_are_correct(self, tmp_path: Path) -> None:
        """Test that returned variant URLs have the right structure."""
        source = _make_image(tmp_path / "photo.jpg", width=1600)
        optimizer = ImageOptimizer(widths=[480, 768], quality=80)

        variants = optimizer.process_image(source, url_base="/images")

        urls = [v.url for v in variants]
        assert "/images/photo-480w.webp" in urls
        assert "/images/photo-768w.webp" in urls

    def test_variant_widths_match(self, tmp_path: Path) -> None:
        """Test that variant width metadata matches the requested widths."""
        source = _make_image(tmp_path / "photo.jpg", width=1600)
        optimizer = ImageOptimizer(widths=[480, 768], quality=80)

        variants = optimizer.process_image(source, url_base="/images")

        widths = [v.width for v in variants]
        assert widths == [480, 768]

    def test_mime_type_is_webp(self, tmp_path: Path) -> None:
        """Test that all variants have the webp MIME type."""
        source = _make_image(tmp_path / "photo.jpg", width=1600)
        optimizer = ImageOptimizer(widths=[480], quality=80)

        variants = optimizer.process_image(source, url_base="/img")

        assert all(v.mime_type == "image/webp" for v in variants)

    def test_skips_widths_larger_than_source(self, tmp_path: Path) -> None:
        """Test that widths exceeding the source width are skipped."""
        source = _make_image(tmp_path / "small.jpg", width=400)
        optimizer = ImageOptimizer(widths=[480, 768, 1200], quality=80)

        variants = optimizer.process_image(source, url_base="/images")

        # All requested widths (480, 768, 1200) exceed the 400px source.
        assert variants == []
        assert not (tmp_path / "small-480w.webp").exists()

    def test_only_smaller_widths_generated(self, tmp_path: Path) -> None:
        """Test that only widths below source width produce variants."""
        source = _make_image(tmp_path / "medium.jpg", width=900)
        optimizer = ImageOptimizer(widths=[480, 900, 1200], quality=80)

        variants = optimizer.process_image(source, url_base="/images")

        # Only 480 < 900; 900 and 1200 are skipped.
        assert len(variants) == 1
        assert variants[0].width == 480

    def test_variants_sorted_ascending(self, tmp_path: Path) -> None:
        """Test that variants are returned in ascending width order."""
        source = _make_image(tmp_path / "photo.jpg", width=2000)
        # Pass widths in reverse order to verify sorting.
        optimizer = ImageOptimizer(widths=[1200, 480, 768], quality=80)

        variants = optimizer.process_image(source, url_base="/images")

        widths = [v.width for v in variants]
        assert widths == sorted(widths)

    def test_handles_png_source(self, tmp_path: Path) -> None:
        """Test that PNG source images are also processed."""
        path = tmp_path / "logo.png"
        img = Image.new("RGBA", (1600, 900), color=(200, 100, 50, 255))
        img.save(path, format="PNG")

        optimizer = ImageOptimizer(widths=[480], quality=80)
        variants = optimizer.process_image(path, url_base="/images")

        assert len(variants) == 1
        assert (tmp_path / "logo-480w.webp").exists()

    def test_returns_empty_list_for_missing_file(self, tmp_path: Path) -> None:
        """Test that a missing source file returns an empty list."""
        missing = tmp_path / "nonexistent.jpg"
        optimizer = ImageOptimizer(widths=[480], quality=80)

        variants = optimizer.process_image(missing, url_base="/images")

        assert variants == []

    def test_url_base_trailing_slash_stripped(self, tmp_path: Path) -> None:
        """Test that a trailing slash in url_base is stripped from variant URLs."""
        source = _make_image(tmp_path / "photo.jpg", width=1600)
        optimizer = ImageOptimizer(widths=[480], quality=80)

        variants = optimizer.process_image(source, url_base="/images/")

        assert variants[0].url == "/images/photo-480w.webp"

    def test_quality_accepted_without_error(self, tmp_path: Path) -> None:
        """Test that different quality values are accepted without raising errors."""
        source = _make_image(tmp_path / "photo.jpg", width=1600)

        for quality in (1, 50, 85, 95):
            # Remove any existing variant before regenerating.
            variant = tmp_path / "photo-480w.webp"
            if variant.exists():
                variant.unlink()

            optimizer = ImageOptimizer(widths=[480], quality=quality)
            variants = optimizer.process_image(source, url_base="/images")
            assert len(variants) == 1
            assert variant.exists()
