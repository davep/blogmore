"""Icon generation from a single source image for blogmore."""

from pathlib import Path

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
    """Generate favicon and Apple touch icons from a single source image."""

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

                # Generate favicon.ico
                favicon_path = self._generate_favicon(img)
                if favicon_path:
                    generated["favicon.ico"] = favicon_path

                # Generate Apple touch icons
                apple_icons = [
                    (180, "apple-touch-icon.png"),
                    (120, "apple-touch-icon-120.png"),
                    (152, "apple-touch-icon-152.png"),
                    (167, "apple-touch-icon-167.png"),
                    (180, "apple-touch-icon-precomposed.png"),
                ]

                for size, filename in apple_icons:
                    icon_path = self._generate_apple_icon(img, size, filename)
                    if icon_path:
                        generated[filename] = icon_path

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

    def _generate_apple_icon(
        self, img: Image.Image, size: int, filename: str
    ) -> Path | None:
        """Generate an Apple touch icon at a specific size.

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
