"""HTML rewriting utilities for responsive image delivery.

Provides [`rewrite_img_tags`][blogmore.responsive_images.rewrite_img_tags],
which scans rendered post/page HTML for ``<img>`` elements whose ``src``
attribute matches a processed image URL and replaces them with ``<picture>``
elements that include a WebP ``<source srcset="…">`` for responsive delivery,
with the original ``<img>`` retained as a fallback.

A ``loading="lazy"`` attribute is also added to any ``<img>`` tag that does
not already carry a ``loading`` attribute, regardless of whether the surrounding
``<picture>`` rewrite applies.
"""

from __future__ import annotations

import re

from blogmore.image_optimizer import ImageVariant

##############################################################################
# Regex that matches a single <img …> tag (self-closing or not).
# Group 1 captures all attribute text inside the tag.
_IMG_TAG_RE = re.compile(
    r"<img\s*([^>]*?)(?:\s*/)?>",
    re.IGNORECASE | re.DOTALL,
)

##############################################################################
# Regex to extract the value of the src attribute from an img tag's attribute
# string.  Handles both double- and single-quoted values.
_SRC_ATTR_RE = re.compile(
    r"""src\s*=\s*(?:"([^"]*)"|'([^']*)')""",
    re.IGNORECASE,
)

##############################################################################
# Regex to check whether a loading attribute is already present.
_LOADING_ATTR_RE = re.compile(r"\bloading\s*=", re.IGNORECASE)


def _add_lazy_loading(attrs: str) -> str:
    """Append ``loading="lazy"`` to an attribute string if not already present.

    Args:
        attrs: The raw attribute string from an ``<img>`` tag.

    Returns:
        The attribute string with ``loading="lazy"`` appended when absent.
    """
    if _LOADING_ATTR_RE.search(attrs):
        return attrs
    return attrs.rstrip() + ' loading="lazy"'


def _build_srcset(variants: list[ImageVariant]) -> str:
    """Build a ``srcset`` attribute value from a list of variants.

    Args:
        variants: Ordered list of image variants (ascending width).

    Returns:
        A comma-separated ``srcset`` string, e.g.
        ``"/img/photo-480w.webp 480w, /img/photo-768w.webp 768w"``.
    """
    return ", ".join(f"{v.url} {v.width}w" for v in variants)


def _normalise_src_for_lookup(src: str) -> str:
    """Normalise an ``<img src>`` value to a root-relative form for variant lookup.

    Keys in the ``image_variants`` mapping are always root-relative
    (``/path/to/image.jpg``).  When Markdown posts reference an image without
    a leading slash (``![alt](attachments/photo.jpg)``), the rendered HTML
    carries ``src="attachments/photo.jpg"``.  This helper normalises such
    bare-relative paths to their root-relative equivalent so they match the
    dictionary keys produced by
    [`AssetManager.process_images`][blogmore.generator.assets.AssetManager.process_images].

    Full URLs (``http://`` / ``https://`` / ``data:``) and fragment-only
    references (``#anchor``) are returned unchanged.

    Args:
        src: The raw value of the ``src`` attribute.

    Returns:
        A root-relative URL string, or *src* unchanged when normalisation is
        not applicable.
    """
    # Leave absolute URLs, data URIs, and fragment anchors as-is.
    if src.startswith("/") or src.startswith("#"):
        return src
    lower = src.lower()
    if (
        lower.startswith("http://")
        or lower.startswith("https://")
        or lower.startswith("data:")
    ):
        return src
    # Bare-relative path — prepend a leading slash.
    return "/" + src


def _replace_img_tag(
    match: re.Match[str],
    image_variants: dict[str, list[ImageVariant]],
) -> str:
    """Replace a single ``<img>`` tag with a ``<picture>`` element if variants exist.

    Always adds ``loading="lazy"`` to the fallback ``<img>`` when absent.

    The ``src`` attribute is normalised to a root-relative URL before the
    variant lookup so that both ``src="/photo.jpg"`` and ``src="photo.jpg"``
    resolve correctly against the dictionary produced by
    [`AssetManager.process_images`][blogmore.generator.assets.AssetManager.process_images].
    The original ``src`` value in the rendered HTML is left untouched.

    Args:
        match: A regex match object for the ``<img>`` tag.
        image_variants: Mapping from original image URL (e.g. ``"/images/photo.jpg"``)
            to its list of [`ImageVariant`][blogmore.image_optimizer.ImageVariant] objects.

    Returns:
        The replacement HTML string — either a ``<picture>`` element wrapping
        the original ``<img>``, or the original tag with ``loading="lazy"``
        added.
    """
    attrs = match.group(1)
    src_match = _SRC_ATTR_RE.search(attrs)
    if src_match is None:
        return match.group(0)

    src = src_match.group(1) or src_match.group(2)
    lazy_attrs = _add_lazy_loading(attrs)

    lookup_key = _normalise_src_for_lookup(src)
    variants = image_variants.get(lookup_key)
    if not variants:
        return f"<img {lazy_attrs}>"

    srcset = _build_srcset(variants)
    fallback_img = f"<img {lazy_attrs}>"
    source_tag = f'<source type="image/webp" srcset="{srcset}">'
    return f"<picture>{source_tag}{fallback_img}</picture>"


def rewrite_img_tags(
    html: str,
    image_variants: dict[str, list[ImageVariant]],
) -> str:
    """Rewrite ``<img>`` tags in *html* to use ``<picture>`` + ``srcset`` where available.

    For each ``<img>`` whose ``src`` maps to an entry in *image_variants*, the
    tag is wrapped in a ``<picture>`` element containing a ``<source>`` with a
    WebP ``srcset``.  The original ``<img>`` is preserved as the fallback.

    Additionally, ``loading="lazy"`` is injected into every ``<img>`` tag that
    does not already carry a ``loading`` attribute, whether or not responsive
    variants are available for that image.

    Args:
        html: The rendered HTML to process.
        image_variants: Mapping from original image URL to the list of generated
            [`ImageVariant`][blogmore.image_optimizer.ImageVariant] objects produced
            by [`ImageOptimizer.process_image`][blogmore.image_optimizer.ImageOptimizer.process_image].
            Keys must be root-relative URLs matching the ``src`` values used in
            the Markdown source (e.g. ``"/images/photo.jpg"``).

    Returns:
        The HTML string with ``<img>`` tags rewritten as described above.
    """
    return _IMG_TAG_RE.sub(
        lambda m: _replace_img_tag(m, image_variants),
        html,
    )
