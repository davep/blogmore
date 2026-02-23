"""Unit tests for the fontawesome module."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from blogmore.fontawesome import (
    FONTAWESOME_CDN_BRANDS_WOFF2_URL,
    FONTAWESOME_CDN_CSS_URL,
    FONTAWESOME_CDN_WEBFONTS_BASE,
    FONTAWESOME_LOCAL_CSS_PATH,
    FONTAWESOME_METADATA_URL,
    FontAwesomeOptimizer,
)


# Minimal stub metadata for use across tests
STUB_METADATA: dict[str, Any] = {
    "github": {"unicode": "f09b", "styles": ["brands"]},
    "mastodon": {"unicode": "e438", "styles": ["brands"]},
    "twitter": {"unicode": "f099", "styles": ["brands"]},
}


class TestFontAwesomeConstants:
    """Test that module-level constants have the expected values."""

    def test_cdn_css_url_contains_version(self) -> None:
        """Test that the CDN CSS URL references version 6.5.1."""
        assert "6.5.1" in FONTAWESOME_CDN_CSS_URL

    def test_cdn_css_url_is_https(self) -> None:
        """Test that the CDN CSS URL uses HTTPS."""
        assert FONTAWESOME_CDN_CSS_URL.startswith("https://")

    def test_cdn_webfonts_base_contains_version(self) -> None:
        """Test that the CDN webfonts base URL references version 6.5.1."""
        assert "6.5.1" in FONTAWESOME_CDN_WEBFONTS_BASE

    def test_metadata_url_contains_version(self) -> None:
        """Test that the metadata URL references version 6.5.1."""
        assert "6.5.1" in FONTAWESOME_METADATA_URL

    def test_local_css_path_under_static(self) -> None:
        """Test that the local CSS path is under /static/."""
        assert FONTAWESOME_LOCAL_CSS_PATH.startswith("/static/")

    def test_cdn_brands_woff2_url_derived_from_webfonts_base(self) -> None:
        """Test that the brands WOFF2 URL is derived from the webfonts base URL."""
        assert FONTAWESOME_CDN_BRANDS_WOFF2_URL.startswith(FONTAWESOME_CDN_WEBFONTS_BASE)
        assert FONTAWESOME_CDN_BRANDS_WOFF2_URL.endswith(".woff2")


class TestFontAwesomeOptimizerInit:
    """Test FontAwesomeOptimizer initialisation."""

    def test_stores_icon_names(self) -> None:
        """Test that icon names are stored on the instance."""
        optimizer = FontAwesomeOptimizer(["github", "mastodon"])
        assert optimizer.icon_names == ["github", "mastodon"]

    def test_empty_icon_names(self) -> None:
        """Test that empty icon names list is accepted."""
        optimizer = FontAwesomeOptimizer([])
        assert optimizer.icon_names == []


class TestFontAwesomeOptimizerBuildCss:
    """Test FontAwesomeOptimizer.build_css."""

    def test_contains_font_face(self) -> None:
        """Test that the generated CSS contains an @font-face rule."""
        optimizer = FontAwesomeOptimizer(["github"])
        css = optimizer.build_css(STUB_METADATA)
        assert "@font-face" in css

    def test_font_family_name(self) -> None:
        """Test that the Font Awesome 6 Brands font family is declared."""
        optimizer = FontAwesomeOptimizer(["github"])
        css = optimizer.build_css(STUB_METADATA)
        assert "Font Awesome 6 Brands" in css

    def test_woff2_url_in_font_face(self) -> None:
        """Test that the woff2 font URL points to the CDN."""
        optimizer = FontAwesomeOptimizer(["github"])
        css = optimizer.build_css(STUB_METADATA)
        assert "fa-brands-400.woff2" in css
        assert FONTAWESOME_CDN_WEBFONTS_BASE in css

    def test_ttf_url_in_font_face(self) -> None:
        """Test that the ttf font URL points to the CDN."""
        optimizer = FontAwesomeOptimizer(["github"])
        css = optimizer.build_css(STUB_METADATA)
        assert "fa-brands-400.ttf" in css

    def test_fab_class_present(self) -> None:
        """Test that the .fa-brands and .fab class rules are present."""
        optimizer = FontAwesomeOptimizer(["github"])
        css = optimizer.build_css(STUB_METADATA)
        assert ".fa-brands" in css
        assert ".fab" in css

    def test_known_icon_definition_included(self) -> None:
        """Test that a requested icon with a known codepoint is included."""
        optimizer = FontAwesomeOptimizer(["github"])
        css = optimizer.build_css(STUB_METADATA)
        assert ".fa-github::before" in css
        assert "\\f09b" in css

    def test_unrequested_icon_excluded(self) -> None:
        """Test that icons not in the requested list are not included."""
        optimizer = FontAwesomeOptimizer(["github"])
        css = optimizer.build_css(STUB_METADATA)
        assert ".fa-mastodon::before" not in css

    def test_multiple_icons_included(self) -> None:
        """Test that all requested icons are included."""
        optimizer = FontAwesomeOptimizer(["github", "mastodon"])
        css = optimizer.build_css(STUB_METADATA)
        assert ".fa-github::before" in css
        assert ".fa-mastodon::before" in css

    def test_unknown_icon_skipped(self) -> None:
        """Test that an icon name not present in metadata is silently skipped."""
        optimizer = FontAwesomeOptimizer(["unknown-icon"])
        css = optimizer.build_css(STUB_METADATA)
        assert ".fa-unknown-icon::before" not in css

    def test_icon_with_missing_unicode_skipped(self) -> None:
        """Test that an icon entry without a unicode field is skipped."""
        metadata = {"no-unicode": {"styles": ["brands"]}}
        optimizer = FontAwesomeOptimizer(["no-unicode"])
        css = optimizer.build_css(metadata)
        assert ".fa-no-unicode::before" not in css

    def test_empty_icon_list_produces_valid_css(self) -> None:
        """Test that an empty icon list produces CSS with only base rules."""
        optimizer = FontAwesomeOptimizer([])
        css = optimizer.build_css(STUB_METADATA)
        assert "@font-face" in css
        assert ".fa-brands" in css
        assert "::before" not in css

    def test_font_display_swap(self) -> None:
        """Test that font-display is set to swap for non-blocking font loading."""
        optimizer = FontAwesomeOptimizer(["github"])
        css = optimizer.build_css(STUB_METADATA)
        assert "font-display: swap;" in css

    def test_css_ends_with_newline(self) -> None:
        """Test that the generated CSS ends with a newline."""
        optimizer = FontAwesomeOptimizer(["github"])
        css = optimizer.build_css(STUB_METADATA)
        assert css.endswith("\n")


class TestFontAwesomeOptimizerFetchIconMetadata:
    """Test FontAwesomeOptimizer.fetch_icon_metadata."""

    def test_fetch_returns_dict_on_success(self) -> None:
        """Test that fetch_icon_metadata returns a dict when the request succeeds."""
        import json

        mock_response_data = json.dumps(STUB_METADATA).encode("utf-8")
        mock_response = MagicMock()
        mock_response.read.return_value = mock_response_data
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_response
        mock_cm.__exit__.return_value = False

        with patch("urllib.request.urlopen", return_value=mock_cm):
            optimizer = FontAwesomeOptimizer(["github"])
            result = optimizer.fetch_icon_metadata()

        assert isinstance(result, dict)
        assert "github" in result

    def test_fetch_raises_on_network_error(self) -> None:
        """Test that fetch_icon_metadata propagates URL errors."""
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("network error"),
        ):
            optimizer = FontAwesomeOptimizer(["github"])
            with pytest.raises(urllib.error.URLError):
                optimizer.fetch_icon_metadata()


class TestFontAwesomeOptimizerGenerate:
    """Test FontAwesomeOptimizer.generate."""

    def test_generate_writes_css_file_on_success(self, tmp_path: Path) -> None:
        """Test that generate() writes fontawesome.css into output/static/."""
        optimizer = FontAwesomeOptimizer(["github"])

        with patch.object(optimizer, "fetch_icon_metadata", return_value=STUB_METADATA):
            success = optimizer.generate(tmp_path)

        assert success is True
        css_file = tmp_path / "static" / "fontawesome.css"
        assert css_file.exists()
        content = css_file.read_text()
        assert ".fa-github::before" in content

    def test_generate_creates_static_dir(self, tmp_path: Path) -> None:
        """Test that generate() creates the static directory if it does not exist."""
        optimizer = FontAwesomeOptimizer(["github"])

        with patch.object(optimizer, "fetch_icon_metadata", return_value=STUB_METADATA):
            optimizer.generate(tmp_path)

        assert (tmp_path / "static").is_dir()

    def test_generate_returns_false_on_network_failure(self, tmp_path: Path) -> None:
        """Test that generate() returns False when metadata fetch fails."""
        import urllib.error

        optimizer = FontAwesomeOptimizer(["github"])

        with patch.object(
            optimizer,
            "fetch_icon_metadata",
            side_effect=urllib.error.URLError("unreachable"),
        ):
            success = optimizer.generate(tmp_path)

        assert success is False
        # No CSS file should have been written
        assert not (tmp_path / "static" / "fontawesome.css").exists()

    def test_generate_returns_false_on_os_error(self, tmp_path: Path) -> None:
        """Test that generate() returns False when an OSError occurs during fetch."""
        optimizer = FontAwesomeOptimizer(["github"])

        with patch.object(
            optimizer,
            "fetch_icon_metadata",
            side_effect=OSError("connection reset"),
        ):
            success = optimizer.generate(tmp_path)

        assert success is False


class TestFontAwesomeOptimizerInGenerator:
    """Test that SiteGenerator integrates FontAwesomeOptimizer correctly."""

    def test_no_socials_produces_no_fontawesome_css_url(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that no fontawesome CSS URL is set when no socials are configured."""
        from blogmore.generator import SiteGenerator

        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            sidebar_config={},
        )

        with patch("blogmore.generator.FontAwesomeOptimizer") as mock_cls:
            generator.generate(include_drafts=False)

        # Optimizer should not have been constructed at all
        mock_cls.assert_not_called()
        # No fontawesome.css should exist
        assert not (temp_output_dir / "static" / "fontawesome.css").exists()
        # HTML should not reference any fontawesome CSS
        index_html = (temp_output_dir / "index.html").read_text()
        assert "fontawesome" not in index_html.lower()

    def test_socials_optimizes_css_on_successful_fetch(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that fontawesome.css is generated when socials are configured."""
        from blogmore.generator import SiteGenerator

        sidebar_config = {
            "socials": [
                {"site": "github", "url": "https://github.com/example"},
                {"site": "mastodon", "url": "https://fosstodon.org/@example"},
            ]
        }
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            sidebar_config=sidebar_config,
        )

        with patch.object(
            FontAwesomeOptimizer,
            "fetch_icon_metadata",
            return_value=STUB_METADATA,
        ):
            generator.generate(include_drafts=False)

        # Optimised CSS file must exist
        css_file = temp_output_dir / "static" / "fontawesome.css"
        assert css_file.exists()
        css_content = css_file.read_text()
        assert ".fa-github::before" in css_content
        assert ".fa-mastodon::before" in css_content

        # HTML should reference the local CSS path
        index_html = (temp_output_dir / "index.html").read_text()
        assert FONTAWESOME_LOCAL_CSS_PATH in index_html

    def test_socials_includes_woff2_preload_hint(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that a preload link for the WOFF2 font is present when socials are configured."""
        from blogmore.generator import SiteGenerator

        sidebar_config = {
            "socials": [{"site": "github", "url": "https://github.com/example"}]
        }
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            sidebar_config=sidebar_config,
        )

        with patch.object(
            FontAwesomeOptimizer,
            "fetch_icon_metadata",
            return_value=STUB_METADATA,
        ):
            generator.generate(include_drafts=False)

        index_html = (temp_output_dir / "index.html").read_text()
        expected_preload = (
            f'<link rel="preload" href="{FONTAWESOME_CDN_BRANDS_WOFF2_URL}"'
            ' as="font" type="font/woff2" crossorigin="anonymous">'
        )
        assert expected_preload in index_html

    def test_socials_falls_back_to_cdn_on_fetch_failure(
        self, posts_dir: Path, temp_output_dir: Path
    ) -> None:
        """Test that CDN URL is used when metadata fetch fails."""
        import urllib.error

        from blogmore.generator import SiteGenerator

        sidebar_config = {
            "socials": [{"site": "github", "url": "https://github.com/example"}]
        }
        generator = SiteGenerator(
            content_dir=posts_dir,
            templates_dir=None,
            output_dir=temp_output_dir,
            sidebar_config=sidebar_config,
        )

        with patch.object(
            FontAwesomeOptimizer,
            "fetch_icon_metadata",
            side_effect=urllib.error.URLError("unreachable"),
        ):
            generator.generate(include_drafts=False)

        # No local CSS file should be created
        assert not (temp_output_dir / "static" / "fontawesome.css").exists()

        # HTML should reference the full CDN URL
        index_html = (temp_output_dir / "index.html").read_text()
        assert FONTAWESOME_CDN_CSS_URL in index_html
