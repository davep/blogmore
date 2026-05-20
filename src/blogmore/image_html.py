"""HTML generation utilities for optimised responsive images."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING, cast
from urllib.parse import urlparse

if TYPE_CHECKING:
    from blogmore.image_manager import ImageManager, OptimisedImage


def create_picture_element(
    optimised: OptimisedImage,
    original_src: str,
    alt: str,
    title: str | None,
    image_manager: ImageManager | None,
    output_url_base: str = "/static/images/optimised/",
) -> ET.Element:
    """Create a `<picture>` XML Element for an optimised image.

    Args:
        optimised: The metadata of the optimised image.
        original_src: The original image source URL.
        alt: The alternative text for the image.
        title: The optional title text for the image.
        image_manager: The image manager.
        output_url_base: The base URL path where optimised images are served.

    Returns:
        An XML `Element` representing the `<picture>` tag.
    """
    picture = ET.Element("picture")

    # Strip fragment for use in srcset
    original_url_clean = original_src.split("#")[0]

    # Check if we should include a standard (JPG/PNG) fallback
    with_fallback = True
    if image_manager:
        with_fallback = image_manager.site_config.image_make_source_fallback

    # 1. Add WebP source
    # We include it if we have generated WebP versions OR if the original is WebP
    # and we wanted an optimised version at its original size.
    has_webp = bool(optimised.webp_paths) or (
        optimised.original_is_webp and optimised.original_width in optimised.widths
    )

    if has_webp:
        webp_source = ET.SubElement(picture, "source")
        webp_source.set("type", "image/webp")

        srcset_parts = []
        # Add all generated WebP versions
        for width, filename in sorted(optimised.webp_paths.items()):
            srcset_parts.append(f"{output_url_base}{filename} {width}w")

        # Add the original if it's WebP and was supposed to be in the ladder
        if (
            optimised.original_is_webp
            and optimised.original_width in optimised.widths
            and optimised.original_width not in optimised.webp_paths
        ):
            srcset_parts.append(f"{original_url_clean} {optimised.original_width}w")

        # Sort by width for consistency
        srcset_parts.sort(key=lambda x: int(x.split()[-1].removesuffix("w")))
        webp_source.set("srcset", ", ".join(srcset_parts))
        webp_source.set("sizes", "(max-width: 800px) 100vw, 800px")

    # 2. Add standard (JPG/PNG) source if enabled
    has_std = (optimised.resized_paths and with_fallback) or (
        with_fallback
        and optimised.original_is_standard
        and optimised.original_width in optimised.widths
    )

    if has_std:
        std_source = ET.SubElement(picture, "source")
        # Determine type from either generated or original
        first_file = (
            next(iter(optimised.resized_paths.values()))
            if optimised.resized_paths
            else original_url_clean
        )
        if first_file.lower().endswith((".jpg", ".jpeg")):
            std_source.set("type", "image/jpeg")
        elif first_file.lower().endswith(".png"):
            std_source.set("type", "image/png")

        srcset_parts = []
        for width, filename in sorted(optimised.resized_paths.items()):
            srcset_parts.append(f"{output_url_base}{filename} {width}w")

        if (
            optimised.original_is_standard
            and optimised.original_width in optimised.widths
            and optimised.original_width not in optimised.resized_paths
        ):
            srcset_parts.append(f"{original_url_clean} {optimised.original_width}w")

        srcset_parts.sort(key=lambda x: int(x.split()[-1].removesuffix("w")))
        std_source.set("srcset", ", ".join(srcset_parts))
        std_source.set("sizes", "(max-width: 800px) 100vw, 800px")

    # 3. Add fallback <img>
    new_img = ET.SubElement(picture, "img")
    new_img.set("alt", alt)
    if title:
        new_img.set("title", title)

    # Pick a sensible default src:
    # Largest of standard versions, or original if it's standard.
    std_available_widths = set(optimised.resized_paths.keys())
    if optimised.original_is_standard:
        std_available_widths.add(optimised.original_width)

    if with_fallback and std_available_widths:
        max_width = max(std_available_widths)
        if max_width == optimised.original_width and optimised.original_is_standard:
            fallback_src = original_src
        else:
            fallback_src = f"{output_url_base}{optimised.resized_paths[max_width]}"
    else:
        # Fallback to WebP or original
        webp_available_widths = set(optimised.webp_paths.keys())
        if optimised.original_is_webp:
            webp_available_widths.add(optimised.original_width)

        if not with_fallback and webp_available_widths:
            max_width = max(webp_available_widths)
            if max_width == optimised.original_width and optimised.original_is_webp:
                fallback_src = original_src
            else:
                fallback_src = f"{output_url_base}{optimised.webp_paths[max_width]}"
        else:
            fallback_src = original_src

    new_img.set("src", fallback_src)
    new_img.set("width", str(optimised.original_width))
    new_img.set("height", str(optimised.original_height))
    new_img.set("loading", "lazy")

    # Ensure centering fragment is preserved if we switched to an optimised URL
    if "#centre" in original_src and "#centre" not in new_img.get("src", ""):
        current_src = new_img.get("src", "")
        if current_src:
            new_img.set("src", f"{current_src}#centre")

    return picture


def render_picture_element(
    optimised: OptimisedImage,
    original_src: str,
    alt: str,
    title: str | None,
    image_manager: ImageManager | None,
    output_url_base: str = "/static/images/optimised/",
) -> str:
    """Create a `<picture>` element and render it as an HTML string.

    Args:
        optimised: The metadata of the optimised image.
        original_src: The original image source URL.
        alt: The alternative text for the image.
        title: The optional title text for the image.
        image_manager: The image manager.
        output_url_base: The base URL path where optimised images are served.

    Returns:
        The rendered HTML string.
    """
    element = create_picture_element(
        optimised,
        original_src,
        alt,
        title,
        image_manager,
        output_url_base,
    )
    return cast(
        str,
        ET.tostring(element, encoding="utf-8", method="html").decode("utf-8"),
    )


def render_logo_picture_html(
    logo_path: str,
    content_dir: Path,
    alt: str,
    image_manager: ImageManager,
) -> tuple[str, str] | None:
    """Resolve a sidebar logo to a responsive `<picture>` HTML string.

    Locates the logo file within `content_dir` (or its ``extras/``
    subdirectory), registers it with `image_manager`, and renders the
    resulting `<picture>` element as an HTML string.

    Returns `None` when the logo is a remote URL, the source file cannot be
    found, or the [`ImageManager`][blogmore.image_manager.ImageManager] has no
    optimised entry for the file.

    Args:
        logo_path: The raw logo path from configuration (may be a relative
            path like ``/img/logo.png`` or a remote URL).
        content_dir: The blog content directory used to locate the file.
        alt: Alt text for the fallback ``<img>`` element.
        image_manager: The image manager used to retrieve the optimised
            image metadata.

    Returns:
        A ``(picture_html, fallback_src)`` pair where *picture_html* is the
        rendered ``<picture>`` HTML string and *fallback_src* is the URL of
        the best standard-format fallback image; or ``None`` if the logo
        cannot be optimised.
    """
    parsed = urlparse(logo_path)
    if parsed.scheme or parsed.netloc or logo_path.startswith("//"):
        return None

    clean_logo = logo_path.split("#")[0].split("?")[0].lstrip("/")
    source_path = content_dir / clean_logo
    if not source_path.is_file():
        extras_path = content_dir / "extras" / clean_logo
        if extras_path.is_file():
            source_path = extras_path

    if not source_path.is_file():
        return None

    optimised = image_manager.get_optimised_image(source_path)
    if not optimised:
        return None

    picture_el = create_picture_element(
        optimised,
        logo_path,
        alt,
        None,
        image_manager,
    )

    img_el = picture_el.find("img")
    fallback_src = img_el.get("src", logo_path) if img_el is not None else logo_path

    html_str = cast(
        str,
        ET.tostring(picture_el, encoding="utf-8", method="html").decode("utf-8"),
    )
    return html_str, fallback_src
