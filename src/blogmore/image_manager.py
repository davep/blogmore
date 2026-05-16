"""Image optimisation and resizing manager."""

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
class OptimisedImage:
    """Metadata for an optimised image ladder."""

    source_path: Path
    original_width: int
    original_height: int
    hash: str
    quality: int
    widths: list[int]
    jpeg_fallback: bool
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
            "quality": self.quality,
            "widths": self.widths,
            "jpeg_fallback": self.jpeg_fallback,
            "resized_paths": {str(w): p for w, p in self.resized_paths.items()},
            "webp_paths": {str(w): p for w, p in self.webp_paths.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OptimisedImage:
        """Create an instance from a dictionary."""
        return cls(
            source_path=Path(data["source_path"]),
            original_width=data["original_width"],
            original_height=data["original_height"],
            hash=data["hash"],
            quality=data.get("quality", 85),
            widths=data.get("widths", []),
            jpeg_fallback=data.get("jpeg_fallback", True),
            resized_paths={int(w): p for w, p in data["resized_paths"].items()},
            webp_paths={int(w): p for w, p in data["webp_paths"].items()},
        )


class ImageManager:
    """Manages image resizing, optimisation, and caching."""

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

        # Maps source path string to OptimisedImage
        self.manifest: dict[str, OptimisedImage] = {}
        self._load_manifest()

        # Set of source paths that need to be processed in this build pass
        self._processing_queue: set[Path] = set()

    def _load_manifest(self) -> None:
        """Load the manifest from disk if it exists."""
        if self.manifest_path.is_file():
            try:
                with open(self.manifest_path) as f:
                    data = json.load(f)
                    for path_str, entry_data in data.items():
                        self.manifest[path_str] = OptimisedImage.from_dict(entry_data)
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

    def get_optimised_image(self, source_path: Path) -> OptimisedImage | None:
        """Register an image for optimisation and return its metadata.

        Note: This does NOT perform the actual resizing/optimisation yet.
        Call `process_all()` to execute the processing.

        Args:
            source_path: Path to the source image.

        Returns:
            An OptimisedImage object if successful, None otherwise.
        """
        if not source_path.is_file():
            return None

        # Check for unsupported formats
        suffix = source_path.suffix.lower()
        if suffix in (".svg", ".gif"):
            return None

        file_hash = self._get_file_hash(source_path)
        source_key = str(source_path.resolve())

        # Check if we already have a valid manifest entry
        if source_key in self.manifest:
            entry = self.manifest[source_key]
            if (
                entry.hash == file_hash
                and entry.quality == self.site_config.image_quality
                and entry.widths == self.site_config.image_widths
                and entry.jpeg_fallback == self.site_config.image_jpeg_fallback
            ):
                # Up to date, but we still need to ensure the physical files
                # exist in the cache. If they were deleted, re-queue.
                all_exist = True
                for filename in list(entry.resized_paths.values()) + list(
                    entry.webp_paths.values()
                ):
                    if not (self.cache_images_dir / filename).exists():
                        all_exist = False
                        break

                if all_exist:
                    return entry

        # Not in manifest, hash changed, parameters changed, or cache missing
        try:
            with Image.open(source_path) as img:
                orig_w, orig_h = img.size

                # Create a placeholder entry with target metadata
                entry = OptimisedImage(
                    source_path=source_path,
                    original_width=orig_w,
                    original_height=orig_h,
                    hash=file_hash,
                    quality=self.site_config.image_quality,
                    widths=self.site_config.image_widths,
                    jpeg_fallback=self.site_config.image_jpeg_fallback,
                )

                # Predict target filenames
                base_name = f"{source_path.stem}_{file_hash[:8]}"
                std_ext = ".png" if suffix == ".png" else ".jpg"

                for width in self.site_config.image_widths:
                    if width >= orig_w:
                        continue
                    if self.site_config.image_jpeg_fallback:
                        entry.resized_paths[width] = f"{base_name}-{width}{std_ext}"
                    entry.webp_paths[width] = f"{base_name}-{width}.webp"

                # Store in manifest and add to queue
                self.manifest[source_key] = entry
                self._processing_queue.add(source_path)
                return entry

        except Exception as e:
            print(f"Warning: Failed to register image {source_path}: {e}")
            return None

    def process_all(self) -> None:
        """Perform resizing and optimisation for all registered images in the queue."""
        if not self._processing_queue:
            return

        self.cache_images_dir.mkdir(parents=True, exist_ok=True)
        processed_count = 0

        for source_path in sorted(self._processing_queue):
            source_key = str(source_path.resolve())
            entry = self.manifest.get(source_key)
            if not entry:
                continue

            try:
                with Image.open(source_path) as img:
                    orig_w, orig_h = img.size

                    all_widths = sorted(
                        set(entry.resized_paths.keys()) | set(entry.webp_paths.keys())
                    )
                    for width in all_widths:
                        std_name = entry.resized_paths.get(width)
                        webp_name = entry.webp_paths.get(width)

                        std_path = (
                            self.cache_images_dir / std_name if std_name else None
                        )
                        webp_path = (
                            self.cache_images_dir / webp_name if webp_name else None
                        )

                        # If the file exists, we still overwrite it because being in the
                        # processing queue means either the source changed OR the settings
                        # (quality/widths) changed, so we want fresh files.

                        # Calculate new height preserving aspect ratio
                        height = int(orig_h * (width / orig_w))
                        resized = img.resize((width, height), Image.Resampling.LANCZOS)

                        # Save standard fallback
                        if std_name and std_path:
                            save_kwargs: dict[str, Any] = {
                                "quality": self.site_config.image_quality
                            }
                            if std_name.endswith(".jpg"):
                                save_kwargs["optimize"] = True
                                if resized.mode in ("RGBA", "P"):
                                    background = Image.new(
                                        "RGB", resized.size, (255, 255, 255)
                                    )
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
                                resized.save(std_path)

                        # Save WebP
                        if webp_name and webp_path:
                            resized.save(
                                webp_path,
                                format="WEBP",
                                quality=self.site_config.image_quality,
                            )

                processed_count += 1

            except Exception as e:
                print(f"Warning: Failed to optimise image {source_path}: {e}")

        if processed_count > 0:
            self._save_manifest()
            self._processing_queue.clear()

    def deploy_optimised_images(self, output_dir: Path) -> None:
        """Copy all cached optimised images to the site output directory.

        Args:
            output_dir: The site output directory (e.g. output/static/images/optimised/).
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
