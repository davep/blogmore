"""Platform-specific user and blog cache path resolution for blogmore."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path


def get_user_cache_dir() -> Path:
    """Return the platform-specific user cache directory for blogmore.

    On Windows, this uses `%LOCALAPPDATA%`. On all other platforms (Unix/macOS),
    it follows the XDG Base Directory Specification (`~/.cache`).

    Returns:
        A Path object pointing to the user's cache directory for blogmore.
    """
    if sys.platform == "win32":
        # Windows: %LOCALAPPDATA%\blogmore\cache
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "blogmore" / "cache"

    # Unix-like (Linux, macOS, etc.): ~/.cache/blogmore or $XDG_CACHE_HOME/blogmore
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "blogmore"


def get_blog_cache_dir(content_dir: Path) -> Path:
    """Return a unique cache directory for a specific blog.

    The directory is unique to the absolute path of the blog's content directory,
    allowing multiple blogs to be managed on the same system without cache
    collisions.

    Args:
        content_dir: The blog's content directory.

    Returns:
        A Path object pointing to the blog-specific cache directory.
    """
    # Create a unique hash for the absolute path of the content directory
    path_hash = hashlib.sha256(str(content_dir.resolve()).encode("utf-8")).hexdigest()
    return get_user_cache_dir() / "blogs" / path_hash
