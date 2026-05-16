"""BlogMore Markdown extension registry.

This module provides the single source of truth for the set of custom
Markdown extensions used throughout the application.
"""

from typing import Any

from blogmore.markdown.admonitions import AdmonitionsExtension
from blogmore.markdown.external_links import ExternalLinksExtension
from blogmore.markdown.heading_anchors import HeadingAnchorsExtension
from blogmore.markdown.optimised_images import OptimisedImagesExtension
from blogmore.markdown.strikethrough import StrikethroughExtension


def create_custom_extensions(
    site_url: str = "",
    image_manager: Any = None,
    content_dir: Any = None,
    with_optimised_images: bool = True,
) -> list[Any]:
    """Create instances of all custom BlogMore Markdown extensions.

    This is the single source of truth for BlogMore's custom Markdown
    extension set.  The full-rendering parser, the first-paragraph
    extractor, and the plain-text converter all pull their custom-extension
    list from here, so any new extension is automatically included in every
    context.

    Args:
        site_url: Base URL of the site; forwarded to
            :class:`~blogmore.markdown.external_links.ExternalLinksExtension`
            so it can distinguish internal from external links.
        image_manager: Optional ImageManager instance for image optimisation.
        content_dir: Optional content directory for image optimisation.
        with_optimised_images: Whether to include the image optimisation
            extension. Defaults to True.

    Returns:
        A list of configured custom Markdown extension instances.
    """
    extensions = [
        AdmonitionsExtension(),
        ExternalLinksExtension(site_url=site_url),
        HeadingAnchorsExtension(),
        StrikethroughExtension(),
    ]
    if with_optimised_images and image_manager is not None:
        extensions.append(
            OptimisedImagesExtension(
                image_manager=image_manager,
                content_dir=content_dir,
            )
        )
    return extensions
