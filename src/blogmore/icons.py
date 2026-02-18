"""Icon generation from a single source image for blogmore."""

import json
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image


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
        custom_path = extras_dir / custom_filename
        if custom_path.is_file():
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
        candidate_path = extras_dir / candidate
        if candidate_path.is_file():
            return candidate_path

    return None


class IconGenerator:
    """Generate favicon and platform-specific icons from a single source image."""

    def __init__(self, source_image: Path, output_dir: Path) -> None:
        """Initialize the icon generator.

        Args:
            source_image: Path to the source image file
            output_dir: Directory where icons will be written (should be /icons subdirectory)
        """
        self.source_image = source_image
        self.output_dir = output_dir

    def generate_all(self) -> dict[str, Path]:
        """Generate all icon formats from the source image.

        Returns:
            Dictionary mapping icon name to output path for successfully generated icons
        """
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

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

                # Generate standard favicon PNG sizes
                favicon_sizes = [
                    (16, "favicon-16x16.png"),
                    (32, "favicon-32x32.png"),
                    (96, "favicon-96x96.png"),
                ]
                for size, filename in favicon_sizes:
                    icon_path = self._generate_png_icon(img, size, filename)
                    if icon_path:
                        generated[filename] = icon_path

                # Generate Apple touch icons
                apple_icons = [
                    (180, "apple-touch-icon.png"),
                    (120, "apple-touch-icon-120.png"),
                    (152, "apple-touch-icon-152.png"),
                    (167, "apple-touch-icon-167.png"),
                    (180, "apple-touch-icon-precomposed.png"),
                ]
                for size, filename in apple_icons:
                    icon_path = self._generate_png_icon(img, size, filename)
                    if icon_path:
                        generated[filename] = icon_path

                # Generate Android/Chrome icons
                android_icons = [
                    (192, "android-chrome-192x192.png"),
                    (512, "android-chrome-512x512.png"),
                ]
                for size, filename in android_icons:
                    icon_path = self._generate_png_icon(img, size, filename)
                    if icon_path:
                        generated[filename] = icon_path

                # Generate Windows/Microsoft tiles
                windows_tiles = [
                    (70, "mstile-70x70.png"),
                    (144, "mstile-144x144.png"),
                    (150, "mstile-150x150.png"),
                    (310, "mstile-310x310.png"),
                ]
                for size, filename in windows_tiles:
                    icon_path = self._generate_png_icon(img, size, filename)
                    if icon_path:
                        generated[filename] = icon_path

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

                return generated

        except Exception as e:
            print(f"Error generating icons: {e}")
            return {}

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
            tile.paste(resized, (x_offset, y_offset), resized if resized.mode == "RGBA" else None)

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

