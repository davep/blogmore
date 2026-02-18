"""Markdown extension to open external links in a new tab."""

from typing import Any
from urllib.parse import urlparse
from xml.etree.ElementTree import Element

from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


class ExternalLinksProcessor(Treeprocessor):
    """Tree processor that adds target="_blank" to external links."""

    def __init__(self, md: Any, site_url: str | None = None) -> None:
        """Initialize the processor with optional site URL.

        Args:
            md: Markdown instance
            site_url: The base URL of the site for determining internal vs external links
        """
        super().__init__(md)
        self.site_url = site_url
        # Parse the site URL to get the domain
        self.site_domain: str | None
        if site_url:
            parsed = urlparse(site_url)
            self.site_domain = parsed.netloc.lower()
        else:
            self.site_domain = None

    def run(self, root: Element) -> Element | None:
        """Process all anchor tags in the element tree.

        Args:
            root: The root element of the markdown tree

        Returns:
            The modified root element or None
        """
        self._process_element(root)
        return None

    def _process_element(self, element: Element) -> None:
        """Recursively process an element and its children.

        Args:
            element: The element to process
        """
        # Process current element if it's an anchor tag
        if element.tag == "a":
            self._process_link(element)

        # Recursively process all children
        for child in element:
            self._process_element(child)

    def _process_link(self, element: Element) -> None:
        """Process a link element to determine if it's external.

        Args:
            element: The anchor element to process
        """
        href = element.get("href", "")

        # Skip empty hrefs
        if not href:
            return

        # Check if link is external
        if self._is_external_link(href):
            # Add target="_blank" to open in new tab
            element.set("target", "_blank")
            # Add rel="noopener noreferrer" for security
            element.set("rel", "noopener noreferrer")

    def _is_external_link(self, href: str) -> bool:
        """Determine if a link is external.

        Args:
            href: The href attribute value

        Returns:
            True if the link is external, False otherwise
        """
        # Relative links (starting with /, #, or no scheme) are internal
        if href.startswith("/") or href.startswith("#"):
            return False

        # Parse the URL
        parsed = urlparse(href)

        # If there's no scheme or netloc, it's a relative link (internal)
        if not parsed.scheme and not parsed.netloc:
            return False

        # If we have a site domain, check if the link matches
        if self.site_domain:
            link_domain = parsed.netloc.lower()
            # If domains match, it's internal
            if (
                link_domain == self.site_domain
                or link_domain == f"www.{self.site_domain}"
            ):
                return False

        # All other links with schemes are external
        return True


class ExternalLinksExtension(Extension):
    """Markdown extension to handle external links."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the extension with configuration.

        Args:
            **kwargs: Configuration options, including 'site_url'
        """
        self.config = {"site_url": ["", "Base URL of the site"]}
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Any) -> None:
        """Register the extension with the Markdown instance.

        Args:
            md: The Markdown instance
        """
        site_url = self.getConfig("site_url")
        processor = ExternalLinksProcessor(md, site_url)
        # Add the processor with a priority that runs after standard link processing
        md.treeprocessors.register(processor, "external_links", 5)


def makeExtension(**kwargs: Any) -> ExternalLinksExtension:
    """Create and return an instance of the extension.

    Args:
        **kwargs: Configuration options

    Returns:
        An instance of ExternalLinksExtension
    """
    return ExternalLinksExtension(**kwargs)
