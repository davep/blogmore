"""Unit tests for the icons module."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from PIL import Image

from blogmore.icons import IconGenerator, detect_source_icon


class TestDetectSourceIcon:
    """Test the detect_source_icon function."""

    def test_detect_custom_filename(self, tmp_path: Path) -> None:
        """Test detecting a custom icon filename."""
        extras_dir = tmp_path / "extras"
        extras_dir.mkdir()

        # Create a custom icon file
        custom_icon = extras_dir / "my-logo.png"
        custom_icon.touch()

        result = detect_source_icon(extras_dir, "my-logo.png")
        assert result == custom_icon

    def test_detect_custom_filename_not_found(self, tmp_path: Path) -> None:
        """Test detecting a custom icon that doesn't exist."""
        extras_dir = tmp_path / "extras"
        extras_dir.mkdir()

        result = detect_source_icon(extras_dir, "nonexistent.png")
        assert result is None

    def test_detect_default_icon_png(self, tmp_path: Path) -> None:
        """Test detecting default icon.png."""
        extras_dir = tmp_path / "extras"
        extras_dir.mkdir()

        # Create default icon file
        icon = extras_dir / "icon.png"
        icon.touch()

        result = detect_source_icon(extras_dir, None)
        assert result == icon

    def test_detect_default_icon_jpg(self, tmp_path: Path) -> None:
        """Test detecting default icon.jpg."""
        extras_dir = tmp_path / "extras"
        extras_dir.mkdir()

        # Create default icon file
        icon = extras_dir / "icon.jpg"
        icon.touch()

        result = detect_source_icon(extras_dir, None)
        assert result == icon

    def test_detect_source_icon_png(self, tmp_path: Path) -> None:
        """Test detecting source-icon.png."""
        extras_dir = tmp_path / "extras"
        extras_dir.mkdir()

        # Create source-icon file
        icon = extras_dir / "source-icon.png"
        icon.touch()

        result = detect_source_icon(extras_dir, None)
        assert result == icon

    def test_detect_app_icon_png(self, tmp_path: Path) -> None:
        """Test detecting app-icon.png."""
        extras_dir = tmp_path / "extras"
        extras_dir.mkdir()

        # Create app-icon file
        icon = extras_dir / "app-icon.png"
        icon.touch()

        result = detect_source_icon(extras_dir, None)
        assert result == icon

    def test_detect_priority_order(self, tmp_path: Path) -> None:
        """Test that icon.png has priority over other defaults."""
        extras_dir = tmp_path / "extras"
        extras_dir.mkdir()

        # Create multiple icon files
        (extras_dir / "icon.png").touch()
        (extras_dir / "icon.jpg").touch()
        (extras_dir / "source-icon.png").touch()

        result = detect_source_icon(extras_dir, None)
        assert result == extras_dir / "icon.png"

    def test_detect_no_icon_found(self, tmp_path: Path) -> None:
        """Test when no icon is found."""
        extras_dir = tmp_path / "extras"
        extras_dir.mkdir()

        result = detect_source_icon(extras_dir, None)
        assert result is None

    def test_detect_extras_dir_not_exists(self, tmp_path: Path) -> None:
        """Test when extras directory doesn't exist."""
        extras_dir = tmp_path / "extras"

        result = detect_source_icon(extras_dir, None)
        assert result is None


