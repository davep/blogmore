"""Unit tests for the cache module."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from blogmore.cache import get_blog_cache_dir, get_user_cache_dir


class TestCache:
    """Test cache path resolution functions."""

    def test_get_user_cache_dir_unix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test user cache directory resolution on Unix-like systems.

        Args:
            monkeypatch: The pytest monkeypatch fixture.
        """
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("XDG_CACHE_HOME", "/custom/cache/dir")

        path = get_user_cache_dir()
        assert path == Path("/custom/cache/dir/blogmore")

    def test_get_user_cache_dir_unix_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test default user cache directory resolution on Unix-like systems when XDG_CACHE_HOME is unset.

        Args:
            monkeypatch: The pytest monkeypatch fixture.
        """
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)

        home_path = Path("/home/testuser")
        with patch.object(Path, "home", return_value=home_path):
            path = get_user_cache_dir()
            assert path == Path("/home/testuser/.cache/blogmore")

    def test_get_user_cache_dir_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test user cache directory resolution on Windows.

        Args:
            monkeypatch: The pytest monkeypatch fixture.
        """
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("LOCALAPPDATA", "C:/Users/testuser/AppData/Local")

        path = get_user_cache_dir()
        assert path == Path("C:/Users/testuser/AppData/Local/blogmore/cache")

    def test_get_user_cache_dir_windows_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test default user cache directory resolution on Windows when LOCALAPPDATA is unset.

        Args:
            monkeypatch: The pytest monkeypatch fixture.
        """
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.delenv("LOCALAPPDATA", raising=False)

        home_path = Path("C:/Users/testuser")
        with patch.object(Path, "home", return_value=home_path):
            path = get_user_cache_dir()
            assert path == Path("C:/Users/testuser/AppData/Local/blogmore/cache")

    def test_get_blog_cache_dir(self, tmp_path: Path) -> None:
        """Test blog-specific cache directory generation based on content path.

        Args:
            tmp_path: The pytest temp path fixture.
        """
        # Since conftest.py mocks get_user_cache_dir automatically, this will resolve under tmp_path
        blog_dir = tmp_path / "my_blog"

        cache_dir_1 = get_blog_cache_dir(blog_dir)
        cache_dir_2 = get_blog_cache_dir(blog_dir)

        # Must be identical for same input path
        assert cache_dir_1 == cache_dir_2

        # Must be different for different input paths
        other_blog_dir = tmp_path / "other_blog"
        cache_dir_other = get_blog_cache_dir(other_blog_dir)
        assert cache_dir_1 != cache_dir_other
