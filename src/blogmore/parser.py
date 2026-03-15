"""Markdown parser with frontmatter support for blog posts."""

import concurrent.futures
import datetime as dt
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frontmatter  # type: ignore[import-untyped]
import markdown
import yaml

from blogmore.admonitions import AdmonitionsExtension
from blogmore.external_links import ExternalLinksExtension
from blogmore.heading_anchors import HeadingAnchorsExtension
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


def extract_first_paragraph(content: str) -> str:
    """Extract the first paragraph from markdown content.

    Skips images and empty lines to find the first text paragraph.
    Removes markdown formatting for a clean description.

    Args:
        content: The markdown content to extract from

    Returns:
        The first paragraph as plain text, or empty string if none found
    """
    lines = content.strip().split("\n")
    paragraph_lines: list[str] = []
    in_paragraph = False

    for line in lines:
        stripped = line.strip()

        # Skip empty lines before we start collecting
        if not in_paragraph and not stripped:
            continue

        # Skip image syntax (markdown images, linked images, and HTML img tags)
        if stripped.startswith(("![", "[![", "<img")):
            continue

        # If we hit a heading, code block, or other special syntax, stop if we have content
        if stripped.startswith(("#", "```", "---")):
            if paragraph_lines:
                break
            continue

        # If we have an empty line and we're in a paragraph, we've reached the end
        if not stripped and in_paragraph:
            break

        # If we have content, add it
        if stripped:
            in_paragraph = True
            paragraph_lines.append(stripped)

    # Join the lines and clean up markdown formatting
    paragraph = " ".join(paragraph_lines)

    # Remove common markdown formatting
    # Remove links but keep text: [text](url) -> text
    paragraph = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", paragraph)
    # Remove bold/italic: **text** or *text* -> text
    paragraph = re.sub(r"\*\*([^\*]+)\*\*", r"\1", paragraph)
    paragraph = re.sub(r"\*([^\*]+)\*", r"\1", paragraph)
    # Remove inline code: `code` -> code
    paragraph = re.sub(r"`([^`]+)`", r"\1", paragraph)

    return paragraph.strip()


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

    @property
    def slug(self) -> str:
        """Generate a URL slug from the post filename."""
        return self.path.stem

    @property
    def url(self) -> str:
        """Generate the URL path for the post.

        If the generator has resolved a custom URL via the ``post_path``
        configuration option it will be stored in ``url_path`` and returned
        directly.  Otherwise the URL is derived from the post date and slug
        using the default ``/{year}/{month}/{day}/{slug}.html`` scheme.

        Returns:
            The URL path for the post, always beginning with ``/``.
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
        return calculate_reading_time(self.content)

    @property
    def modified_date(self) -> dt.datetime | None:
        """Get the modified date as a datetime object.

        Parses the ``modified`` field from metadata into a proper datetime,
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
                from dateutil import parser as dateutil_parser

                return dateutil_parser.parse(modified)
            except (ImportError, ValueError):
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

    @property
    def slug(self) -> str:
        """Generate a URL slug from the page filename."""
        return self.path.stem

    @property
    def url(self) -> str:
        """Generate the URL path for the page."""
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
        self._site_url = site_url or ""
        self._thread_local: threading.local = threading.local()
        # Prime the main thread's markdown instance eagerly so that
        # `parser.markdown` continues to work in existing sequential code.
        self._thread_local.markdown = self._make_markdown_instance()

    def _make_markdown_instance(self) -> markdown.Markdown:
        """Create a fresh, fully-configured :class:`markdown.Markdown` processor.

        Each call returns an independent instance so that the processor can
        safely be used concurrently across multiple threads.

        Returns:
            A new Markdown processor with all required extensions registered.
        """
        external_links_ext = ExternalLinksExtension(site_url=self._site_url)
        admonitions_ext = AdmonitionsExtension()
        heading_anchors_ext = HeadingAnchorsExtension()

        return markdown.Markdown(
            extensions=[
                "meta",
                "attr_list",
                "fenced_code",
                "codehilite",
                "tables",
                "toc",
                "footnotes",
                admonitions_ext,
                external_links_ext,
                heading_anchors_ext,
            ],
            extension_configs={
                "codehilite": {
                    "css_class": "highlight",
                    "guess_lang": False,
                    "use_pygments": True,
                },
                "footnotes": {
                    "UNIQUE_IDS": True,
                },
            },
        )

    @property
    def markdown(self) -> markdown.Markdown:
        """Return the thread-local :class:`markdown.Markdown` processor.

        Each thread receives its own independent instance so that concurrent
        calls to :meth:`parse_file` and :meth:`parse_page` cannot interfere
        with each other.

        Returns:
            The Markdown processor for the calling thread.
        """
        if not hasattr(self._thread_local, "markdown"):
            self._thread_local.markdown = self._make_markdown_instance()
        return self._thread_local.markdown  # type: ignore[no-any-return]

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

        # Extract metadata
        title = post_data.get("title")
        if not title:
            raise ValueError(f"Post missing required 'title' in frontmatter: {path}")
        if not isinstance(title, str):
            raise ValueError(
                f"Post 'title' in frontmatter must be a string in: {path}\n"
                f"  Found: {title!r} (type: {type(title).__name__})\n"
                f"  Fix: wrap the value in quotes, e.g.  title: 'My Post Title'"
            )

        # Parse date if present
        date = None
        if "date" in post_data:
            date_value = post_data["date"]
            if isinstance(date_value, dt.datetime):
                date = date_value
            elif isinstance(date_value, dt.date):
                # Convert date to datetime
                date = dt.datetime.combine(date_value, dt.time())
            elif isinstance(date_value, str):
                # Try to parse common date formats, including timezone-aware formats
                for fmt in _DATE_FORMATS:
                    try:
                        date = dt.datetime.strptime(date_value, fmt)
                        break
                    except ValueError:
                        continue

                # If we still couldn't parse it, try with python-dateutil if available
                if date is None:
                    try:
                        from dateutil import parser as dateutil_parser

                        date = dateutil_parser.parse(date_value)
                    except (ImportError, ValueError):
                        pass

        # Extract category - coerce to str in case YAML parsed it as a non-string
        # (e.g. `category: 2024` is parsed as int by the YAML parser)
        raw_category = post_data.get("category")
        if raw_category is not None:
            category: str | None = str(raw_category).strip() or None
        else:
            category = None

        # Extract tags - coerce each item to str in case YAML parsed numeric
        # values as int (e.g. `tags: [2024, python]` gives [2024, "python"]).
        # A bare scalar (e.g. `tags: +3` parsed as int 3) is not iterable and
        # must be caught explicitly with a helpful error rather than letting
        # Python raise "'int' object is not iterable".
        # A bare `tags:` with no value is parsed by YAML as None; treat it as
        # an empty list (no tags).
        raw_tags = post_data.get("tags", [])
        if raw_tags is None:
            tags: list[str] = []
        elif isinstance(raw_tags, str):
            tags = [tag.strip() for tag in raw_tags.split(",")]
        elif isinstance(raw_tags, list):
            tags = [str(tag).strip() for tag in raw_tags]
        else:
            raise ValueError(
                f"Post 'tags' in frontmatter must be a string or list in: {path}\n"
                f"  Found: {raw_tags!r} (type: {type(raw_tags).__name__})\n"
                f"  Fix: wrap the value in quotes or brackets, e.g. "
                f" tags: 'my-tag'  or  tags: [tag1, tag2]"
            )

        # Check draft status
        draft = post_data.get("draft", False)

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
        parallel: bool = False,
        max_workers: int | None = None,
    ) -> list[Post]:
        """Parse all markdown files in a directory.

        Args:
            directory: Directory containing markdown files
            include_drafts: Whether to include posts marked as drafts
            exclude_dirs: Optional list of subdirectories to exclude from scanning
            parallel: When ``True``, parse files concurrently using a process pool.
            max_workers: Maximum number of worker processes when ``parallel`` is
                ``True``.  ``None`` lets Python choose a sensible default.

        Returns:
            List of Post objects sorted by date (newest first)
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        resolved_exclude_dirs = [d.resolve() for d in (exclude_dirs or [])]

        md_files = [
            md_file
            for md_file in directory.rglob("*.md")
            if not any(
                md_file.resolve().is_relative_to(excluded)
                for excluded in resolved_exclude_dirs
            )
        ]

        posts: list[Post] = []

        if parallel and len(md_files) > 1:
            errors: list[tuple[Path, Exception]] = []
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=max_workers,
                initializer=_init_parser_worker,
                initargs=(self._site_url,),
            ) as executor:
                future_to_path = {
                    executor.submit(_parse_file_worker, md_file): md_file
                    for md_file in md_files
                }
                for future in concurrent.futures.as_completed(future_to_path):
                    md_file = future_to_path[future]
                    try:
                        post = future.result()
                        if not post.draft or include_drafts:
                            posts.append(post)
                    except (ValueError, FileNotFoundError) as exc:
                        print(f"Warning: Skipping {md_file}: {exc}")
                    except Exception as exc:
                        print(f"Warning: Skipping {md_file}: {exc}")
                        errors.append((md_file, exc))
            if errors:
                raise RuntimeError(
                    f"Parallel parsing failed for {len(errors)} file(s)"
                ) from errors[0][1]
        else:
            for md_file in md_files:
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

        # Extract metadata
        title = page_data.get("title")
        if not title:
            raise ValueError(f"Page missing required 'title' in frontmatter: {path}")
        if not isinstance(title, str):
            raise ValueError(
                f"Page 'title' in frontmatter must be a string in: {path}\n"
                f"  Found: {title!r} (type: {type(title).__name__})\n"
                f"  Fix: wrap the value in quotes, e.g.  title: 'My Page Title'"
            )

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

        The special file ``404.md`` is excluded from the returned list; use
        :meth:`parse_404_page` to obtain it separately.

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
            directory: Directory that may contain a ``404.md`` file

        Returns:
            A Page object if ``404.md`` exists and parses successfully,
            otherwise ``None``
        """
        path = directory / CUSTOM_404_MARKDOWN
        if not path.exists():
            return None
        try:
            return self.parse_page(path)
        except (ValueError, FileNotFoundError) as e:
            print(f"Warning: Skipping {path}: {e}")
            return None


##############################################################################
# Module-level state and helpers for process-pool parallel parsing.
#
# ProcessPoolExecutor requires picklable callables (module-level functions,
# not bound methods).  A PostParser is created once per worker process via
# the initializer so it need not be pickled for every individual task.

_process_parser: PostParser | None = None


def _init_parser_worker(site_url: str) -> None:
    """Initialise a per-process PostParser for parallel parsing.

    Called exactly once per worker process by
    :class:`~concurrent.futures.ProcessPoolExecutor` before any task runs.

    Args:
        site_url: The site base URL passed to :class:`PostParser`.
    """
    global _process_parser
    _process_parser = PostParser(site_url=site_url)


def _parse_file_worker(path: Path) -> Post:
    """Parse a single Markdown file inside a worker process.

    Uses the per-process :class:`PostParser` created by
    :func:`_init_parser_worker`.

    Args:
        path: Path to the Markdown file to parse.

    Returns:
        The parsed :class:`Post` object.
    """
    assert _process_parser is not None, "Worker process parser not initialised"
    return _process_parser.parse_file(path)
