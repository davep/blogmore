"""Tests for the calendar module."""

import datetime as dt
from pathlib import Path

import pytest

from blogmore.calendar import (
    CalendarDay,
    CalendarMonth,
    CalendarYear,
    build_calendar,
)
from blogmore.parser import Post


def _make_post(year: int, month: int, day: int) -> Post:
    """Create a minimal Post with a specific date.

    Args:
        year: The year for the post date.
        month: The month for the post date.
        day: The day for the post date.

    Returns:
        A Post instance with the given date.
    """
    return Post(
        path=Path(f"post-{year}-{month:02d}-{day:02d}.md"),
        title=f"Post {year}-{month:02d}-{day:02d}",
        content="Some content.",
        html_content="<p>Some content.</p>",
        date=dt.datetime(year, month, day, 10, 0, 0, tzinfo=dt.UTC),
        category="general",
        tags=[],
        draft=False,
        metadata={},
    )


class TestBuildCalendarEmpty:
    """Tests for build_calendar with no posts or undated posts."""

    def test_returns_empty_list_when_no_posts(self) -> None:
        """build_calendar returns an empty list when the posts list is empty."""
        result = build_calendar([], "index.html")
        assert result == []

    def test_returns_empty_list_when_posts_have_no_dates(self) -> None:
        """build_calendar returns an empty list when all posts lack dates."""
        post = Post(
            path=Path("no-date.md"),
            title="No date",
            content=".",
            html_content="<p>.</p>",
            date=None,
            category="general",
            tags=[],
            draft=False,
            metadata={},
        )
        result = build_calendar([post], "index.html")
        assert result == []


class TestBuildCalendarSinglePost:
    """Tests for build_calendar with a single post."""

    def test_single_post_produces_one_year(self) -> None:
        """A single post produces one CalendarYear."""
        post = _make_post(2024, 6, 15)
        result = build_calendar([post], "index.html")
        assert len(result) == 1
        assert result[0].year == 2024

    def test_single_post_year_has_posts(self) -> None:
        """The CalendarYear for a year with posts has has_posts=True."""
        post = _make_post(2024, 6, 15)
        result = build_calendar([post], "index.html")
        assert result[0].has_posts is True

    def test_single_post_year_url(self) -> None:
        """The year_url links to the yearly archive with the page1_suffix."""
        post = _make_post(2024, 6, 15)
        result = build_calendar([post], "index.html")
        assert result[0].year_url == "/2024/index.html"

    def test_single_post_produces_one_month(self) -> None:
        """A single post produces one CalendarMonth."""
        post = _make_post(2024, 6, 15)
        result = build_calendar([post], "index.html")
        year = result[0]
        assert len(year.months) == 1
        assert year.months[0].month == 6

    def test_single_post_month_name(self) -> None:
        """The month_name is the full English month name."""
        post = _make_post(2024, 6, 15)
        result = build_calendar([post], "index.html")
        assert result[0].months[0].month_name == "June"

    def test_single_post_month_url(self) -> None:
        """The month_url links to the monthly archive with the page1_suffix."""
        post = _make_post(2024, 6, 15)
        result = build_calendar([post], "index.html")
        assert result[0].months[0].month_url == "/2024/06/index.html"

    def test_single_post_day_url(self) -> None:
        """The day_url for the post date links to the daily archive."""
        post = _make_post(2024, 6, 15)
        result = build_calendar([post], "index.html")
        month = result[0].months[0]
        # Find the day with post_count > 0
        post_days = [
            day
            for week in month.weeks
            for day in week
            if day.date is not None and day.post_count > 0
        ]
        assert len(post_days) == 1
        assert post_days[0].day_url == "/2024/06/15/index.html"
        assert post_days[0].post_count == 1

    def test_day_title_uses_post_singular(self) -> None:
        """A day with 1 post has post_count=1."""
        post = _make_post(2024, 6, 15)
        result = build_calendar([post], "index.html")
        month = result[0].months[0]
        post_days = [
            day
            for week in month.weeks
            for day in week
            if day.post_count > 0
        ]
        assert post_days[0].post_count == 1

    def test_day_without_posts_has_no_url(self) -> None:
        """A day with no posts has day_url=None."""
        post = _make_post(2024, 6, 15)
        result = build_calendar([post], "index.html")
        month = result[0].months[0]
        no_post_days = [
            day
            for week in month.weeks
            for day in week
            if day.date is not None and day.post_count == 0
        ]
        assert all(day.day_url is None for day in no_post_days)

    def test_padding_days_have_none_date(self) -> None:
        """Padding days (before/after the month) have date=None."""
        post = _make_post(2024, 6, 15)
        result = build_calendar([post], "index.html")
        month = result[0].months[0]
        padding_days = [
            day for week in month.weeks for day in week if day.date is None
        ]
        # June 2024 starts on Saturday, so there are 5 padding days at the start.
        assert len(padding_days) > 0

    def test_each_week_has_seven_days(self) -> None:
        """Each week in a CalendarMonth has exactly 7 CalendarDay entries."""
        post = _make_post(2024, 6, 15)
        result = build_calendar([post], "index.html")
        for week in result[0].months[0].weeks:
            assert len(week) == 7


