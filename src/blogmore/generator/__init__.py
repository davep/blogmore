"""Static site generator for blog content."""

from blogmore.fontawesome import FontAwesomeOptimizer
from blogmore.generator.constants import (
    ARCHIVE_CSS_FILENAME,
    CALENDAR_CSS_FILENAME,
    CODE_CSS_FILENAME,
    CODEBLOCKS_JS_FILENAME,
    CSS_FILENAME,
    GRAPH_CSS_FILENAME,
    GRAPH_JS_FILENAME,
    SEARCH_CSS_FILENAME,
    SEARCH_JS_FILENAME,
    STATS_CSS_FILENAME,
    TAG_CLOUD_CSS_FILENAME,
    THEME_JS_FILENAME,
)
from blogmore.generator.site import SiteGenerator
from blogmore.generator.utils import minified_filename, paginate_posts
from blogmore.parser import sanitize_for_url

__all__ = [
    "SiteGenerator",
    "minified_filename",
    "paginate_posts",
    "sanitize_for_url",
    "FontAwesomeOptimizer",
    "CSS_FILENAME",
    "SEARCH_CSS_FILENAME",
    "STATS_CSS_FILENAME",
    "ARCHIVE_CSS_FILENAME",
    "CALENDAR_CSS_FILENAME",
    "GRAPH_CSS_FILENAME",
    "TAG_CLOUD_CSS_FILENAME",
    "GRAPH_JS_FILENAME",
    "CODE_CSS_FILENAME",
    "THEME_JS_FILENAME",
    "SEARCH_JS_FILENAME",
    "CODEBLOCKS_JS_FILENAME",
]
