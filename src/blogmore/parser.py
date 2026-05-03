"""Markdown parser with frontmatter support for blog posts."""

import datetime as dt
import re
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frontmatter  # type: ignore[import-untyped]
import markdown
import yaml
from dateutil import parser as dateutil_parser
from pygments.formatters import HtmlFormatter

from blogmore.markdown.first_paragraph import extract_first_paragraph
from blogmore.markdown.plain_text import create_custom_extensions
from blogmore.utils import calculate_reading_time

_DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S %z",
    "%Y-%m-%d %H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
]

CUSTOM_404_MARKDOWN = "404.md"
CUSTOM_404_HTML = "404.html"

_LANG_PREFIX = "language-"


class _LangAwareHtmlFormatter(HtmlFormatter[str]):
    """Pygments HTML formatter that exposes the detected language via a data attribute.

    The codehilite Markdown extension passes the fenced code block language as
    `lang_str` (e.g. `language-python`) when constructing the formatter.
    This subclass captures that value and writes it as a `data-lang` attribute
    on the wrapper `<div>`, making it available to JavaScript without any
    additional post-processing.
    """

    def __init__(self, lang_str: str = "", **kwargs: Any) -> None:
        """Initialise the formatter.

        Args:
            lang_str: The language string passed by codehilite, typically in the
                form `language-<name>` (e.g. `language-python`).  An empty
                string means no language was specified.
            **kwargs: Remaining keyword arguments forwarded to
                `pygments.formatters.HtmlFormatter`.
        """
        super().__init__(**kwargs)
        self._lang_name = lang_str.removeprefix(_LANG_PREFIX) if lang_str else ""

    def _wrap_div(
        self, inner: Generator[tuple[int, str], None, None]
    ) -> Generator[tuple[int, str], None, None]:
        """Wrap the highlighted code in a `<div>` element.

        Extends the parent implementation by adding a `data-lang` attribute
        when a language name is available.

        Args:
            inner: Generator of `(token_type, value)` tuples from the parent.

        Yields:
            `(token_type, value)` tuples forming the wrapped HTML.
        """
        style_parts: list[str] = []
        if (
            self.noclasses
            and not self.nobackground
            and self.style.background_color is not None
        ):
            style_parts.append(f"background: {self.style.background_color}")
        if self.cssstyles:
            style_parts.append(self.cssstyles)
        style_attr = f' style="{"; ".join(style_parts)}"' if style_parts else ""
        class_attr = f' class="{self.cssclass}"' if self.cssclass else ""
        lang_attr = f' data-lang="{self._lang_name}"' if self._lang_name else ""

        yield 0, f"<div{class_attr}{lang_attr}{style_attr}>"
        yield from inner
        yield 0, "</div>\n"


def sanitize_for_url(value: str) -> str:
    """Sanitize a string for safe use in URLs and filenames.

    Args:
        value: The string to sanitize

    Returns:
        A sanitized string safe for URLs and filenames
    """
    # Remove or replace dangerous characters
    # Allow only alphanumeric, dash, underscore
    sanitized = re.sub(r"[^\w\-]", "-", value.lower())
    # Remove multiple consecutive dashes
    sanitized = re.sub(r"-+", "-", sanitized)
    # Remove leading/trailing dashes
    sanitized = sanitized.strip("-")
    # Ensure it's not empty
    return sanitized or "unnamed"


def remove_date_prefix(slug: str) -> str:
    """Remove YYYY-MM-DD- date prefix from a slug if present.

    Args:
        slug: The slug potentially containing a date prefix

    Returns:
        The slug without the date prefix
    """
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", slug)


