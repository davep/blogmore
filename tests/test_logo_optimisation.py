"""Tests for site logo image optimisation and responsive logo generation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from blogmore.generator.context import ContextBuilder
from blogmore.site_config import SiteConfig


@pytest.fixture
def site_config(tmp_path: Path) -> SiteConfig:
    """Return a SiteConfig with image optimisation enabled.

    Args:
        tmp_path: The pytest temporary directory path.

    Returns:
        A SiteConfig instance configured for testing image optimisation.
    """
    return SiteConfig(
        output_dir=tmp_path / "output",
        content_dir=tmp_path / "content",
        optimise_images=True,
        image_widths=[400, 800],
        image_quality=80,
        image_make_source_fallback=True,
        site_title="Test Blog",
    )


class TestLogoOptimisation:
    """Test site logo optimisation and responsive HTML generation."""

    @patch("PIL.Image.open")
    @patch("blogmore.image_manager.ImageManager._get_file_hash")
    def test_logo_optimisation_in_context_builder(
        self,
        mock_hash: MagicMock,
        mock_open: MagicMock,
        site_config: SiteConfig,
        tmp_path: Path,
    ) -> None:
        """Test that a local site logo is registered and optimized, producing site_logo_html.

        Args:
            mock_hash: Mock for the file hash helper.
            mock_open: Mock for PIL Image.open.
            site_config: The test site configuration.
            tmp_path: The temporary directory path.
        """
        mock_hash.return_value = "logohash"

        # Mock PIL Image for the logo
        mock_img = MagicMock()
        mock_img.size = (1200, 600)
        mock_img.mode = "RGB"
        mock_open.return_value.__enter__.return_value = mock_img

        # Configure local site logo (PNG is a standard format)
        site_config.sidebar_config = {"site_logo": "/images/logo.png"}
        site_config.content_dir = tmp_path / "content"

        # Create dummy logo source file in the content directory (under extras/)
        logo_dir = site_config.content_dir / "extras" / "images"
        logo_dir.mkdir(parents=True)
        logo_path = logo_dir / "logo.png"
        logo_path.touch()

        from blogmore.image_manager import ImageManager

        image_manager = ImageManager(site_config, tmp_path / "cache")

        # Let's register it to simulate the site generator
        image_manager.get_optimised_image(logo_path)

        context_builder = ContextBuilder(
            site_config,
            image_manager=image_manager,
        )

        context = context_builder.get_global_context()

        # The global context should contain the site_logo_html picture element
        assert context["site_logo_html"] is not None
        assert "<picture>" in context["site_logo_html"]
        assert 'type="image/webp"' in context["site_logo_html"]
        # For standard format originals, the fallback img src is the original itself
        assert context["site_logo"] == "/images/logo.png"
        # The alt tag should be the site title
        assert 'alt="Test Blog"' in context["site_logo_html"]

        # Now test with a WebP original logo (non-standard fallback format)
        site_config.sidebar_config = {"site_logo": "/images/logo.webp"}
        logo_webp_path = logo_dir / "logo.webp"
        logo_webp_path.touch()
        image_manager.get_optimised_image(logo_webp_path)

        context_builder_webp = ContextBuilder(
            site_config,
            image_manager=image_manager,
        )
        context_webp = context_builder_webp.get_global_context()
        assert context_webp["site_logo_html"] is not None
        # The fallback img src should be updated to point to the optimized fallback image (JPG)
        assert "/static/images/optimised/logo.webp" not in context_webp["site_logo"]
        assert context_webp["site_logo"].startswith("/static/images/optimised/")
        assert context_webp["site_logo"].endswith(".jpg")

    @patch("PIL.Image.open")
    @patch("blogmore.image_manager.ImageManager._get_file_hash")
    def test_logo_optimisation_bypassed_for_remote_url(
        self,
        mock_hash: MagicMock,
        mock_open: MagicMock,
        site_config: SiteConfig,
        tmp_path: Path,
    ) -> None:
        """Test that remote site logo URLs are not optimized.

        Args:
            mock_hash: Mock for the file hash helper.
            mock_open: Mock for PIL Image.open.
            site_config: The test site configuration.
            tmp_path: The temporary directory path.
        """
        # Configure remote site logo
        site_config.sidebar_config = {"site_logo": "https://example.com/logo.png"}
        site_config.content_dir = tmp_path / "content"

        from blogmore.image_manager import ImageManager

        image_manager = ImageManager(site_config, tmp_path / "cache")

        context_builder = ContextBuilder(
            site_config,
            image_manager=image_manager,
        )

        context = context_builder.get_global_context()

        # The global context should have site_logo_html set to None
        assert context["site_logo_html"] is None
        # The site_logo should remain the original URL
        assert context["site_logo"] == "https://example.com/logo.png"

    @patch("PIL.Image.open")
    @patch("blogmore.image_manager.ImageManager._get_file_hash")
    def test_logo_optimisation_bypassed_for_missing_file(
        self,
        mock_hash: MagicMock,
        mock_open: MagicMock,
        site_config: SiteConfig,
        tmp_path: Path,
    ) -> None:
        """Test that missing local site logo files are bypassed.

        Args:
            mock_hash: Mock for the file hash helper.
            mock_open: Mock for PIL Image.open.
            site_config: The test site configuration.
            tmp_path: The temporary directory path.
        """
        # Configure local site logo but do not create the file
        site_config.sidebar_config = {"site_logo": "/images/missing.png"}
        site_config.content_dir = tmp_path / "content"

        from blogmore.image_manager import ImageManager

        image_manager = ImageManager(site_config, tmp_path / "cache")

        context_builder = ContextBuilder(
            site_config,
            image_manager=image_manager,
        )

        context = context_builder.get_global_context()

        # The global context should have site_logo_html set to None
        assert context["site_logo_html"] is None
        # The site_logo should remain the original path
        assert context["site_logo"] == "/images/missing.png"
