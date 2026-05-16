"""Image optimization and resizing manager."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image

if TYPE_CHECKING:
    from blogmore.site_config import SiteConfig


@dataclass
class OptimizedImage:
    """Metadata for an optimized image ladder."""

    source_path: Path
    original_width: int
    original_height: int
    hash: str
    # Maps width to relative output path (standard format)
    resized_paths: dict[int, str] = field(default_factory=dict)
    # Maps width to relative output path (WebP format)
    webp_paths: dict[int, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for JSON serialization."""
        return {
            "source_path": str(self.source_path),
            "original_width": self.original_width,
            "original_height": self.original_height,
            "hash": self.hash,
            "resized_paths": {str(w): p for w, p in self.resized_paths.items()},
            "webp_paths": {str(w): p for w, p in self.webp_paths.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OptimizedImage:
        """Create an instance from a dictionary."""
        return cls(
            source_path=Path(data["source_path"]),
            original_width=data["original_width"],
            original_height=data["original_height"],
            hash=data["hash"],
            resized_paths={int(w): p for w, p in data["resized_paths"].items()},
            webp_paths={int(w): p for w, p in data["webp_paths"].items()},
        )


class ImageManager:
    """Manages image resizing, optimization, and caching."""

    MANIFEST_FILENAME = "manifest.json"

    def __init__(self, site_config: SiteConfig, cache_dir: Path) -> None:
        """Initialize the image manager.

        Args:
            site_config: The site configuration.
            cache_dir: The directory to store cached images and manifest.
        """
        self.site_config = site_config
        self.cache_dir = cache_dir
        self.cache_images_dir = cache_dir / "files"
        self.manifest_path = cache_dir / self.MANIFEST_FILENAME

        # Maps source path string to OptimizedImage
        self.manifest: dict[str, OptimizedImage] = {}
        self._load_manifest()

    def _load_manifest(self) -> None:
        """Load the manifest from disk if it exists."""
        if self.manifest_path.is_file():
            try:
                with open(self.manifest_path) as f:
                    data = json.load(f)
                    for path_str, entry_data in data.items():
                        self.manifest[path_str] = OptimizedImage.from_dict(entry_data)
            except Exception as e:
                print(f"Warning: Failed to load image manifest: {e}")
                self.manifest = {}

    def _save_manifest(self) -> None:
        """Save the manifest to disk."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        data = {path: entry.to_dict() for path, entry in self.manifest.items()}
        with open(self.manifest_path, "w") as f:
            json.dump(data, f, indent=2)

    def _get_file_hash(self, path: Path) -> str:
        """Calculate the SHA-256 hash of a file.

        Args:
            path: Path to the file.

        Returns:
            The hex digest of the file hash.
        """
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_optimized_image(self, source_path: Path) -> OptimizedImage | None:
        """Get or create optimized versions of an image.

        Args:
            source_path: Path to the source image.

        Returns:
            An OptimizedImage object if successful, None otherwise.
        """
        if not source_path.is_file():
            return None

        # Check for unsupported formats
        suffix = source_path.suffix.lower()
        if suffix in (".svg", ".gif"):
            return None

        file_hash = self._get_file_hash(source_path)
        source_key = str(source_path.resolve())

        # Check manifest
        if source_key in self.manifest:
            entry = self.manifest[source_key]
            if entry.hash == file_hash:
                return entry

        # Not in manifest or hash changed: process it
        try:
            with Image.open(source_path) as img:
                orig_w, orig_h = img.size

                entry = OptimizedImage(
                    source_path=source_path,
                    original_width=orig_w,
                    original_height=orig_h,
                    hash=file_hash,
                )

                # Process ladder
                self.cache_images_dir.mkdir(parents=True, exist_ok=True)

                # We'll use the hash in the filename to avoid collisions
                base_name = f"{source_path.stem}_{file_hash[:8]}"

                for width in self.site_config.image_widths:
                    if width >= orig_w:
                        continue

                    # Calculate new height preserving aspect ratio
                    height = int(orig_h * (width / orig_w))

                    # Target filenames
                    # Fallback "standard" format is JPEG unless it's a PNG source
                    std_ext = ".png" if suffix == ".png" else ".jpg"
                    std_name = f"{base_name}-{width}{std_ext}"
                    webp_name = f"{base_name}-{width}.webp"

                    std_path = self.cache_images_dir / std_name
                    webp_path = self.cache_images_dir / webp_name

                    # Resize and save if not already in cache
                    if not std_path.exists() or not webp_path.exists():
                        resized = img.resize((width, height), Image.Resampling.LANCZOS)

                        # Save standard fallback
                        save_kwargs: dict[str, Any] = {
                            "quality": self.site_config.image_quality
                        }
                        if std_ext == ".jpg":
                            save_kwargs["optimize"] = True
                            # JPEG does not support RGBA; flatten to RGB on white background
                            if resized.mode in ("RGBA", "P"):
                                background = Image.new(
                                    "RGB", resized.size, (255, 255, 255)
                                )
                                # Handle palette images with transparency
                                resized_rgb = (
                                    resized.convert("RGBA")
                                    if resized.mode == "P"
                                    else resized
                                )
                                background.paste(
                                    resized_rgb, mask=resized_rgb.split()[3]
                                )

                                background.save(std_path, **save_kwargs)
                            else:
                                resized.save(std_path, **save_kwargs)
                        else:
                            # PNG or other
                            resized.save(std_path)

                        # Save WebP (native support for transparency)
                        resized.save(
                            webp_path,
                            format="WEBP",
                            quality=self.site_config.image_quality,
                        )

                    entry.resized_paths[width] = std_name
                    entry.webp_paths[width] = webp_name

                self.manifest[source_key] = entry
                self._save_manifest()
                return entry

        except Exception as e:
            print(f"Warning: Failed to optimize image {source_path}: {e}")
            return None

    def deploy_optimized_images(self, output_dir: Path) -> None:
        """Copy all cached optimized images to the site output directory.

        Args:
            output_dir: The site output directory (e.g. output/static/images/optimized/).
        """
        if not self.cache_images_dir.exists():
            return

        output_dir.mkdir(parents=True, exist_ok=True)
        for entry in self.manifest.values():
            for filename in list(entry.resized_paths.values()) + list(
                entry.webp_paths.values()
            ):
                src = self.cache_images_dir / filename
                dst = output_dir / filename
                if src.exists():
                    shutil.copy2(src, dst)
