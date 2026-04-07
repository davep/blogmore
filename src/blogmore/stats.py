"""Blog statistics computation for blogmore."""

##############################################################################
# Python imports.
import datetime as dt
import re
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urlparse

##############################################################################
# Local imports.
from blogmore.parser import Post
from blogmore.utils import count_words


@dataclass
class StreakChartCell:
    """A single cell in the posting-streak chart grid.

    Attributes:
        date: The calendar date this cell represents.
        count: Number of posts published on this date.
        in_window: Whether this date falls within the 365-day window.
            Cells outside the window are rendered as empty/dimmed spacers.
    """

    date: dt.date
    """The calendar date this cell represents."""

    count: int
    """Number of posts published on this date."""

    in_window: bool
    """Whether this date falls within the 365-day window."""


##############################################################################
# Day-of-week labels (Sunday first, used in the streak chart rows).
STREAK_DOW_LABELS: list[str] = [
    "Sun",
    "Mon",
    "Tue",
    "Wed",
    "Thu",
    "Fri",
    "Sat",
]

##############################################################################
# Day-of-week labels (Monday first, matching datetime.weekday() → 0=Mon).
WEEKDAY_LABELS: list[str] = [
    "Mon",
    "Tue",
    "Wed",
    "Thu",
    "Fri",
    "Sat",
    "Sun",
]

##############################################################################
# Month labels.
MONTH_LABELS: list[str] = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


@dataclass
class BlogStats:
    """Aggregated statistics for a collection of blog posts.

    All histogram counts are fixed-length lists indexed from zero:

    * ``posts_per_hour`` — 24 elements, index 0 = midnight hour.
    * ``posts_per_weekday`` — 7 elements, index 0 = Monday.
    * ``posts_per_month`` — 12 elements, index 0 = January.

    Posts without a date are excluded from date-based statistics.
    Posts without any content contribute zero to word-count statistics.
    """

    posts_per_hour: list[int] = field(default_factory=lambda: [0] * 24)
    """Count of posts grouped by the hour (0-23) at which they were published."""

    posts_per_weekday: list[int] = field(default_factory=lambda: [0] * 7)
    """Count of posts grouped by day of week (0 = Monday, 6 = Sunday)."""

    posts_per_month: list[int] = field(default_factory=lambda: [0] * 12)
    """Count of posts grouped by month (0 = January, 11 = December)."""

    avg_word_count: float = 0.0
    """Average word count across all posts."""

    min_word_count: int = 0
    """Minimum word count among all posts."""

    max_word_count: int = 0
    """Maximum word count among all posts."""

    min_word_count_post: Post | None = None
    """Post with the fewest words."""

    max_word_count_post: Post | None = None
    """Post with the most words."""

    avg_reading_time: float = 0.0
    """Average estimated reading time in minutes across all posts."""

    min_reading_time: int = 0
    """Minimum estimated reading time in minutes."""

    max_reading_time: int = 0
    """Maximum estimated reading time in minutes."""

    min_reading_time_post: Post | None = None
    """Post with the shortest estimated reading time."""

    max_reading_time_post: Post | None = None
    """Post with the longest estimated reading time."""

    earliest_post_date: dt.datetime | None = None
    """Date of the oldest published post."""

    latest_post_date: dt.datetime | None = None
    """Date of the most recently published post."""

    earliest_post: Post | None = None
    """The oldest published post."""

    latest_post: Post | None = None
    """The most recently published post."""

    tag_count: int = 0
    """Number of distinct tags used across all posts."""

    category_count: int = 0
    """Number of distinct categories used across all posts."""

    unique_external_link_count: int = 0
    """Number of unique external URLs referenced across all posts."""

    top_domains: list[tuple[str, int]] = field(default_factory=list)
    """Top 20 externally-linked domains as ``(domain, count)`` pairs.

    Sorted by count descending.
    """

    posts_in_last_year: int = 0
    """Total number of posts published in the last 365 days (inclusive of today)."""

    streak_weeks: list[list[StreakChartCell | None]] = field(default_factory=list)
    """Streak chart data for the last 365 days.

    A list of week columns, ordered oldest to newest (left → right).  Each
    column is a list of exactly 7 entries ordered Sunday-first (index 0 =
    Sunday, index 6 = Saturday).  An entry is ``None`` when the slot falls
    outside the 365-day window (i.e. the leading or trailing partial weeks).
    """

    @property
    def blog_span_days(self) -> int | None:
        """Return the total span of the blog in days, or ``None`` if fewer than two dated posts exist.

        Returns:
            Number of days between the earliest and latest post dates, or
            ``None`` when fewer than two dated posts exist.
        """
        if self.earliest_post_date is None or self.latest_post_date is None:
            return None
        delta = self.latest_post_date - self.earliest_post_date
        return delta.days