@dataclass
class Post:
    """Represents a blog post with metadata and content."""

    path: Path
    title: str
    content: str
    html_content: str
    date: dt.datetime | None = None
    category: str | None = None
    tags: list[str] | None = None
    draft: bool = False
    metadata: dict[str, Any] | None = None
    url_path: str | None = field(default=None, repr=False, compare=False)
    words_per_minute: int = field(default=200, repr=False, compare=False)

    @property
    def slug(self) -> str:
        """Generate a URL slug from the post filename."""
        return self.path.stem

    @property
    def url(self) -> str:
        """Generate the URL path for the post.

        If the generator has resolved a custom URL via the `post_path`
        configuration option it will be stored in `url_path` and returned
        directly.  Otherwise the URL is derived from the post date and slug
        using the default `/{year}/{month}/{day}/{slug}.html` scheme.

        Returns:
            The URL path for the post, always beginning with `/`.
        """
        if self.url_path is not None:
            return self.url_path
        if self.date:
            # Extract date components
            year = self.date.year
            month = f"{self.date.month:02d}"
            day = f"{self.date.day:02d}"
            # Remove date prefix from slug if present
            slug = remove_date_prefix(self.slug)
            return f"/{year}/{month}/{day}/{slug}.html"
        # Fallback for posts without dates
        return f"/{self.slug}.html"

    @property
    def safe_category(self) -> str | None:
        """Get the category sanitized for use in URLs and filenames."""
        if self.category:
            return sanitize_for_url(self.category)
        return None

    def safe_tags(self) -> list[str]:
        """Get tags sanitized for use in URLs and filenames."""
        if self.tags:
            return [sanitize_for_url(tag) for tag in self.tags]
        return []

    def sorted_tag_pairs(self) -> list[tuple[str, str]]:
        """Get tags as (display, safe) pairs sorted in casefold alphabetical order."""
        if not self.tags:
            return []
        pairs = [(tag, sanitize_for_url(tag)) for tag in self.tags]
        return sorted(pairs, key=lambda pair: pair[0].casefold())

    @property
    def description(self) -> str:
        """Get the description for the post.

        Returns the description from metadata if present, otherwise
        extracts and returns the first paragraph from the content.

        Returns:
            The post description as a string
        """
        if self.metadata and self.metadata.get("description"):
            return str(self.metadata.get("description"))
        return extract_first_paragraph(self.content)

    @property
    def reading_time(self) -> int:
        """Calculate the estimated reading time for this post in whole minutes.

        Returns:
            Estimated reading time in minutes (minimum 1 minute)
        """
        return calculate_reading_time(self.content, self.words_per_minute)

    @property
    def modified_date(self) -> dt.datetime | None:
        """Get the modified date as a datetime object.

        Parses the `modified` field from metadata into a proper datetime,
        handling datetime objects returned by the YAML parser as well as raw
        strings in common date formats.

        Returns:
            The modified datetime, or None if not set in metadata
        """
        if not self.metadata:
            return None
        modified = self.metadata.get("modified")
        if modified is None:
            return None
        if isinstance(modified, dt.datetime):
            return modified
        if isinstance(modified, dt.date):
            return dt.datetime.combine(modified, dt.time())
        if isinstance(modified, str):
            for fmt in _DATE_FORMATS:
                try:
                    return dt.datetime.strptime(modified, fmt)
                except ValueError:
                    continue
            try:
                return dateutil_parser.parse(modified)
            except ValueError:
                pass
        return None


def post_sort_key(post: Post) -> float:
    """Compute a sort key for a post based on its date.

    Posts without dates sort to the end (key value 0.0). Timezone-aware
    and naive datetimes are both converted to a UTC timestamp for comparison.

    Args:
        post: The post to compute a sort key for

    Returns:
        A float sort key derived from the post date
    """
    if post.date is None:
        return 0.0
    if post.date.tzinfo:
        return post.date.timestamp()
    return post.date.replace(tzinfo=dt.UTC).timestamp()


@dataclass
class Page:
    """Represents a static page with metadata and content."""

    path: Path
    title: str
    content: str
    html_content: str
    metadata: dict[str, Any] | None = None
    url_path: str | None = field(default=None, repr=False, compare=False)

    @property
    def slug(self) -> str:
        """Generate a URL slug from the page filename."""
        return self.path.stem

    @property
    def url(self) -> str:
        """Generate the URL path for the page.

        If the generator has resolved a custom URL via the `page_path`
        configuration option it will be stored in `url_path` and returned
        directly.  Otherwise the URL is derived from the page slug using the
        default `/{slug}.html` scheme.

        Returns:
            The URL path for the page, always beginning with `/`.
        """
        if self.url_path is not None:
            return self.url_path
        return f"/{self.slug}.html"

    @property
    def description(self) -> str:
        """Get the description for the page.

        Returns the description from metadata if present, otherwise
        extracts and returns the first paragraph from the content.

        Returns:
            The page description as a string
        """
        if self.metadata and self.metadata.get("description"):
            return str(self.metadata.get("description"))
        return extract_first_paragraph(self.content)


