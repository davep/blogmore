"""Image optimisation and resizing manager."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from PIL import Image

if TYPE_CHECKING:
    from blogmore.site_config import SiteConfig


@dataclass
class OptimisedImage:
    """Metadata for an optimised image ladder."""

    source_path: Path
    """Path to the source image file."""
    original_width: int
    """Width of the original image in pixels."""
    original_height: int
    """Height of the original image in pixels."""
    hash: str
    """SHA-256 hash of the original image file."""
    quality: int
    """Quality setting used for optimisation."""
    widths: list[int]
    """List of widths generated for this image."""
    make_source_fallback: bool
    """Whether a standard fallback format was generated."""
    original_is_webp: bool = False
    """True if the original source file can be used as a WebP version."""
    original_is_standard: bool = False
    """True if the original source file can be used as a standard version."""
    resized_paths: dict[int, str] = field(default_factory=dict)
    """Maps width to relative output path for the standard format."""
    webp_paths: dict[int, str] = field(default_factory=dict)
    """Maps width to relative output path for the WebP format."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for JSON serialization."""
        data = asdict(self)
        data["source_path"] = str(self.source_path)
        # JSON keys must be strings
        data["resized_paths"] = {str(k): v for k, v in self.resized_paths.items()}
        data["webp_paths"] = {str(k): v for k, v in self.webp_paths.items()}
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create an instance from a dictionary."""
        # Convert string paths and keys back to their types
        data["source_path"] = Path(data["source_path"])
        if "resized_paths" in data:
            data["resized_paths"] = {
                int(k): v for k, v in data["resized_paths"].items()
            }
        if "webp_paths" in data:
            data["webp_paths"] = {int(k): v for k, v in data["webp_paths"].items()}
        return cls(**data)


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
                with open(self.manifest_path) as manifest_file:
                    data = json.load(manifest_file)
                    for path_str, entry_data in data.items():
                        self.manifest[path_str] = OptimisedImage.from_dict(entry_data)
            except Exception as error:
                print(f"Warning: Failed to load image manifest: {error}")
                self.manifest = {}

    def _save_manifest(self) -> None:
        """Save the manifest to disk."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        data = {path: entry.to_dict() for path, entry in self.manifest.items()}
        with open(self.manifest_path, "w") as manifest_file:
            json.dump(data, manifest_file, indent=2)

    def _get_file_hash(self, path: Path) -> str:
        """Calculate the SHA-256 hash of a file.

        Args:
            path: Path to the file.

        Returns:
            The hex digest of the file hash.
        """
        with open(path, "rb") as source_file:
            return hashlib.file_digest(source_file, "sha256").hexdigest()

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

        # Determine target widths: all buckets smaller than the original,
        # plus the original width itself if it's within the range of our buckets.
        # This ensures that an image like 753px doesn't get capped at 400px
        # if the next bucket is 800px.
        try:
            with Image.open(source_path) as image:
                original_width, original_height = image.size
        except Exception as error:
            print(
                f"Warning: Failed to open image {source_path} to determine size: {error}"
            )
            return None

        target_widths = {
            width for width in self.site_config.image_widths if width < original_width
        }
        if self.site_config.image_widths and original_width <= max(
            self.site_config.image_widths
        ):
            target_widths.add(original_width)

        sorted_target_widths = sorted(target_widths)

        # Check if we already have a valid manifest entry
        if source_key in self.manifest:
            entry = self.manifest[source_key]
            if (
                entry.hash == file_hash
                and entry.quality == self.site_config.image_quality
                and entry.widths == sorted_target_widths
                and entry.make_source_fallback
                == self.site_config.image_make_source_fallback
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
            # Predict target filenames
            base_name = f"{source_path.stem}_{file_hash[:8]}"
            standard_extension = (
                suffix if suffix in (".png", ".jpg", ".jpeg") else ".jpg"
            )

            # Determine if the original image can satisfy our needs for the
            # original resolution version.
            original_is_webp = suffix == ".webp"
            if standard_extension in (".jpg", ".jpeg"):
                original_is_standard = suffix in (".jpg", ".jpeg")
            else:
                original_is_standard = suffix == standard_extension

            # Create a placeholder entry with target metadata
            entry = OptimisedImage(
                source_path=source_path,
                original_width=original_width,
                original_height=original_height,
                hash=file_hash,
                quality=self.site_config.image_quality,
                widths=sorted_target_widths,
                make_source_fallback=self.site_config.image_make_source_fallback,
                original_is_webp=original_is_webp,
                original_is_standard=original_is_standard,
            )

            for width in sorted_target_widths:
                if self.site_config.image_make_source_fallback:
                    # Register a standard format resized version if the original doesn't match the requirements
                    if not (width == original_width and original_is_standard):
                        entry.resized_paths[width] = (
                            f"{base_name}-{width}{standard_extension}"
                        )

                # Register a WebP version if the original isn't already a usable WebP file at this width
                if not (width == original_width and original_is_webp):
                    entry.webp_paths[width] = f"{base_name}-{width}.webp"

            # Store in manifest and add to queue
            self.manifest[source_key] = entry
            self._processing_queue.add(source_path)
            return entry

        except Exception as error:
            print(f"Warning: Failed to register image {source_path}: {error}")
            return None

    def _save_standard_image(self, image: Image.Image, path: Path) -> None:
        """Save an image in a standard format (JPG/PNG), handling transparency for JPG.

        Args:
            image: The image object to save.
            path: Target file path.
        """
        save_kwargs: dict[str, Any] = {"quality": self.site_config.image_quality}
        if path.suffix.lower() in (".jpg", ".jpeg"):
            save_kwargs["optimize"] = True
            if image.mode in ("RGBA", "P"):
                # Paste onto a white background to handle transparency
                background = Image.new("RGB", image.size, (255, 255, 255))
                # If mode is P, we need to convert to RGBA first to get the alpha mask
                image_rgba = image.convert("RGBA") if image.mode == "P" else image
                background.paste(image_rgba, mask=image_rgba.split()[3])
                background.save(path, **save_kwargs)
            else:
                image.save(path, **save_kwargs)
        else:
            image.save(path)

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
                with Image.open(source_path) as image:
                    original_width, original_height = image.size

                    all_widths = sorted(
                        set(entry.resized_paths.keys()) | set(entry.webp_paths.keys())
                    )
                    for width in all_widths:
                        standard_name = entry.resized_paths.get(width)
                        webp_name = entry.webp_paths.get(width)

                        standard_path = (
                            self.cache_images_dir / standard_name
                            if standard_name
                            else None
                        )
                        webp_path = (
                            self.cache_images_dir / webp_name if webp_name else None
                        )

                        # If the file exists, we still overwrite it because being in the
                        # processing queue means either the source changed OR the settings
                        # (quality/widths) changed, so we want fresh files.

                        # Calculate new height preserving aspect ratio
                        resized: Image.Image
                        if width == original_width:
                            resized = image
                        else:
                            height = int(original_height * (width / original_width))
                            resized = image.resize(
                                (width, height), Image.Resampling.LANCZOS
                            )

                        # Save standard fallback
                        if standard_path:
                            self._save_standard_image(resized, standard_path)

                        # Save WebP
                        if webp_name and webp_path:
                            webp_save_kwargs: dict[str, Any] = {
                                "format": "WEBP",
                                "quality": self.site_config.image_quality,
                            }
                            # Use lossless encoding for PNG sources (better for screenshots)
                            if source_path.suffix.lower() == ".png":
                                webp_save_kwargs["lossless"] = True

                            resized.save(webp_path, **webp_save_kwargs)

                processed_count += 1

            except Exception as error:
                print(f"Warning: Failed to optimise image {source_path}: {error}")

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
                cached_file_path = self.cache_images_dir / filename
                destination_file_path = output_dir / filename
                if cached_file_path.exists():
                    shutil.copy2(cached_file_path, destination_file_path)
