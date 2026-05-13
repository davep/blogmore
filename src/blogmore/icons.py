"""Icon generation from a single source image for blogmore."""

import json
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

# PNG icon specifications: (size, filename) tuples for all platforms
PNG_ICON_SPECS: list[tuple[int, str]] = [
    # Standard favicon PNG sizes
    (16, "favicon-16x16.png"),
    (32, "favicon-32x32.png"),
    (96, "favicon-96x96.png"),
    # Apple touch icons
    (180, "apple-touch-icon.png"),
    (120, "apple-touch-icon-120.png"),
    (152, "apple-touch-icon-152.png"),
    (167, "apple-touch-icon-167.png"),
    (180, "apple-touch-icon-precomposed.png"),
    # Android/Chrome icons
    (192, "android-chrome-192x192.png"),
    (512, "android-chrome-512x512.png"),
    # Windows/Microsoft tiles
    (70, "mstile-70x70.png"),
    (144, "mstile-144x144.png"),
    (150, "mstile-150x150.png"),
    (310, "mstile-310x310.png"),
]


def detect_source_icon(
    extras_dir: Path, custom_filename: str | None = None
) -> Path | None:
    """Detect the source icon file in the extras directory.

    Args:
        extras_dir: Directory to search for the source icon
        custom_filename: Optional custom filename from configuration

    Returns:
        Path to the source icon file if found, None otherwise
    """
    if not extras_dir.exists():
        return None

    # If a custom filename is provided, check for it
    if custom_filename:
        if (custom_path := extras_dir / Path(custom_filename).name).is_file():
            return custom_path
        return None

    # Otherwise search for default candidates
    default_candidates = [
        "icon.png",
        "icon.jpg",
        "icon.jpeg",
        "source-icon.png",
        "source-icon.jpg",
        "app-icon.png",
    ]

    for candidate in default_candidates:
        if (candidate_path := extras_dir / candidate).is_file():
            return candidate_path

    return None


