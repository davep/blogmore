"""Tests for image optimization and responsive images."""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import Element

import pytest

from blogmore.image_manager import ImageManager, OptimizedImage
from blogmore.markdown.optimized_images import (
    IMAGE_LINK_RE,
    OptimizedImageInlineProcessor,
)
from blogmore.site_config import SiteConfig


@pytest.fixture
def site_config(tmp_path):
    return SiteConfig(
        output_dir=tmp_path / "output",
        content_dir=tmp_path / "content",
        optimize_images=True,
        image_widths=[400, 800],
        image_quality=80,
    )


@pytest.fixture
def image_manager(site_config, tmp_path):
    cache_dir = tmp_path / "cache"
    return ImageManager(site_config, cache_dir)


class TestImageManager:
    """Test the ImageManager class."""

    @patch("PIL.Image.open")
    @patch("blogmore.image_manager.ImageManager._get_file_hash")
    def test_get_optimized_image_success(
        self, mock_hash, mock_open, image_manager, tmp_path
    ):
        """Test successful image optimization."""
        mock_hash.return_value = "fakehash"

        # Mock PIL Image
        mock_img = MagicMock()
        mock_img.size = (1600, 900)
        mock_open.return_value.__enter__.return_value = mock_img

        source_path = tmp_path / "test.jpg"
        source_path.touch()

        optimized = image_manager.get_optimized_image(source_path)

        assert optimized is not None
        assert optimized.original_width == 1600
        assert optimized.original_height == 900
        assert optimized.hash == "fakehash"
        assert 400 in optimized.resized_paths
        assert 800 in optimized.resized_paths
        assert 400 in optimized.webp_paths

        # Verify resize calls
        # 1600 -> 400 (scale 0.25)
        # 1600 -> 800 (scale 0.5)
        assert mock_img.resize.call_count == 2

    def test_get_optimized_image_unsupported(self, image_manager, tmp_path):
        """Test that unsupported formats are bypassed."""
        svg_path = tmp_path / "test.svg"
        svg_path.touch()
        assert image_manager.get_optimized_image(svg_path) is None

        gif_path = tmp_path / "test.gif"
        gif_path.touch()
        assert image_manager.get_optimized_image(gif_path) is None

    @patch("PIL.Image.open")
    @patch("blogmore.image_manager.ImageManager._get_file_hash")
    def test_no_upscaling(self, mock_hash, mock_open, image_manager, tmp_path):
        """Test that images are not upscaled."""
        mock_hash.return_value = "smallhash"

        mock_img = MagicMock()
        mock_img.size = (600, 400)
        mock_open.return_value.__enter__.return_value = mock_img

        source_path = tmp_path / "small.jpg"
        source_path.touch()

        # site_config image_widths are [400, 800]
        optimized = image_manager.get_optimized_image(source_path)

        assert optimized is not None
        assert 400 in optimized.resized_paths
        assert 800 not in optimized.resized_paths  # 800 > 600, so skip


class TestOptimizedImageProcessor:
    """Test the OptimizedImageInlineProcessor Markdown extension."""

    def test_is_local_image(self):
        """Test local image detection logic."""
        processor = OptimizedImageInlineProcessor(IMAGE_LINK_RE, None, None, None)

        assert processor._is_local_image("images/test.jpg") is True
        assert processor._is_local_image("/images/test.jpg") is True
        assert processor._is_local_image("http://example.com/img.jpg") is False
        assert processor._is_local_image("https://example.com/img.jpg") is False
        assert processor._is_local_image("//example.com/img.jpg") is False

    def test_transform_img_to_picture(self, image_manager, tmp_path):
        """Test the transformation of ![]() to <picture>."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        img_path = content_dir / "photo.jpg"
        img_path.touch()

        # Mock optimized data
        optimized = OptimizedImage(
            source_path=img_path,
            original_width=1000,
            original_height=500,
            hash="abc",
            resized_paths={400: "photo-400.jpg", 800: "photo-800.jpg"},
            webp_paths={400: "photo-400.webp", 800: "photo-800.webp"},
        )
        image_manager.get_optimized_image = MagicMock(return_value=optimized)

        processor = OptimizedImageInlineProcessor(
            IMAGE_LINK_RE, None, image_manager, content_dir
        )

        # Create a mock Match object
        text = "![Some text](photo.jpg)"
        match = next(re.finditer(IMAGE_LINK_RE, text))

        picture = processor.handleMatch(match)

        assert picture is not None
        assert picture.tag == "picture"

        # Check <source> tags
        sources = picture.findall("source")
        assert len(sources) == 2
        assert sources[0].get("type") == "image/webp"
        assert "photo-400.webp 400w" in sources[0].get("srcset")
        assert "photo-800.webp 800w" in sources[0].get("srcset")

        # Check fallback <img>
        fallback = picture.find("img")
        assert fallback is not None
        assert fallback.get("alt") == "Some text"
        assert "/static/images/optimized/photo-800.jpg" in fallback.get("src")
        assert fallback.get("width") == "1000"
        assert fallback.get("height") == "500"
        assert fallback.get("loading") == "lazy"

    def test_preserve_centre_fragment(self, image_manager, tmp_path):
        """Test that #centre fragment is preserved in transformed image."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        img_path = content_dir / "photo.jpg"
        img_path.touch()

        optimized = OptimizedImage(
            source_path=img_path,
            original_width=1000,
            original_height=500,
            hash="abc",
            resized_paths={800: "photo-800.jpg"},
            webp_paths={800: "photo-800.webp"},
        )
        image_manager.get_optimized_image = MagicMock(return_value=optimized)

        processor = OptimizedImageInlineProcessor(
            IMAGE_LINK_RE, None, image_manager, content_dir
        )

        text = "![alt](photo.jpg#centre)"
        match = next(re.finditer(IMAGE_LINK_RE, text))

        picture = processor.handleMatch(match)
        fallback = picture.find("img")
        assert fallback.get("src").endswith("#centre")
