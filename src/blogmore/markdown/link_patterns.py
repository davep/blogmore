"""Compiled regular expressions for Markdown link detection.

Centralises all Markdown link-related regex patterns so that both the
backlink analyser ([`backlinks`][blogmore.backlinks]) and the site linter
([`linter`][blogmore.linter]) can import from a single source of truth
rather than maintaining independent copies.

The URL-capturing group used inside inline-link patterns supports one level
of balanced parentheses so that paths such as
``/2016/11/15/seen_by_davep_(the_return).html`` are captured in full.  The
atomic group ``(?>...)`` prevents catastrophic backtracking when the regex
engine encounters a long run of characters without a matching closing ``)``.
This requires Python 3.11+ (this codebase targets 3.12+).
"""

##############################################################################
# Python imports.
import re

##############################################################################
# The URL-capturing group shared by all inline-link patterns.
# Allows one level of balanced parentheses inside the URL.
_URL_GROUP: str = r"((?>[^()]+|\([^()]*\))*)"

##############################################################################
# Inline link patterns.

INLINE_ALL_LINK_RE: re.Pattern[str] = re.compile(
    r"\[([^\]]*)\]\(" + _URL_GROUP + r"\)"
)
"""Inline links, both image and non-image: ``[text](url)`` and ``![alt](url)``.

Used by the backlink analyser which processes all link types uniformly.
"""

INLINE_LINK_RE: re.Pattern[str] = re.compile(
    r"(?<!!)\[([^\]]*)\]\(" + _URL_GROUP + r"\)"
)
"""Non-image inline links only: ``[text](url)``.

The negative lookbehind ``(?<!!)`` excludes image links (``![alt](url)``).
Used by the linter for regular-link checks.
"""

INLINE_IMAGE_RE: re.Pattern[str] = re.compile(
    r"!\[([^\]]*)\]\(" + _URL_GROUP + r"\)"
)
"""Inline image links only: ``![alt](url)``.

Used by the linter for image-file existence checks.
"""

##############################################################################
# Reference-style link patterns.

REF_ALL_LINK_RE: re.Pattern[str] = re.compile(r"\[([^\]]+)\]\[([^\]]*)\]")
"""Reference-style links, both image and non-image: ``[text][ref]`` and ``![alt][ref]``.

Used by the backlink analyser which processes all link types uniformly.
"""

REF_LINK_RE: re.Pattern[str] = re.compile(r"(?<!!)\[([^\]]+)\]\[([^\]]*)\]")
"""Non-image reference-style links only: ``[text][ref]`` or ``[text][]``.

The negative lookbehind ``(?<!!)`` excludes image links (``![alt][ref]``).
Used by the linter for regular-link checks.
"""

REF_IMAGE_RE: re.Pattern[str] = re.compile(r"!\[([^\]]+)\]\[([^\]]*)\]")
"""Reference-style image links only: ``![alt][ref]`` or ``![alt][]``.

Used by the linter for image-file existence checks.
"""

##############################################################################
# Link definition pattern.

LINK_DEF_RE: re.Pattern[str] = re.compile(
    r"^\[([^\]]+)\]:\s+(\S+)", re.MULTILINE
)
"""Reference link definitions: ``[id]: url`` at the start of any line.

Used by both the backlink analyser and the linter to resolve reference-style
link IDs to their target URLs.
"""

### link_patterns.py ends here