class TestIconGenerator:
    """Test the IconGenerator class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test initializing IconGenerator."""
        source_image = tmp_path / "icon.png"
        output_dir = tmp_path / "icons"

        generator = IconGenerator(source_image, output_dir)

        assert generator.source_image == source_image
        assert generator.output_dir == output_dir

    @patch("blogmore.icons.Image")
    def test_generate_all_creates_output_dir(
        self, mock_image_module: Mock, tmp_path: Path
    ) -> None:
        """Test that generate_all creates output directory."""
        source_image = tmp_path / "icon.png"
        output_dir = tmp_path / "icons"

        # Create a mock image
        mock_img = MagicMock()
        mock_img.mode = "RGBA"
        mock_image_module.open.return_value.__enter__.return_value = mock_img

        generator = IconGenerator(source_image, output_dir)
        generator.generate_all()

        assert output_dir.exists()

    @patch("blogmore.icons.Image")
    def test_generate_all_rgb_image(
        self, mock_image_module: Mock, tmp_path: Path
    ) -> None:
        """Test generating icons from RGB image."""
        source_image = tmp_path / "icon.png"
        output_dir = tmp_path / "icons"

        # Create a mock RGB image
        mock_img = MagicMock()
        mock_img.mode = "RGB"
        mock_image_module.open.return_value.__enter__.return_value = mock_img

        generator = IconGenerator(source_image, output_dir)
        result = generator.generate_all()

        # Should generate all expected icon files
        assert "favicon.ico" in result
        assert "favicon-16x16.png" in result
        assert "favicon-32x32.png" in result
        assert "favicon-96x96.png" in result
        assert "apple-touch-icon.png" in result
        assert "apple-touch-icon-120.png" in result
        assert "apple-touch-icon-152.png" in result
        assert "apple-touch-icon-167.png" in result
        assert "apple-touch-icon-precomposed.png" in result
        assert "android-chrome-192x192.png" in result
        assert "android-chrome-512x512.png" in result
        assert "mstile-70x70.png" in result
        assert "mstile-144x144.png" in result
        assert "mstile-150x150.png" in result
        assert "mstile-310x310.png" in result
        assert "mstile-310x150.png" in result
        assert "site.webmanifest" in result
        assert "browserconfig.xml" in result

    @patch("blogmore.icons.Image")
    def test_generate_all_converts_grayscale(
        self, mock_image_module: Mock, tmp_path: Path
    ) -> None:
        """Test that grayscale images are converted to RGBA."""
        source_image = tmp_path / "icon.png"
        output_dir = tmp_path / "icons"

        # Create a mock grayscale image
        mock_img = MagicMock()
        mock_img.mode = "L"
        mock_converted = MagicMock()
        mock_converted.mode = "RGBA"
        mock_img.convert.return_value = mock_converted
        mock_image_module.open.return_value.__enter__.return_value = mock_img

        generator = IconGenerator(source_image, output_dir)
        generator.generate_all()

        # Should have called convert
        mock_img.convert.assert_called_once_with("RGBA")

    @patch("blogmore.icons.Image")
    def test_generate_favicon(self, mock_image_module: Mock, tmp_path: Path) -> None:
        """Test generating favicon.ico."""
        source_image = tmp_path / "icon.png"
        output_dir = tmp_path / "icons"
        output_dir.mkdir()

        # Create a mock image
        mock_img = MagicMock()
        mock_img.mode = "RGBA"
        mock_resized = MagicMock()
        mock_resized.mode = "RGBA"
        mock_img.resize.return_value = mock_resized

        generator = IconGenerator(source_image, output_dir)
        result = generator._generate_favicon(mock_img)

        assert result == output_dir / "favicon.ico"
        # Should resize for 16, 32, 48 sizes
        assert mock_img.resize.call_count == 3

    @patch("blogmore.icons.Image")
    def test_generate_png_icon(self, mock_image_module: Mock, tmp_path: Path) -> None:
        """Test generating a PNG icon."""
        source_image = tmp_path / "icon.png"
        output_dir = tmp_path / "icons"
        output_dir.mkdir()

        # Create a mock image
        mock_img = MagicMock()
        mock_resized = MagicMock()
        mock_img.resize.return_value = mock_resized

        generator = IconGenerator(source_image, output_dir)
        result = generator._generate_png_icon(mock_img, 180, "apple-touch-icon.png")

        assert result == output_dir / "apple-touch-icon.png"
        mock_img.resize.assert_called_once()
        mock_resized.save.assert_called_once()

    @patch("blogmore.icons.Image")
    def test_generate_all_handles_errors(
        self, mock_image_module: Mock, tmp_path: Path
    ) -> None:
        """Test that generate_all handles errors gracefully."""
        source_image = tmp_path / "icon.png"
        output_dir = tmp_path / "icons"

        # Make Image.open raise an exception
        mock_image_module.open.side_effect = Exception("Test error")

        generator = IconGenerator(source_image, output_dir)
        result = generator.generate_all()

        # Should return empty dict on error
        assert result == {}

    def test_generate_all_with_real_image(self, tmp_path: Path) -> None:
        """Test generating icons with a real image."""
        source_image = tmp_path / "icon.png"
        output_dir = tmp_path / "icons"

        # Create a real test image
        img = Image.new("RGBA", (512, 512), (255, 0, 0, 255))
        img.save(source_image)

        generator = IconGenerator(source_image, output_dir)
        result = generator.generate_all()

        # Check that all icons were generated
        assert "favicon.ico" in result
        assert "favicon-16x16.png" in result
        assert "favicon-32x32.png" in result
        assert "favicon-96x96.png" in result
        assert "apple-touch-icon.png" in result
        assert "apple-touch-icon-120.png" in result
        assert "apple-touch-icon-152.png" in result
        assert "apple-touch-icon-167.png" in result
        assert "apple-touch-icon-precomposed.png" in result
        assert "android-chrome-192x192.png" in result
        assert "android-chrome-512x512.png" in result
        assert "mstile-70x70.png" in result
        assert "mstile-144x144.png" in result
        assert "mstile-150x150.png" in result
        assert "mstile-310x310.png" in result
        assert "mstile-310x150.png" in result
        assert "site.webmanifest" in result
        assert "browserconfig.xml" in result

        # Check that files exist
        assert (output_dir / "favicon.ico").exists()
        assert (output_dir / "favicon-16x16.png").exists()
        assert (output_dir / "favicon-32x32.png").exists()
        assert (output_dir / "favicon-96x96.png").exists()
        assert (output_dir / "apple-touch-icon.png").exists()
        assert (output_dir / "apple-touch-icon-120.png").exists()
        assert (output_dir / "apple-touch-icon-152.png").exists()
        assert (output_dir / "apple-touch-icon-167.png").exists()
        assert (output_dir / "apple-touch-icon-precomposed.png").exists()
        assert (output_dir / "android-chrome-192x192.png").exists()
        assert (output_dir / "android-chrome-512x512.png").exists()
        assert (output_dir / "mstile-70x70.png").exists()
        assert (output_dir / "mstile-144x144.png").exists()
        assert (output_dir / "mstile-150x150.png").exists()
        assert (output_dir / "mstile-310x310.png").exists()
        assert (output_dir / "mstile-310x150.png").exists()
        assert (output_dir / "site.webmanifest").exists()
        assert (output_dir / "browserconfig.xml").exists()

        # Verify the images are the correct size
        apple_180 = Image.open(output_dir / "apple-touch-icon.png")
        assert apple_180.size == (180, 180)

        apple_120 = Image.open(output_dir / "apple-touch-icon-120.png")
        assert apple_120.size == (120, 120)

        apple_152 = Image.open(output_dir / "apple-touch-icon-152.png")
        assert apple_152.size == (152, 152)

        apple_167 = Image.open(output_dir / "apple-touch-icon-167.png")
        assert apple_167.size == (167, 167)

        android_192 = Image.open(output_dir / "android-chrome-192x192.png")
        assert android_192.size == (192, 192)

        android_512 = Image.open(output_dir / "android-chrome-512x512.png")
        assert android_512.size == (512, 512)

        mstile_150 = Image.open(output_dir / "mstile-150x150.png")
        assert mstile_150.size == (150, 150)

        # Check wide tile dimensions
        wide_tile = Image.open(output_dir / "mstile-310x150.png")
        assert wide_tile.size == (310, 150)