class PostParser:
    """Parse markdown files with frontmatter into Post objects."""

    def __init__(self, site_url: str | None = None) -> None:
        """Initialize the parser with markdown extensions.

        Args:
            site_url: Optional base URL of the site for determining internal vs external links
        """
        self.markdown = markdown.Markdown(
            extensions=[
                "attr_list",
                "fenced_code",
                "codehilite",
                "tables",
                "toc",
                "footnotes",
                *create_custom_extensions(site_url=site_url or ""),
            ],
            extension_configs={
                "codehilite": {
                    "css_class": "highlight",
                    "guess_lang": False,
                    "use_pygments": True,
                    "pygments_formatter": _LangAwareHtmlFormatter,
                },
                "footnotes": {
                    "UNIQUE_IDS": True,
                },
            },
        )

    def _load_frontmatter(
        self, path: Path, content_type: str = "file"
    ) -> frontmatter.Post:
        """Load and parse frontmatter from a markdown file.

        Args:
            path: Path to the markdown file
            content_type: Human-readable description of the file type (e.g. "post"
                          or "page"), used in error messages

        Returns:
            Parsed frontmatter post object

        Raises:
            ValueError: If the frontmatter YAML is malformed
        """
        try:
            return frontmatter.load(path)
        except yaml.scanner.ScannerError as e:
            raise ValueError(
                f"YAML syntax error in frontmatter of {path}:\n"
                f"  {e}\n\n"
                f"Common causes:\n"
                f"  - Unquoted colons in values "
                f"(e.g., 'title: My {content_type}: the sequel')\n"
                f"  - Missing quotes around special characters\n"
                f"  - Incorrect indentation\n\n"
                f"Fix: Wrap values containing colons or special characters in quotes:\n"
                f'  title: "My {content_type}: the sequel"'
            ) from e
        except Exception as e:
            raise ValueError(f"Error parsing frontmatter in {path}: {e}") from e

    def _extract_title(
        self, metadata: dict[str, Any], path: Path, content_type: str
    ) -> str:
        """Extract and validate the title from frontmatter metadata.

        Args:
            metadata: Frontmatter metadata dictionary.
            path: Path to the markdown file (for error messages).
            content_type: Human-readable description of the file type (e.g. "post"
                          or "page").

        Returns:
            The validated title string.

        Raises:
            ValueError: If the title is missing or not a string.
        """
        title = metadata.get("title")
        if not title:
            raise ValueError(
                f"{content_type.capitalize()} missing required 'title' in frontmatter: {path}"
            )
        if not isinstance(title, str):
            raise ValueError(
                f"{content_type.capitalize()} 'title' in frontmatter must be a string in: {path}\n"
                f"  Found: {title!r} (type: {type(title).__name__})\n"
                f"  Fix: wrap the value in quotes, e.g.  title: 'My Title'"
            )
        return title

    def _extract_date(self, metadata: dict[str, Any]) -> dt.datetime | None:
        """Extract and parse the publication date from frontmatter metadata.

        Args:
            metadata: Frontmatter metadata dictionary.

        Returns:
            The parsed datetime object, or None if no date was provided.
        """
        if "date" not in metadata:
            return None
        date_value = metadata["date"]
        if isinstance(date_value, dt.datetime):
            return date_value
        if isinstance(date_value, dt.date):
            return dt.datetime.combine(date_value, dt.time())
        if isinstance(date_value, str):
            for fmt in _DATE_FORMATS:
                try:
                    return dt.datetime.strptime(date_value, fmt)
                except ValueError:
                    continue
            try:
                return dateutil_parser.parse(date_value)
            except ValueError:
                pass
        return None

    def _extract_category(self, metadata: dict[str, Any]) -> str | None:
        """Extract the category from frontmatter metadata.

        Args:
            metadata: Frontmatter metadata dictionary.

        Returns:
            The category string (stripped), or None if no category was provided.
        """
        raw_category = metadata.get("category")
        if raw_category is not None:
            return str(raw_category).strip() or None
        return None

    def _extract_tags(self, metadata: dict[str, Any], path: Path) -> list[str]:
        """Extract and validate the tags from frontmatter metadata.

        Args:
            metadata: Frontmatter metadata dictionary.
            path: Path to the markdown file (for error messages).

        Returns:
            A list of tag strings.

        Raises:
            ValueError: If tags are present but in an invalid format.
        """
        raw_tags = metadata.get("tags", [])
        if raw_tags is None:
            return []
        if isinstance(raw_tags, str):
            return [tag.strip() for tag in raw_tags.split(",")]
        if isinstance(raw_tags, list):
            return [str(tag).strip() for tag in raw_tags]
        raise ValueError(
            f"Post 'tags' in frontmatter must be a string or list in: {path}\n"
            f"  Found: {raw_tags!r} (type: {type(raw_tags).__name__})\n"
            f"  Fix: wrap the value in quotes or brackets, e.g. "
            f" tags: 'my-tag'  or  tags: [tag1, tag2]"
        )

    def parse_file(self, path: Path) -> Post:
        """Parse a markdown file with frontmatter.

        Args:
            path: Path to the markdown file

        Returns:
            A Post object with parsed metadata and content

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If required metadata is missing or YAML is malformed
        """
        if not path.exists():
            raise FileNotFoundError(f"Post file not found: {path}")

        # Parse frontmatter
        post_data = self._load_frontmatter(path, content_type="post")
        metadata = dict(post_data.metadata)

        # Extract and validate metadata
        title = self._extract_title(metadata, path, "post")
        date = self._extract_date(metadata)
        category = self._extract_category(metadata)
        tags = self._extract_tags(metadata, path)
        draft = metadata.get("draft", False)

        # Convert markdown to HTML
        html_content = self.markdown.convert(post_data.content)

        # Reset markdown parser for next use
        self.markdown.reset()

        return Post(
            path=path,
            title=title,
            content=post_data.content,
            html_content=html_content,
            date=date,
            category=category,
            tags=tags,
            draft=draft,
            metadata=dict(post_data.metadata),
        )

    def parse_directory(
        self,
        directory: Path,
        include_drafts: bool = False,
        exclude_dirs: list[Path] | None = None,
    ) -> list[Post]:
        """Parse all markdown files in a directory.

        Args:
            directory: Directory containing markdown files
            include_drafts: Whether to include posts marked as drafts
            exclude_dirs: Optional list of subdirectories to exclude from scanning

        Returns:
            List of Post objects sorted by date (newest first)
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        resolved_exclude_dirs = [d.resolve() for d in (exclude_dirs or [])]

        posts = []
        for md_file in directory.rglob("*.md"):
            if any(
                md_file.resolve().is_relative_to(excluded)
                for excluded in resolved_exclude_dirs
            ):
                continue
            try:
                post = self.parse_file(md_file)
                if not post.draft or include_drafts:
                    posts.append(post)
            except (ValueError, FileNotFoundError) as e:
                print(f"Warning: Skipping {md_file}: {e}")
                continue

        # Sort by date (newest first)
        posts.sort(key=post_sort_key, reverse=True)
        return posts

    def parse_page(self, path: Path) -> Page:
        """Parse a markdown file as a static page.

        Args:
            path: Path to the markdown file

        Returns:
            A Page object with parsed metadata and content

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If required metadata is missing or YAML is malformed
        """
        if not path.exists():
            raise FileNotFoundError(f"Page file not found: {path}")

        # Parse frontmatter
        page_data = self._load_frontmatter(path, content_type="page")
        metadata = dict(page_data.metadata)

        # Extract and validate metadata
        title = self._extract_title(metadata, path, "page")

        # Convert markdown to HTML
        html_content = self.markdown.convert(page_data.content)

        # Reset markdown parser for next use
        self.markdown.reset()

        return Page(
            path=path,
            title=title,
            content=page_data.content,
            html_content=html_content,
            metadata=dict(page_data.metadata),
        )

    def parse_pages_directory(self, directory: Path) -> list[Page]:
        """Parse all markdown files in a pages directory.

        The special file `404.md` is excluded from the returned list; use
        `blogmore.parser.parse_404_page` to obtain it separately.

        Args:
            directory: Directory containing page markdown files

        Returns:
            List of Page objects sorted by title (alphabetically)
        """
        if not directory.exists():
            return []

        pages = []
        for md_file in directory.glob("*.md"):
            if md_file.name == CUSTOM_404_MARKDOWN:
                continue
            try:
                page = self.parse_page(md_file)
                pages.append(page)
            except (ValueError, FileNotFoundError) as e:
                print(f"Warning: Skipping {md_file}: {e}")
                continue

        # Sort by title (alphabetically)
        pages.sort(key=lambda page: page.title.lower())
        return pages

    def parse_404_page(self, directory: Path) -> Page | None:
        """Parse the optional custom 404 page from a pages directory.

        Args:
            directory: Directory that may contain a `404.md` file

        Returns:
            A Page object if `404.md` exists and parses successfully,
            otherwise `None`
        """
        path = directory / CUSTOM_404_MARKDOWN
        if not path.exists():
            return None
        try:
            return self.parse_page(path)
        except (ValueError, FileNotFoundError) as e:
            print(f"Warning: Skipping {path}: {e}")
            return None