def _extract_external_links(html_content: str, site_url: str) -> list[str]:
    """Extract all external URLs referenced in an HTML fragment.

    Finds every ``href`` attribute value inside anchor tags and filters out
    URLs that point to the same site (as determined by *site_url*).

    Args:
        html_content: The HTML content of a post.
        site_url: The configured base URL of the blog site (may be empty).

    Returns:
        A list of external URL strings found in the content.
    """
    site_domain: str | None = None
    if site_url:
        parsed_site = urlparse(site_url)
        site_domain = parsed_site.netloc.lower() or None

    external_urls: list[str] = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', html_content):
        # Skip anchors, root-relative and relative paths.
        if href.startswith(("/", "#")) or not href:
            continue
        parsed = urlparse(href)
        if not parsed.scheme and not parsed.netloc:
            continue
        if site_domain:
            link_domain = parsed.netloc.lower()
            if link_domain == site_domain or link_domain == f"www.{site_domain}":
                continue
        external_urls.append(href)
    return external_urls


def compute_blog_stats(posts: list[Post], site_url: str = "") -> BlogStats:
    """Compute aggregated statistics from a collection of blog posts.

    Args:
        posts: The list of posts to compute statistics for.
        site_url: The configured base URL of the blog site.  Used to
            distinguish internal from external links.  May be empty.

    Returns:
        A :class:`BlogStats` instance populated from the given posts.
    """
    stats = BlogStats()

    # --- Date-based histograms -----------------------------------------------
    dated_posts = [post for post in posts if post.date is not None]
    for post in dated_posts:
        assert post.date is not None
        stats.posts_per_hour[post.date.hour] += 1
        stats.posts_per_weekday[post.date.weekday()] += 1
        stats.posts_per_month[post.date.month - 1] += 1

    # --- Blog time span -------------------------------------------------------
    if dated_posts:
        # Normalise to naive datetimes for comparison across tz-aware / naive.
        def _to_naive(date: dt.datetime) -> dt.datetime:
            if date.tzinfo is not None:
                return date.astimezone(dt.UTC).replace(tzinfo=None)
            return date

        naive_dated = [(post, _to_naive(post.date)) for post in dated_posts]  # type: ignore[arg-type]
        earliest_pair = min(naive_dated, key=lambda pair: pair[1])
        latest_pair = max(naive_dated, key=lambda pair: pair[1])
        stats.earliest_post = earliest_pair[0]
        stats.latest_post = latest_pair[0]
        stats.earliest_post_date = earliest_pair[0].date
        stats.latest_post_date = latest_pair[0].date
        # Ensure they're stored as naive datetimes for consistent rendering.
        if (
            stats.earliest_post_date is not None
            and stats.earliest_post_date.tzinfo is not None
        ):
            stats.earliest_post_date = _to_naive(stats.earliest_post_date)
        if (
            stats.latest_post_date is not None
            and stats.latest_post_date.tzinfo is not None
        ):
            stats.latest_post_date = _to_naive(stats.latest_post_date)

    # --- Word count and reading time -----------------------------------------
    word_counts = [(post, count_words(post.content)) for post in posts]
    reading_times = [(post, post.reading_time) for post in posts]

    if word_counts:
        total_words = sum(wc for _, wc in word_counts)
        stats.avg_word_count = total_words / len(word_counts)
        min_wc_post, min_wc = min(word_counts, key=lambda pair: pair[1])
        max_wc_post, max_wc = max(word_counts, key=lambda pair: pair[1])
        stats.min_word_count = min_wc
        stats.max_word_count = max_wc
        stats.min_word_count_post = min_wc_post
        stats.max_word_count_post = max_wc_post

    if reading_times:
        total_time = sum(rt for _, rt in reading_times)
        stats.avg_reading_time = total_time / len(reading_times)
        min_rt_post, min_rt = min(reading_times, key=lambda pair: pair[1])
        max_rt_post, max_rt = max(reading_times, key=lambda pair: pair[1])
        stats.min_reading_time = min_rt
        stats.max_reading_time = max_rt
        stats.min_reading_time_post = min_rt_post
        stats.max_reading_time_post = max_rt_post

    # --- Tags and categories --------------------------------------------------
    all_tags: set[str] = set()
    all_categories: set[str] = set()
    for post in posts:
        if post.tags:
            all_tags.update(post.tags)
        if post.category:
            all_categories.add(post.category)
    stats.tag_count = len(all_tags)
    stats.category_count = len(all_categories)

    # --- External links -------------------------------------------------------
    all_external_urls: set[str] = set()
    domain_counter: Counter[str] = Counter()
    for post in posts:
        for url in _extract_external_links(post.html_content, site_url):
            all_external_urls.add(url)
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain:
                domain_counter[domain] += 1
    stats.unique_external_link_count = len(all_external_urls)
    stats.top_domains = domain_counter.most_common(20)

    # --- Streak chart (last 365 days) ----------------------------------------
    today = dt.date.today()
    window_start = today - dt.timedelta(days=364)  # 365 days inclusive of today

    # Tally posts that fall within the window.
    posts_by_date: dict[dt.date, int] = {}
    for post in dated_posts:
        assert post.date is not None
        # Normalise timezone-aware datetimes to UTC before extracting date.
        post_dt = post.date
        if post_dt.tzinfo is not None:
            post_dt = post_dt.astimezone(dt.UTC).replace(tzinfo=None)
        post_date = post_dt.date()
        if window_start <= post_date <= today:
            posts_by_date[post_date] = posts_by_date.get(post_date, 0) + 1

    stats.posts_in_last_year = sum(posts_by_date.values())

    # Extend the grid to full weeks: start on the Sunday on or before
    # window_start, end on the Saturday on or after today.
    # isoweekday(): Mon=1 … Sun=7.  We want Sun=0, Mon=1, …, Sat=6.
    dow_of_window_start = window_start.isoweekday() % 7  # Sun→0, Mon→1, …
    grid_start = window_start - dt.timedelta(days=dow_of_window_start)

    dow_of_today = today.isoweekday() % 7
    days_to_saturday = (6 - dow_of_today) % 7
    grid_end = today + dt.timedelta(days=days_to_saturday)

    weeks: list[list[StreakChartCell | None]] = []
    current_sunday = grid_start
    while current_sunday <= grid_end:
        week: list[StreakChartCell | None] = []
        for day_offset in range(7):
            day = current_sunday + dt.timedelta(days=day_offset)
            if window_start <= day <= today:
                week.append(
                    StreakChartCell(
                        date=day,
                        count=posts_by_date.get(day, 0),
                        in_window=True,
                    )
                )
            else:
                week.append(None)
        weeks.append(week)
        current_sunday += dt.timedelta(days=7)

    stats.streak_weeks = weeks

    return stats


### stats.py ends here
