"""Static site generator for blog content.

This package re-exports all public symbols that were previously available
directly from the ``blogmore.generator`` module, ensuring full backward
compatibility for existing imports.
"""

from blogmore.generator.site import SiteGenerator
from blogmore.generator.utils import minified_filename, paginate_posts

__all__ = [
    "SiteGenerator",
    "minified_filename",
    "paginate_posts",
]

### __init__.py ends here
