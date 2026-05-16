"""Automatic image optimization and responsive variant generation for blogmore.

Processes images found in the ``extras/`` directory, generating resized WebP
variants at a configurable set of widths.  The resulting variant metadata is
used by [`blogmore.responsive_images`][] to rewrite ``<img>`` tags in generated
HTML into ``<picture>`` elements with ``srcset`` for responsive delivery.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

##############################################################################
# File extensions recognised as processable images.
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png"})

##############################################################################
# Default widths for the responsive size ladder (pixels).
DEFAULT_IMAGE_WIDTHS: list[int] = [480, 768, 1200]

##############################################################################
# Default quality for WebP output (1-95).
DEFAULT_IMAGE_QUALITY: int = 85


@dataclass
class ImageVariant:
    """Metadata for a single resized image variant.

    Attributes:
        url: Root-relative URL of the generated variant file (e.g. ``"/images/photo-480.webp"``).
        width: Width of the variant in pixels.
        mime_type: MIME type of the variant file (e.g. ``"image/webp"``).
    """

    url: str
    width: int
    mime_type: str


class ImageOptimizer:
    """Generate resized WebP image variants for responsive delivery.

    For each source image, this class produces WebP variants at the requested
    widths (skipping any width that exceeds the source image's own width).
    Variants are written next to the original file using the naming pattern
    ``{stem}-{width}w.webp``.

    Example usage::

        optimizer = ImageOptimizer(widths=[480, 768, 1200], quality=85)
        variants = optimizer.process_image(
            source_path=Path("/output/images/photo.jpg"),
            url_base="/images",
        )
    """

    def __init__(self, widths: list[int], quality: int) -> None:
        """Initialise the optimizer.

        Args:
            widths: Pixel widths to generate variants at.  Widths that exceed
                the source image's natural width are silently skipped.
            quality: WebP compression quality (1–95; higher means better
                quality but larger files).
        """
        self._widths = sorted(widths)
        self._quality = quality

    def process_image(
        self,
        source_path: Path,
        url_base: str,
    ) -> list[ImageVariant]:
        """Generate WebP variants for *source_path* and return their metadata.

        The variant files are written into the same directory as *source_path*.
        Each variant is named ``{stem}-{width}w.webp`` (e.g.
        ``photo-480w.webp``).  Widths that exceed the source image's natural
        width are skipped so we never upscale.

        Args:
            source_path: Absolute path to the source image file.
            url_base: Root-relative URL directory prefix for the generated
                variant URLs (e.g. ``"/images"``).  Must not include a
                trailing slash.

        Returns:
            A list of [`ImageVariant`][blogmore.image_optimizer.ImageVariant]
            objects describing each successfully generated variant, ordered by
            ascending width.  Returns an empty list if the source file cannot
            be opened or no variants were produced.
        """
        output_dir = source_path.parent
        stem = source_path.stem
        url_base = url_base.rstrip("/")

        try:
            with Image.open(source_path) as raw_img:
                source_width, source_height = raw_img.size
                # Normalise to RGB/RGBA so WebP encoding always works.
                if raw_img.mode not in ("RGB", "RGBA"):
                    img: Image.Image = raw_img.convert("RGB")
                else:
                    raw_img.load()
                    img = raw_img

                variants: list[ImageVariant] = []

                for width in self._widths:
                    if width >= source_width:
                        # Never upscale.
                        continue

                    height = round(source_height * width / source_width)
                    resized = img.resize((width, height), Image.Resampling.LANCZOS)

                    variant_filename = f"{stem}-{width}w.webp"
                    variant_path = output_dir / variant_filename
                    resized.save(variant_path, format="WEBP", quality=self._quality)

                    variant_url = f"{url_base}/{variant_filename}"
                    variants.append(
                        ImageVariant(
                            url=variant_url,
                            width=width,
                            mime_type="image/webp",
                        )
                    )

                return variants

        except (UnidentifiedImageError, OSError) as error:
            print(f"Warning: Could not process image {source_path.name}: {error}")
            return []
