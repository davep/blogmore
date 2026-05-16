"""Markdown extension for automatically optimizing and resizing local images."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from xml.etree.ElementTree import Element, SubElement

from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern

if TYPE_CHECKING:
    from pathlib import Path

    from blogmore.image_manager import ImageManager

# A more robust image regex that allows for optional spaces and various title delimiters
IMAGE_LINK_RE = r'\!\[(?P<alt>.*?)\]\s*\((?P<src>.*?)(?P<title>\s+".*?"|\s+\'.*?\')?\)'


class OptimizedImageInlineProcessor(Pattern):
    """Pattern processor that transforms local Markdown image syntax into responsive <picture> elements."""

    def __init__(
        self,
        pattern: str,
        md: Any,
        image_manager: ImageManager | None,
        content_dir: Path | None,
        output_url_base: str = "/static/images/optimized/",
        base_dir: Path | None = None,
    ) -> None:
        """Initialize the processor.

        Args:
            pattern: The regex pattern to match.
            md: The Markdown instance.
            image_manager: The ImageManager instance to handle optimization.
            content_dir: The blog's content directory for local file verification.
            output_url_base: Base URL where optimized images are served.
            base_dir: Directory of the current Markdown file for relative resolution.
        """
        super().__init__(pattern, md)
        self.image_manager = image_manager
        self.content_dir = content_dir
        self.output_url_base = output_url_base
        self.base_dir = base_dir

    def handleMatch(self, m: re.Match[str]) -> Element | None:
        """Process an image match.

        Args:
            m: The match object.

        Returns:
            The replacement element.
        """
        src = m.group("src").strip()
        alt = m.group("alt")
        title = m.group("title")
        if title:
            title = title.strip().strip('"').strip("'")

        if (
            not self.image_manager
            or not self.content_dir
            or not self._is_local_image(src)
        ):
            return self._create_standard_img(src, alt, title)

        # Remove fragment for path resolution
        clean_src = src.split("#")[0]

        # Resolve absolute path to the source image
        if clean_src.startswith("/"):
            # Check for the file directly in content_dir
            source_path = self.content_dir / clean_src.lstrip("/")
            # Also check in the "extras" directory, which is where BlogMore
            # usually expects static assets to live.
            if not source_path.is_file():
                extras_path = self.content_dir / "extras" / clean_src.lstrip("/")
                if extras_path.is_file():
                    source_path = extras_path
        elif self.base_dir:
            source_path = self.base_dir / clean_src
        else:
            source_path = self.content_dir / clean_src

        optimized = self.image_manager.get_optimized_image(source_path)
        if not optimized:
            # If it's a local path but file wasn't found, warn the user
            # as this is the most likely cause of "no difference in output".
            if not source_path.is_file():
                print(
                    f"Warning: Image optimization skipped; file not found: {source_path}"
                )
            return self._create_standard_img(src, alt, title)

        # Transform to <picture>
        return self._create_picture_element(optimized, src, alt, title)

    def _create_standard_img(self, src: str, alt: str, title: str | None) -> Element:
        """Create a standard <img> tag."""
        el = Element("img")
        el.set("src", src)
        el.set("alt", alt)
        if title:
            el.set("title", title)
        el.set("loading", "lazy")
        return el

    def _create_picture_element(
        self, optimized: Any, original_src: str, alt: str, title: str | None
    ) -> Element:
        """Create a <picture> element for a local image.

        Args:
            optimized: The OptimizedImage metadata.
            original_src: The original source URL (including fragments).
            alt: The alt text.
            title: The title text.

        Returns:
            A new <picture> element.
        """
        picture = Element("picture")

        # Check if we should include a standard (JPG/PNG) fallback
        with_fallback = True
        if self.image_manager:
            with_fallback = self.image_manager.site_config.image_jpeg_fallback

        # 1. Add WebP source
        if optimized.webp_paths:
            webp_source = SubElement(picture, "source")
            webp_source.set("type", "image/webp")

            srcset_parts = []
            for width, filename in sorted(optimized.webp_paths.items()):
                srcset_parts.append(f"{self.output_url_base}{filename} {width}w")

            webp_source.set("srcset", ", ".join(srcset_parts))
            webp_source.set("sizes", "(max-width: 800px) 100vw, 800px")

        # 2. Add standard (JPG/PNG) source if enabled
        if with_fallback and optimized.resized_paths:
            std_source = SubElement(picture, "source")
            first_file = next(iter(optimized.resized_paths.values()))
            if first_file.endswith((".jpg", ".jpeg")):
                std_source.set("type", "image/jpeg")
            elif first_file.endswith(".png"):
                std_source.set("type", "image/png")

            srcset_parts = []
            for width, filename in sorted(optimized.resized_paths.items()):
                srcset_parts.append(f"{self.output_url_base}{filename} {width}w")

            std_source.set("srcset", ", ".join(srcset_parts))
            std_source.set("sizes", "(max-width: 800px) 100vw, 800px")

        # 3. Add fallback <img>
        new_img = SubElement(picture, "img")
        new_img.set("alt", alt)
        if title:
            new_img.set("title", title)

        # Pick a sensible default src:
        # If we have resized versions, pick the largest.
        # Otherwise, use the original source (which might be the case for small images).
        if with_fallback and optimized.resized_paths:
            max_width = max(optimized.resized_paths.keys())
            fallback_src = f"{self.output_url_base}{optimized.resized_paths[max_width]}"
        elif not with_fallback and optimized.webp_paths:
            max_width = max(optimized.webp_paths.keys())
            fallback_src = f"{self.output_url_base}{optimized.webp_paths[max_width]}"
        else:
            # Fallback to the original URL if no resizing happened (e.g. image too small)
            fallback_src = original_src

        new_img.set("src", fallback_src)
        new_img.set("width", str(optimized.original_width))
        new_img.set("height", str(optimized.original_height))
        new_img.set("loading", "lazy")

        if "#centre" in original_src and "#centre" not in fallback_src:
            current_src = new_img.get("src", "")
            if current_src:
                new_img.set("src", f"{current_src}#centre")

        return picture

    def _is_local_image(self, src: str) -> bool:
        """Check if an image source refers to a local file."""
        if not src:
            return False
        parsed = urlparse(src)
        if parsed.scheme or parsed.netloc:
            return False
        return not src.startswith("//")


class OptimizedImagesExtension(Extension):
    """Markdown extension for optimized responsive images."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the extension."""
        self.config = {
            "image_manager": [None, "ImageManager instance"],
            "content_dir": [None, "Blog content directory"],
            "output_url_base": [
                "/static/images/optimized/",
                "Base URL for optimized images",
            ],
            "base_dir": [None, "Directory of the current Markdown file"],
        }
        if "image_manager" in kwargs:
            self.config["image_manager"][0] = kwargs.pop("image_manager")
        if "content_dir" in kwargs:
            self.config["content_dir"][0] = kwargs.pop("content_dir")
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Any) -> None:
        """Register the extension with the Markdown instance."""
        image_manager = self.getConfig("image_manager")
        content_dir = self.getConfig("content_dir")
        output_url_base = self.getConfig("output_url_base")
        base_dir = self.getConfig("base_dir")

        processor = OptimizedImageInlineProcessor(
            IMAGE_LINK_RE,
            md,
            image_manager,
            content_dir,
            output_url_base,
            base_dir,
        )
        # Register with high priority to run before standard image patterns
        md.inlinePatterns.register(processor, "optimized_images", 200)
        self.processor = processor

    def set_base_dir(self, base_dir: Path) -> None:
        """Update the base directory for the current document."""
        if hasattr(self, "processor"):
            self.processor.base_dir = base_dir


def makeExtension(**kwargs: Any) -> OptimizedImagesExtension:
    """Create and return an instance of the extension."""
    return OptimizedImagesExtension(**kwargs)
