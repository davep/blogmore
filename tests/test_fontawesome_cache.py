"""Unit tests for FontAwesome metadata caching."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from blogmore.fontawesome import FONTAWESOME_METADATA_URL, FontAwesomeOptimizer

STUB_METADATA = {"github": {"unicode": "f09b"}}


class TestFontAwesomeCaching:
    """Test the caching logic in FontAwesomeOptimizer.fetch_icon_metadata."""

    @pytest.fixture
    def mock_cache_dir(self, tmp_path):
        """Mock the cache directory using a temporary path."""
        with patch("blogmore.fontawesome.get_user_cache_dir", return_value=tmp_path):
            yield tmp_path

    def test_fetch_uses_cache_when_available(self, mock_cache_dir):
        """Test that metadata is loaded from cache if the file exists."""
        cache_file = mock_cache_dir / "fa-metadata-6.5.1.json"
        cache_file.write_text(json.dumps(STUB_METADATA))

        optimizer = FontAwesomeOptimizer(["github"])

        # Patch urlopen to ensure it's NOT called
        with patch("urllib.request.urlopen") as mock_urlopen:
            metadata = optimizer.fetch_icon_metadata()
            mock_urlopen.assert_not_called()

        assert metadata == STUB_METADATA

    def test_fetch_updates_cache_on_miss(self, mock_cache_dir):
        """Test that metadata is fetched and saved to cache on a miss."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(STUB_METADATA).encode("utf-8")
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_response

        optimizer = FontAwesomeOptimizer(["github"])

        with patch("urllib.request.urlopen", return_value=mock_cm) as mock_urlopen:
            metadata = optimizer.fetch_icon_metadata()
            mock_urlopen.assert_called_once_with(FONTAWESOME_METADATA_URL)

        assert metadata == STUB_METADATA

        # Verify cache file was created
        cache_file = mock_cache_dir / "fa-metadata-6.5.1.json"
        assert cache_file.exists()
        assert json.loads(cache_file.read_text()) == STUB_METADATA

    def test_fetch_falls_back_on_corrupt_cache(self, mock_cache_dir):
        """Test that corrupt cache is ignored and metadata is re-fetched."""
        cache_file = mock_cache_dir / "fa-metadata-6.5.1.json"
        cache_file.write_text("invalid json")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(STUB_METADATA).encode("utf-8")
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_response

        optimizer = FontAwesomeOptimizer(["github"])

        with patch("urllib.request.urlopen", return_value=mock_cm) as mock_urlopen:
            metadata = optimizer.fetch_icon_metadata()
            mock_urlopen.assert_called_once()

        assert metadata == STUB_METADATA
        # Cache should have been updated with valid data
        assert json.loads(cache_file.read_text()) == STUB_METADATA

    def test_fetch_works_if_cache_cannot_be_written(self, tmp_path):
        """Test that fetch succeeds even if the cache directory is read-only."""
        # Create a read-only directory
        cache_dir = tmp_path / "readonly_cache"
        cache_dir.mkdir()
        # On some systems, making it read-only might not prevent file creation
        # depending on parent permissions, but we can mock mkdir to fail.

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(STUB_METADATA).encode("utf-8")
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_response

        with patch("blogmore.fontawesome.get_user_cache_dir", return_value=cache_dir):
            # Mock mkdir to simulate permission error
            with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
                optimizer = FontAwesomeOptimizer(["github"])
                with patch("urllib.request.urlopen", return_value=mock_cm):
                    metadata = optimizer.fetch_icon_metadata()

        assert metadata == STUB_METADATA
        # No cache file should have been created (or at least we didn't crash)
