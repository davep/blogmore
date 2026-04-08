"""Calendar view data structures for blog post history."""

##############################################################################
# Python imports.
import calendar as cal_module
import datetime as dt
from dataclasses import dataclass

##############################################################################
# Local imports.
from blogmore.parser import Post


@dataclass
class CalendarDay:
    """Represents a single day cell in the calendar grid.

    A day cell may be a real date within the current month, or a padding
    cell (``date is None``) for the blank slots before the first and after
    the last day of the month.
    """

    date: dt.date | None
    """The calendar date for this cell.

    ``None`` for padding slots that do not belong to the current month.
    """

    post_count: int = 0
    """Number of posts published on this day."""

    day_url: str | None = None
    """URL for the daily archive page.

    Set only when ``post_count > 0``; ``None`` for padding cells and days
    with no posts.
    """


@dataclass
class CalendarMonth:
    """Represents a single month in the calendar view."""

    year: int
    """The year this month belongs to."""

    month: int
    """The month number (1–12)."""

    month_name: str
    """Full name of the month (e.g. ``"January"``)."""

    month_url: str | None
    """URL linking to the monthly archive.

    ``None`` when the month has no posts.
    """

    has_posts: bool
    """Whether any posts were published in this month."""

    weeks: list[list[CalendarDay]]
    """Calendar grid rows.

    Each row contains exactly seven :class:`CalendarDay` items in
    Monday-to-Sunday order.
    """


@dataclass
class CalendarYear:
    """Represents a single year in the calendar view."""

    year: int
    """The calendar year."""

    year_url: str | None
    """URL linking to the yearly archive.

    ``None`` when the year has no posts.
    """

    has_posts: bool
    """Whether any posts were published in this year."""

    months: list[CalendarMonth]
    """Months for this year in reverse chronological order (latest first)."""


def build_calendar(
    posts: list[Post],
    page1_suffix: str,
) -> list[CalendarYear]:
    """Build the calendar data structure from a list of posts.

    Constructs a reverse-chronological list of :class:`CalendarYear` objects,
    each containing months in reverse order, spanning from the date of the
    first post to the date of the latest post.

    Args:
        posts: All published posts to include in the calendar.
        page1_suffix: The URL suffix for the first pagination page (e.g.
            ``"index.html"`` or ``""`` for clean URLs).

    Returns:
        A list of :class:`CalendarYear` objects in reverse chronological
        order (most recent year first).  Returns an empty list when *posts*
        is empty or no posts have a date.
    """
    dated_posts = [p for p in posts if p.date is not None]
    if not dated_posts:
        return []

    # Build a map of date → post count.
    post_counts: dict[dt.date, int] = {}
    for post in dated_posts:
        assert post.date is not None  # narrowing for mypy
        date = post.date.date()
        post_counts[date] = post_counts.get(date, 0) + 1

    # Determine the overall date span.
    all_dates = sorted(post_counts.keys())
    first_date = all_dates[0]
    last_date = all_dates[-1]

    first_year, first_month = first_date.year, first_date.month
    last_year, last_month = last_date.year, last_date.month

    # Pre-compute sets of month/year tuples that have at least one post.
    months_with_posts: set[tuple[int, int]] = set()
    years_with_posts: set[int] = set()
    for date in post_counts:
        months_with_posts.add((date.year, date.month))
        years_with_posts.add(date.year)

    # Use a Calendar fixed to Monday so the grid is locale-independent.
    month_calendar = cal_module.Calendar(firstweekday=0)

    years: list[CalendarYear] = []

    for year in range(last_year, first_year - 1, -1):
        # Determine the month range to include for this year.
        if year == last_year and year == first_year:
            year_last_month = last_month
            year_first_month = first_month
        elif year == last_year:
            year_last_month = last_month
            year_first_month = 1
        elif year == first_year:
            year_last_month = 12
            year_first_month = first_month
        else:
            year_last_month = 12
            year_first_month = 1

        year_has_posts = year in years_with_posts
        year_url: str | None = f"/{year}/{page1_suffix}" if year_has_posts else None

        months: list[CalendarMonth] = []

        for month in range(year_last_month, year_first_month - 1, -1):
            month_has_posts = (year, month) in months_with_posts
            month_name = dt.date(year, month, 1).strftime("%B")
            month_url: str | None = (
                f"/{year}/{month:02d}/{page1_suffix}" if month_has_posts else None
            )

            # Build the week grid.  ``monthdayscalendar`` returns weeks in
            # forward order; reverse them so the most recent week appears at
            # the top of the month block (consistent with the overall
            # reverse-chronological ordering of the calendar).
            raw_weeks = list(reversed(month_calendar.monthdayscalendar(year, month)))
            weeks: list[list[CalendarDay]] = []

            for raw_week in raw_weeks:
                week: list[CalendarDay] = []
                for day_num in raw_week:
                    if day_num == 0:
                        week.append(CalendarDay(date=None))
                    else:
                        date = dt.date(year, month, day_num)
                        count = post_counts.get(date, 0)
                        day_url: str | None = (
                            f"/{year}/{month:02d}/{day_num:02d}/{page1_suffix}"
                            if count > 0
                            else None
                        )
                        week.append(
                            CalendarDay(date=date, post_count=count, day_url=day_url)
                        )
                weeks.append(week)

            months.append(
                CalendarMonth(
                    year=year,
                    month=month,
                    month_name=month_name,
                    month_url=month_url,
                    has_posts=month_has_posts,
                    weeks=weeks,
                )
            )

        years.append(
            CalendarYear(
                year=year,
                year_url=year_url,
                has_posts=year_has_posts,
                months=months,
            )
        )

    return years


### calendar.py ends here