class TestBuildCalendarMultiplePosts:
    """Tests for build_calendar with multiple posts across months/years."""

    def test_multiple_posts_same_day_count(self) -> None:
        """Multiple posts on the same day are counted correctly."""
        post1 = _make_post(2024, 3, 10)
        post2 = _make_post(2024, 3, 10)
        result = build_calendar([post1, post2], "index.html")
        month = result[0].months[0]
        post_days = [
            day
            for week in month.weeks
            for day in week
            if day.post_count > 0
        ]
        assert len(post_days) == 1
        assert post_days[0].post_count == 2

    def test_reverse_chronological_year_order(self) -> None:
        """Years are listed in reverse chronological order (latest first)."""
        posts = [_make_post(2022, 1, 1), _make_post(2024, 12, 31)]
        result = build_calendar(posts, "index.html")
        years = [y.year for y in result]
        assert years == [2024, 2023, 2022]

    def test_years_without_posts_included_in_span(self) -> None:
        """Years between first and last post with no posts are still included."""
        posts = [_make_post(2022, 1, 1), _make_post(2024, 12, 31)]
        result = build_calendar(posts, "index.html")
        year_nums = {y.year for y in result}
        assert 2023 in year_nums

    def test_year_without_posts_has_no_url(self) -> None:
        """A year with no posts has year_url=None."""
        posts = [_make_post(2022, 1, 1), _make_post(2024, 12, 31)]
        result = build_calendar(posts, "index.html")
        year_2023 = next(y for y in result if y.year == 2023)
        assert year_2023.year_url is None
        assert year_2023.has_posts is False

    def test_reverse_chronological_month_order(self) -> None:
        """Months within a year are listed in reverse chronological order."""
        posts = [_make_post(2024, 1, 5), _make_post(2024, 11, 20)]
        result = build_calendar(posts, "index.html")
        year = result[0]
        assert year.year == 2024
        months = [m.month for m in year.months]
        assert months == list(range(11, 0, -1))

    def test_last_year_starts_at_latest_post_month(self) -> None:
        """The most recent year only includes months up to the latest post."""
        posts = [_make_post(2024, 3, 1)]
        result = build_calendar(posts, "index.html")
        year = result[0]
        months = [m.month for m in year.months]
        assert max(months) == 3

    def test_first_year_ends_at_first_post_month(self) -> None:
        """The oldest year only includes months from the first post onward."""
        posts = [_make_post(2024, 5, 1)]
        result = build_calendar(posts, "index.html")
        year = result[0]
        months = [m.month for m in year.months]
        assert min(months) == 5


class TestBuildCalendarCleanUrls:
    """Tests for build_calendar with various page1_suffix values."""

    def test_page1_suffix_applied_to_day_url(self) -> None:
        """The day_url uses the supplied page1_suffix."""
        post = _make_post(2024, 4, 8)
        result = build_calendar([post], "index.html")
        month = result[0].months[0]
        post_days = [
            day for week in month.weeks for day in week if day.post_count > 0
        ]
        assert post_days[0].day_url == "/2024/04/08/index.html"

    def test_page1_suffix_applied_to_month_url(self) -> None:
        """The month_url uses the supplied page1_suffix."""
        post = _make_post(2024, 4, 8)
        result = build_calendar([post], "index.html")
        assert result[0].months[0].month_url == "/2024/04/index.html"

    def test_page1_suffix_applied_to_year_url(self) -> None:
        """The year_url uses the supplied page1_suffix."""
        post = _make_post(2024, 4, 8)
        result = build_calendar([post], "index.html")
        assert result[0].year_url == "/2024/index.html"

    def test_empty_page1_suffix(self) -> None:
        """An empty page1_suffix (clean URLs) produces trailing-slash-like URLs."""
        post = _make_post(2024, 4, 8)
        result = build_calendar([post], "")
        assert result[0].year_url == "/2024/"
        assert result[0].months[0].month_url == "/2024/04/"
        month = result[0].months[0]
        post_days = [
            day for week in month.weeks for day in week if day.post_count > 0
        ]
        assert post_days[0].day_url == "/2024/04/08/"


class TestBuildCalendarMondayFirst:
    """Tests that the calendar week starts on Monday."""

    def test_first_day_of_week_is_monday(self) -> None:
        """Monday appears in the last column (index 6) because days are reversed.

        January 2024: the 1st is a Monday. Weeks are reversed (most recent
        first) and days within each week are also reversed (Sunday first,
        Monday last), so the last week row's last column should be January 1.
        """
        post = _make_post(2024, 1, 1)
        result = build_calendar([post], "index.html")
        month = result[0].months[0]
        # Weeks are in reverse order (last week first), so the final row
        # contains week 1 of January 2024. Days are also reversed within each
        # week (Sunday first, Monday last), so January 1 (a Monday) appears
        # at column index 6 (the last position) of that final row.
        last_week = month.weeks[-1]
        assert last_week[6].date is not None
        assert last_week[6].date.day == 1


class TestCalendarDataClasses:
    """Tests for CalendarDay, CalendarMonth, and CalendarYear dataclasses."""

    def test_calendar_day_defaults(self) -> None:
        """CalendarDay has sensible defaults for optional fields."""
        day = CalendarDay(date=dt.date(2024, 1, 1))
        assert day.post_count == 0
        assert day.day_url is None

    def test_calendar_day_padding(self) -> None:
        """A padding CalendarDay has date=None."""
        day = CalendarDay(date=None)
        assert day.date is None
        assert day.post_count == 0
        assert day.day_url is None

    def test_calendar_month_fields(self) -> None:
        """CalendarMonth stores all expected fields."""
        month = CalendarMonth(
            year=2024,
            month=3,
            month_name="March",
            month_url="/2024/03/index.html",
            has_posts=True,
            weeks=[],
        )
        assert month.year == 2024
        assert month.month == 3
        assert month.month_name == "March"
        assert month.month_url == "/2024/03/index.html"
        assert month.has_posts is True

    def test_calendar_year_fields(self) -> None:
        """CalendarYear stores all expected fields."""
        year = CalendarYear(
            year=2024,
            year_url="/2024/index.html",
            has_posts=True,
            months=[],
        )
        assert year.year == 2024
        assert year.year_url == "/2024/index.html"
        assert year.has_posts is True
        assert year.months == []
