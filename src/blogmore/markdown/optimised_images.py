"""Markdown extension for automatically optimising and resizing local images."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from xml.etree.ElementTree import Element

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor

from blogmore.console import print_warning
from blogmore.image_html import create_picture_element

if TYPE_CHECKING:
    from pathlib import Path

    from markdown import Markdown

    from blogmore.image_manager import ImageManager, OptimisedImage

# A more robust image regex that allows for optional spaces and various title delimiters
IMAGE_LINK_RE = (
    r"\!\[(?P<alt>.*?)\]\s*\(\s*(?P<src><.*?>|"
    r'([^\s\(\)]|\([^\s\)]*\))+)\s*(?P<title>\s+".*?"|\s+\'.*?\')?\s*\)'
)


class OptimisedImageInlineProcessor(InlineProcessor):
    """Inline processor that transforms local Markdown image syntax into responsive <picture> elements."""

    def __init__(
        self,
        pattern: str,
        md: Markdown,
        image_manager: ImageManager | None,
        content_dir: Path | None,
        output_url_base: str = "/static/images/optimised/",
        base_dir: Path | None = None,
    ) -> None:
        """Initialize the processor.

        Args:
            pattern: The regex pattern to match.
            md: The Markdown instance.
            image_manager: The ImageManager instance to handle optimisation.
            content_dir: The blog's content directory for local file verification.
            output_url_base: Base URL where optimised images are served.
            base_dir: Directory of the current Markdown file for relative resolution.
        """
        super().__init__(pattern, md)
        self.image_manager = image_manager
        self.content_dir = content_dir
        self.output_url_base = output_url_base
        self.base_dir = base_dir

    def handleMatch(  # type: ignore[override]
        self, m: re.Match[str], data: str
    ) -> tuple[Element | str | None, int | None, int | None]:
        """Process an image match.

        Args:
            m: The match object.
            data: The full document data.

        Returns:
            A tuple of (replacement element, start index, end index).
        """
        src = m.group("src").strip()
        if src.startswith("<") and src.endswith(">"):
            src = src[1:-1].strip()

        alt = m.group("alt")
        title = m.group("title")
        if title:
            title = title.strip().strip('"').strip("'")

        if (
            not self.image_manager
            or not self.content_dir
            or not self._is_local_image(src)
        ):
            return self._create_standard_img(src, alt, title), m.start(0), m.end(0)

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

        optimised = self.image_manager.get_optimised_image(source_path)
        if not optimised:
            # If it's a local path but file wasn't found, warn the user
            # as this is the most likely cause of "no difference in output".
            if not source_path.is_file():
                print_warning(
                    f"Warning: Image optimisation skipped; file not found: {source_path}"
                )
            return self._create_standard_img(src, alt, title), m.start(0), m.end(0)

        # Transform to <picture>
        return (
            self._create_picture_element(optimised, src, alt, title),
            m.start(0),
            m.end(0),
        )

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
        self, optimised: OptimisedImage, original_src: str, alt: str, title: str | None
    ) -> Element:
        """Create a <picture> element for a local image.

        Args:
            optimised: The OptimisedImage metadata.
            original_src: The original source URL (including fragments).
            alt: The alt text.
            title: The title text.

        Returns:
            A new <picture> element.
        """
        return create_picture_element(
            optimised,
            original_src,
            alt,
            title,
            self.image_manager,
            self.output_url_base,
        )

    def _is_local_image(self, src: str) -> bool:
        """Check if an image source refers to a local file."""
        if not src:
            return False
        parsed = urlparse(src)
        if parsed.scheme or parsed.netloc:
            return False
        return not src.startswith("//")


class OptimisedImagesExtension(Extension):
    """Markdown extension for optimised responsive images."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the extension."""
        self.config = {
            "image_manager": [None, "ImageManager instance"],
            "content_dir": [None, "Blog content directory"],
            "output_url_base": [
                "/static/images/optimised/",
                "Base URL for optimised images",
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

        processor = OptimisedImageInlineProcessor(
            IMAGE_LINK_RE,
            md,
            image_manager,
            content_dir,
            output_url_base,
            base_dir,
        )
        # Register with high priority to run before standard image patterns
        md.inlinePatterns.register(processor, "optimised_images", 200)
        self.processor = processor

    def set_base_dir(self, base_dir: Path) -> None:
        """Update the base directory for the current document."""
        if hasattr(self, "processor"):
            self.processor.base_dir = base_dir


def makeExtension(**kwargs: Any) -> OptimisedImagesExtension:
    """Create and return an instance of the extension."""
    return OptimisedImagesExtension(**kwargs)
