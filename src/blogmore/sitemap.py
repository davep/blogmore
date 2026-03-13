"""XML sitemap generation for static sites."""

from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, indent, tostring

from blogmore.parser import CUSTOM_404_HTML
from blogmore.utils import normalize_site_url

SITEMAP_XMLNS = "http://www.sitemaps.org/schemas/sitemap/0.9"
SITEMAP_FILENAME = "sitemap.xml"

# Pages to exclude from the sitemap
EXCLUDED_PAGES = frozenset({"search.html", CUSTOM_404_HTML})


def collect_sitemap_urls(
    output_dir: Path, site_url: str, clean_urls: bool = False
) -> list[str]:
    """Collect all page URLs for the sitemap.

    Walks the output directory collecting every ``.html`` file, excluding
    ``search.html``.  Each file path is converted to an absolute URL using
    ``site_url`` as the base.  If ``site_url`` is empty, the fallback
    ``https://example.com`` is used.

    When *clean_urls* is ``True``, any URL that ends with ``/index.html``
    has the ``index.html`` portion removed so the URL ends with a trailing
    slash instead.

    Args:
        output_dir: The output directory containing the generated site.
        site_url: Base URL of the site (e.g. ``https://example.com``).
        clean_urls: When ``True``, strip ``index.html`` from URLs that end
            with it.

    Returns:
        Sorted list of absolute URL strings, one per generated page.
    """
    normalized = normalize_site_url(site_url)
    base_url = normalized if normalized else "https://example.com"

    urls = []
    for html_file in sorted(output_dir.rglob("*.html")):
        relative_path = html_file.relative_to(output_dir)

        # Exclude certain pages (e.g. search.html)
        if relative_path.name in EXCLUDED_PAGES:
            continue

        # Convert any OS-specific path separators to forward slashes
        url_path = "/" + str(relative_path).replace("\\", "/")

        # Apply clean URL transformation when enabled
        if clean_urls and url_path.endswith("/index.html"):
            url_path = url_path[: -len("index.html")]

        urls.append(f"{base_url}{url_path}")

    return urls


def generate_sitemap_xml(urls: list[str]) -> str:
    """Generate XML sitemap content from a list of URLs.

    Produces a valid XML sitemap conforming to the
    ``http://www.sitemaps.org/schemas/sitemap/0.9`` schema, with one
    ``<url><loc>`` entry per URL.

    Args:
        urls: List of absolute URL strings to include in the sitemap.

    Returns:
        Well-formed XML sitemap as a UTF-8 string.
    """
    root = Element("urlset")
    root.set("xmlns", SITEMAP_XMLNS)

    for url in urls:
        url_elem = SubElement(root, "url")
        loc = SubElement(url_elem, "loc")
        loc.text = url

    indent(root, space="  ")
    xml_str = tostring(root, encoding="unicode", xml_declaration=False)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}\n'


def write_sitemap(output_dir: Path, site_url: str, clean_urls: bool = False) -> None:
    """Generate and write the XML sitemap file.

    Collects all HTML pages in the output directory (excluding
    ``search.html``) and writes ``sitemap.xml`` to the root of the output
    directory.

    Args:
        output_dir: The output directory containing the generated site.
        site_url: Base URL of the site (e.g. ``https://example.com``).
        clean_urls: When ``True``, strip ``index.html`` from URLs that end
            with it.
    """
    urls = collect_sitemap_urls(output_dir, site_url, clean_urls=clean_urls)
    xml_content = generate_sitemap_xml(urls)
    sitemap_path = output_dir / SITEMAP_FILENAME
    sitemap_path.write_text(xml_content, encoding="utf-8")
