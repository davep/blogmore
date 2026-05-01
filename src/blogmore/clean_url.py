"""Clean URL transformation utilities."""

##############################################################################
# Python imports.
from pathlib import PurePosixPath

##############################################################################
# The set of filenames that are treated as "index" files and stripped when
# clean_urls is enabled.  A frozenset allows the list to grow in future
# without changing any of the transformation logic.
CLEAN_URL_INDEX_FILES = frozenset({"index.html", "index.htm"})


def make_url_clean(url: str) -> str:
    """Strip a trailing index filename from a URL path.

    Checks whether the final path component of *url* is exactly one of the
    recognised index filenames (`index.html` or `index.htm`).  When it
    is, that component is removed so that, for example,
    `/posts/my-post/index.html` becomes `/posts/my-post/`.

    Only the exact index filename is stripped.  A URL whose final component
    merely *ends with* an index filename (e.g. `/search-index.html`) is
    returned unchanged, because `search-index.html` is not an index file
    — it is an ordinary page whose name happens to include the word
    `index`.

    Args:
        url: The URL path to clean.

    Returns:
        The URL with the trailing index filename removed, or the original URL
        if the final path component is not a recognised index filename.
    """
    name = PurePosixPath(url).name
    if name in CLEAN_URL_INDEX_FILES:
        return url.removesuffix(name)
    return url


### clean_url.py ends here