class IconGenerator:
    """Generate favicon and platform-specific icons from a single source image."""

    def __init__(
        self, source_image: Path, output_dir: Path, cache_dir: Path | None = None
    ) -> None:
        """Initialize the icon generator.

        Args:
            source_image: Path to the source image file
            output_dir: Directory where icons will be written (should be /icons subdirectory)
            cache_dir: Optional directory to cache generated icons (unique to the blog)
        """
        self.source_image = source_image
        self.output_dir = output_dir
        self.cache_dir = cache_dir

    def generate_all(self) -> dict[str, Path]:
        """Generate all icon formats from the source image.

        Returns:
            Dictionary mapping icon name to output path for successfully generated icons
        """
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Check cache if available
        if self.cache_dir:
            cached_icons = self._load_from_cache()
            if cached_icons:
                # Copy cached icons to output directory
                for filename, cached_path in cached_icons.items():
                    shutil.copy2(cached_path, self.output_dir / filename)
                return {
                    filename: self.output_dir / filename for filename in cached_icons
                }

        # Open and validate source image
        try:
            with Image.open(self.source_image) as source_img:
                # Convert to RGBA if needed
                img: Image.Image = source_img
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA")

                generated: dict[str, Path] = {}

                # Generate favicon.ico (multi-resolution)
                favicon_path = self._generate_favicon(img)
                if favicon_path:
                    generated["favicon.ico"] = favicon_path

                # Generate all PNG icons (favicon, Apple, Android, Windows)
                self._generate_png_icons_batch(img, PNG_ICON_SPECS, generated)

                # Generate wide Windows tile (310x150)
                wide_tile_path = self._generate_wide_tile(img)
                if wide_tile_path:
                    generated["mstile-310x150.png"] = wide_tile_path

                # Generate web manifest for Android/PWA
                manifest_path = self._generate_web_manifest()
                if manifest_path:
                    generated["site.webmanifest"] = manifest_path

                # Generate browserconfig.xml for Windows tiles
                browserconfig_path = self._generate_browserconfig()
                if browserconfig_path:
                    generated["browserconfig.xml"] = browserconfig_path

                # Save to cache if available
                if self.cache_dir:
                    self._save_to_cache(generated)

                return generated

        except Exception as e:
            print(f"Error generating icons: {e}")
            return {}

    def _load_from_cache(self) -> dict[str, Path] | None:
        """Attempt to load icons from the cache.

        Returns:
            Dictionary of cached icons if valid, None otherwise.
        """
        if not self.cache_dir or not self.cache_dir.exists():
            return None

        cache_info_file = self.cache_dir / "cache_info.json"
        if not cache_info_file.exists():
            return None

        try:
            with open(cache_info_file) as f:
                info = json.load(f)

            # Check if source image has changed (name or mtime)
            source_mtime = int(self.source_image.stat().st_mtime)
            if (
                info.get("source_name") != self.source_image.name
                or info.get("source_mtime") != source_mtime
            ):
                return None

            # Verify all expected files exist in cache
            cached_files = info.get("files", [])
            result = {}
            for filename in cached_files:
                cached_path = self.cache_dir / filename
                if not cached_path.exists():
                    return None
                result[filename] = cached_path

            return result
        except Exception as e:
            print(f"Exception in _load_from_cache: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _save_to_cache(self, generated: dict[str, Path]) -> None:
        """Save successfully generated icons to the cache.

        Args:
            generated: Dictionary of generated icons and their paths.
        """
        if not self.cache_dir:
            return

        try:
            # Clear and recreate cache directory
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            # Copy generated files to cache
            filenames = []
            for filename, path in generated.items():
                shutil.copy2(path, self.cache_dir / filename)
                filenames.append(filename)

            # Save cache info
            info = {
                "source_name": self.source_image.name,
                "source_mtime": int(self.source_image.stat().st_mtime),
                "files": filenames,
            }
            with open(self.cache_dir / "cache_info.json", "w") as f:
                json.dump(info, f)

        except Exception as e:
            print(f"Warning: Failed to save icons to cache: {e}")

    def _generate_png_icons_batch(
        self,
        img: Image.Image,
        icon_specs: list[tuple[int, str]],
        generated: dict[str, Path],
    ) -> None:
        """Generate a batch of PNG icons with the same pattern.

        Args:
            img: Source PIL Image
            icon_specs: List of (size, filename) tuples
            generated: Dictionary to update with successfully generated icons
        """
        for size, filename in icon_specs:
            icon_path = self._generate_png_icon(img, size, filename)
            if icon_path:
                generated[filename] = icon_path

    def _generate_favicon(self, img: Image.Image) -> Path | None:
        """Generate a multi-resolution favicon.ico file.

        Args:
            img: Source PIL Image

        Returns:
            Path to the generated favicon.ico file, or None on failure
        """
        try:
            output_path = self.output_dir / "favicon.ico"

            # Generate multiple sizes for the favicon
            sizes = [16, 32, 48]
            icons = []

            for size in sizes:
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                # Convert to RGB for ICO format
                if resized.mode == "RGBA":
                    # Create a white background
                    background = Image.new("RGB", (size, size), (255, 255, 255))
                    background.paste(resized, mask=resized.split()[3])
                    icons.append(background)
                else:
                    icons.append(resized.convert("RGB"))

            # Save as multi-resolution ICO
            icons[0].save(
                output_path,
                format="ICO",
                sizes=[(s, s) for s in sizes],
                append_images=icons[1:],
            )

            return output_path

        except Exception as e:
            print(f"Error generating favicon: {e}")
            return None

    def _generate_png_icon(
        self, img: Image.Image, size: int, filename: str
    ) -> Path | None:
        """Generate a PNG icon at a specific size.

        Args:
            img: Source PIL Image
            size: Size in pixels (width and height, icons are square)
            filename: Output filename

        Returns:
            Path to the generated icon file, or None on failure
        """
        try:
            output_path = self.output_dir / filename

            # Resize to target size
            resized = img.resize((size, size), Image.Resampling.LANCZOS)

            # Save as PNG
            resized.save(output_path, format="PNG")

            return output_path

        except Exception as e:
            print(f"Error generating {filename}: {e}")
            return None

    def _generate_wide_tile(self, img: Image.Image) -> Path | None:
        """Generate a wide Windows tile (310x150).

        Args:
            img: Source PIL Image

        Returns:
            Path to the generated tile, or None on failure
        """
        try:
            output_path = self.output_dir / "mstile-310x150.png"

            # Create 310x150 image with centered icon
            # Resize icon to fit within the tile
            icon_size = 150  # Height of the tile
            resized = img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)

            # Create tile background
            tile = Image.new("RGBA", (310, 150), (0, 0, 0, 0))

            # Center the icon
            x_offset = (310 - icon_size) // 2
            y_offset = 0
            tile.paste(
                resized,
                (x_offset, y_offset),
                resized if resized.mode == "RGBA" else None,
            )

            # Save as PNG
            tile.save(output_path, format="PNG")

            return output_path

        except Exception as e:
            print(f"Error generating wide tile: {e}")
            return None

    def _generate_web_manifest(self) -> Path | None:
        """Generate a web manifest file for Android/PWA.

        Returns:
            Path to the generated manifest file, or None on failure
        """
        try:
            output_path = self.output_dir / "site.webmanifest"

            manifest = {
                "name": "",
                "short_name": "",
                "icons": [
                    {
                        "src": "/icons/android-chrome-192x192.png",
                        "sizes": "192x192",
                        "type": "image/png",
                    },
                    {
                        "src": "/icons/android-chrome-512x512.png",
                        "sizes": "512x512",
                        "type": "image/png",
                    },
                ],
                "theme_color": "#ffffff",
                "background_color": "#ffffff",
                "display": "standalone",
            }

            with open(output_path, "w") as f:
                json.dump(manifest, f, indent=2)

            return output_path

        except Exception as e:
            print(f"Error generating web manifest: {e}")
            return None

    def _generate_browserconfig(self) -> Path | None:
        """Generate browserconfig.xml for Windows tiles.

        Returns:
            Path to the generated browserconfig file, or None on failure
        """
        try:
            output_path = self.output_dir / "browserconfig.xml"

            # Create XML structure
            browserconfig = ET.Element("browserconfig")
            msapplication = ET.SubElement(browserconfig, "msapplication")
            tile = ET.SubElement(msapplication, "tile")

            # Add tile image references
            tiles = [
                ("square70x70logo", "/icons/mstile-70x70.png"),
                ("square150x150logo", "/icons/mstile-150x150.png"),
                ("wide310x150logo", "/icons/mstile-310x150.png"),
                ("square310x310logo", "/icons/mstile-310x310.png"),
            ]

            for name, src in tiles:
                element = ET.SubElement(tile, name)
                element.set("src", src)

            # Add tile color
            tile_color = ET.SubElement(tile, "TileColor")
            tile_color.text = "#ffffff"

            # Write XML to file
            tree = ET.ElementTree(browserconfig)
            ET.indent(tree, space="  ")
            tree.write(output_path, encoding="utf-8", xml_declaration=True)

            return output_path

        except Exception as e:
            print(f"Error generating browserconfig: {e}")
            return None
