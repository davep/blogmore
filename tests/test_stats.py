"""Tests for the stats module."""

import datetime as dt
from pathlib import Path

import pytest

from blogmore.parser import Post
from blogmore.stats import (
    BlogStats,
    StreakChartCell,
    StreakChartVariant,
    _extract_external_links,
    compute_blog_stats,
)


class TestExtractExternalLinks:
    """Tests for the _extract_external_links helper."""

    def test_extracts_external_http_link(self) -> None:
        """An http:// link is detected as external."""
        links = _extract_external_links('<a href="http://example.com">link</a>', "")
        assert "http://example.com" in links

    def test_extracts_external_https_link(self) -> None:
        """An https:// link is detected as external."""
        links = _extract_external_links(
            '<a href="https://github.com/user/repo">link</a>', ""
        )
        assert "https://github.com/user/repo" in links

    def test_skips_root_relative_link(self) -> None:
        """Root-relative links starting with / are not counted as external."""
        links = _extract_external_links('<a href="/about.html">About</a>', "")
        assert not links

    def test_skips_anchor_link(self) -> None:
        """Anchor-only links (#section) are not counted as external."""
        links = _extract_external_links('<a href="#section">Jump</a>', "")
        assert not links

    def test_skips_same_site_link(self) -> None:
        """Links pointing to the same site_url domain are not counted as external."""
        links = _extract_external_links(
            '<a href="https://example.com/page">page</a>',
            "https://example.com",
        )
        assert not links

    def test_skips_same_site_www_variant(self) -> None:
        """Links to www.site_url are also treated as internal."""
        links = _extract_external_links(
            '<a href="https://www.example.com/page">page</a>',
            "https://example.com",
        )
        assert not links

    def test_multiple_links_returned(self) -> None:
        """All external links in the content are returned."""
        html = (
            '<a href="https://a.com">a</a>'
            '<a href="https://b.com">b</a>'
            '<a href="/internal">i</a>'
        )
        links = _extract_external_links(html, "")
        assert "https://a.com" in links
        assert "https://b.com" in links
        assert "/internal" not in links

    def test_empty_href_skipped(self) -> None:
        """An empty href value is silently ignored."""
        links = _extract_external_links('<a href="">empty</a>', "")
        assert not links


class TestComputeBlogStats:
    """Tests for the compute_blog_stats function."""

    def _make_post(
        self,
        *,
        slug: str = "test",
        title: str = "Test",
        content: str = "Hello world.",
        html_content: str = "<p>Hello world.</p>",
        date: dt.datetime | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
    ) -> Post:
        return Post(
            path=Path(f"{slug}.md"),
            title=title,
            content=content,
            html_content=html_content,
            date=date,
            tags=tags,
            category=category,
        )

    def test_empty_posts_returns_default_stats(self) -> None:
        """An empty post list returns a BlogStats with all-zero values."""
        stats = compute_blog_stats([])
        assert isinstance(stats, BlogStats)
        assert stats.avg_word_count == 0.0
        assert stats.tag_count == 0
        assert stats.unique_external_link_count == 0
        assert stats.top_domains == []

    def test_posts_per_hour_counts_correctly(self) -> None:
        """Posts are counted in the correct hour bucket."""
        posts = [
            self._make_post(date=dt.datetime(2024, 1, 1, 10, 0, 0)),
            self._make_post(date=dt.datetime(2024, 1, 2, 10, 0, 0)),
            self._make_post(date=dt.datetime(2024, 1, 3, 14, 0, 0)),
        ]
        stats = compute_blog_stats(posts)
        assert stats.posts_per_hour[10] == 2
        assert stats.posts_per_hour[14] == 1
        assert stats.posts_per_hour[0] == 0

    def test_posts_per_weekday_counts_correctly(self) -> None:
        """Posts are counted in the correct weekday bucket (Monday = 0)."""
        # 2024-01-01 is a Monday (weekday 0)
        post = self._make_post(date=dt.datetime(2024, 1, 1, 12, 0, 0))
        stats = compute_blog_stats([post])
        assert stats.posts_per_weekday[0] == 1  # Monday

    def test_posts_per_month_counts_correctly(self) -> None:
        """Posts are counted in the correct month bucket (January = index 0)."""
        posts = [
            self._make_post(date=dt.datetime(2024, 1, 15)),
            self._make_post(date=dt.datetime(2024, 3, 20)),
        ]
        stats = compute_blog_stats(posts)
        assert stats.posts_per_month[0] == 1  # January
        assert stats.posts_per_month[2] == 1  # March
        assert stats.posts_per_month[1] == 0  # February

    def test_posts_without_dates_excluded_from_histograms(self) -> None:
        """Posts with no date are not included in date-based histograms."""
        posts = [
            self._make_post(date=None),
            self._make_post(date=dt.datetime(2024, 6, 1, 9, 0, 0)),
        ]
        stats = compute_blog_stats(posts)
        assert sum(stats.posts_per_hour) == 1
        assert sum(stats.posts_per_weekday) == 1
        assert sum(stats.posts_per_month) == 1

    def test_avg_word_count_computed(self) -> None:
        """Average word count is the mean of all post word counts."""
        posts = [
            self._make_post(content="one two three"),  # 3 words
            self._make_post(content="a b c d e f g"),  # 7 words
        ]
        stats = compute_blog_stats(posts)
        assert stats.avg_word_count == pytest.approx(5.0)

    def test_min_max_word_count_and_posts(self) -> None:
        """Min and max word count values and their linked posts are identified."""
        short = self._make_post(slug="short", title="Short", content="a b c")
        long = self._make_post(slug="long", title="Long", content="a " * 50)
        stats = compute_blog_stats([short, long])
        assert stats.min_word_count == 3
        assert stats.max_word_count == 50
        assert stats.min_word_count_post is short
        assert stats.max_word_count_post is long

    def test_blog_span_days_computed(self) -> None:
        """blog_span_days returns the difference between earliest and latest dates."""
        posts = [
            self._make_post(date=dt.datetime(2024, 1, 1)),
            self._make_post(date=dt.datetime(2024, 6, 1)),
        ]
        stats = compute_blog_stats(posts)
        assert (
            stats.blog_span_days
            == (dt.datetime(2024, 6, 1) - dt.datetime(2024, 1, 1)).days
        )

    def test_blog_span_days_none_without_dated_posts(self) -> None:
        """blog_span_days is None when no posts have a date."""
        stats = compute_blog_stats([self._make_post(date=None)])
        assert stats.blog_span_days is None

    def test_tag_count_unique(self) -> None:
        """tag_count is the number of distinct tags across all posts."""
        posts = [
            self._make_post(tags=["python", "testing"]),
            self._make_post(tags=["python", "web"]),
        ]
        stats = compute_blog_stats(posts)
        assert stats.tag_count == 3  # python, testing, web

    def test_category_count_unique(self) -> None:
        """category_count is the number of distinct categories."""
        posts = [
            self._make_post(category="Programming"),
            self._make_post(category="News"),
            self._make_post(category="Programming"),
        ]
        stats = compute_blog_stats(posts)
        assert stats.category_count == 2

    def test_unique_external_link_count(self) -> None:
        """unique_external_link_count reflects distinct URLs across all posts."""
        posts = [
            self._make_post(html_content='<a href="https://a.com">a</a>'),
            self._make_post(
                html_content='<a href="https://b.com">b</a><a href="https://a.com">a again</a>'
            ),
        ]
        stats = compute_blog_stats(posts)
        # a.com and b.com are both unique; a.com appears twice but only counted once.
        assert stats.unique_external_link_count == 2

    def test_top_domains_sorted_by_count_descending(self) -> None:
        """top_domains is sorted from most to fewest links."""
        posts = [
            self._make_post(
                html_content=(
                    '<a href="https://common.com/1">1</a>'
                    '<a href="https://common.com/2">2</a>'
                    '<a href="https://common.com/3">3</a>'
                    '<a href="https://rare.com/1">r1</a>'
                )
            ),
        ]
        stats = compute_blog_stats(posts)
        assert stats.top_domains[0][0] == "common.com"
        assert stats.top_domains[0][1] == 3
        assert stats.top_domains[1][0] == "rare.com"
        assert stats.top_domains[1][1] == 1

    def test_top_domains_capped_at_20(self) -> None:
        """At most 20 domains are returned in top_domains."""
        html = "".join(
            f'<a href="https://domain{i}.com/link{j}">link</a>'
            for i in range(30)
            for j in range(3)
        )
        post = self._make_post(html_content=html)
        stats = compute_blog_stats([post])
        assert len(stats.top_domains) <= 20

    def test_site_url_links_excluded_from_external(self) -> None:
        """Links pointing to the site_url domain are not counted as external."""
        post = self._make_post(
            html_content='<a href="https://myblog.com/about">internal</a>'
        )
        stats = compute_blog_stats([post], site_url="https://myblog.com")
        assert stats.unique_external_link_count == 0


class TestBlogStatsBlogSpanDays:
    """Tests for the blog_span_days property."""

    def test_span_is_none_when_no_dates(self) -> None:
        """Returns None when earliest or latest date is not set."""
        stats = BlogStats()
        assert stats.blog_span_days is None

    def test_span_is_zero_for_single_day(self) -> None:
        """Returns 0 when earliest and latest dates are the same."""
        same = dt.datetime(2024, 5, 1)
        stats = BlogStats(earliest_post_date=same, latest_post_date=same)
        assert stats.blog_span_days == 0

    def test_span_in_days(self) -> None:
        """Returns the correct number of days between two dates."""
        start = dt.datetime(2023, 1, 1)
        end = dt.datetime(2024, 1, 1)
        stats = BlogStats(
            earliest_post_date=start,
            latest_post_date=end,
        )
        assert stats.blog_span_days == (end - start).days


class TestStreakChart:
    """Tests for the streak chart fields on BlogStats."""

    def _make_post(
        self,
        *,
        slug: str = "test",
        title: str = "Test",
        date: dt.datetime | None = None,
    ) -> Post:
        """Create a minimal Post for testing."""
        return Post(
            path=Path(f"{slug}.md"),
            title=title,
            content="Hello.",
            html_content="<p>Hello.</p>",
            date=date,
        )

    def _nine_month_variant(
        self, posts: list[Post] | None = None
    ) -> StreakChartVariant:
        """Return the 9-month streak variant (index 2 in the list)."""
        stats = compute_blog_stats(posts or [])
        assert len(stats.streak_variants) == 3
        variant = stats.streak_variants[2]
        assert variant.months == 9
        return variant

    def test_streak_variants_populated(self) -> None:
        """streak_variants contains exactly three entries (3, 6, 9 months)."""
        stats = compute_blog_stats([])
        assert len(stats.streak_variants) == 3
        assert [v.months for v in stats.streak_variants] == [3, 6, 9]

    def test_streak_variants_populated_no_posts(self) -> None:
        """streak_variants is built even when there are no posts."""
        stats = compute_blog_stats([])
        assert len(stats.streak_variants) > 0

    def test_streak_weeks_each_has_seven_entries(self) -> None:
        """Every week column in every variant contains exactly 7 entries."""
        stats = compute_blog_stats([])
        for variant in stats.streak_variants:
            for week in variant.weeks:
                assert len(week) == 7

    def test_streak_9mo_grid_covers_correct_days(self) -> None:
        """The 9-month variant covers all days from window_start to today."""
        today = dt.date.today()
        # window_start = 1st of month 8 months before today
        start_month = today.month - 8
        start_year = today.year
        while start_month <= 0:
            start_month += 12
            start_year -= 1
        window_start = dt.date(start_year, start_month, 1)
        expected_days = (today - window_start).days + 1

        variant = self._nine_month_variant()
        in_window = [
            cell for week in variant.weeks for cell in week if cell is not None
        ]
        assert len(in_window) == expected_days

    def test_streak_grid_starts_at_window_start(self) -> None:
        """The first non-None cell of each variant falls exactly on window_start."""
        stats = compute_blog_stats([])
        today = dt.date.today()
        for variant in stats.streak_variants:
            start_month = today.month - (variant.months - 1)
            start_year = today.year
            while start_month <= 0:
                start_month += 12
                start_year -= 1
            expected_start = dt.date(start_year, start_month, 1)
            first_in_window = next(
                cell for week in variant.weeks for cell in week if cell is not None
            )
            assert first_in_window.date == expected_start

    def test_streak_grid_ends_on_today(self) -> None:
        """The last non-None cell's date is today in all variants."""
        stats = compute_blog_stats([])
        today = dt.date.today()
        for variant in stats.streak_variants:
            last_in_window = None
            for week in variant.weeks:
                for cell in week:
                    if cell is not None:
                        last_in_window = cell
            assert last_in_window is not None
            assert last_in_window.date == today

    def test_posts_in_last_year_counts_only_within_window(self) -> None:
        """posts_in_last_year counts only posts within the 365-day window."""
        today = dt.date.today()
        in_window_date = dt.datetime.combine(
            today - dt.timedelta(days=10), dt.time(12, 0)
        )
        out_of_window_date = dt.datetime.combine(
            today - dt.timedelta(days=400), dt.time(12, 0)
        )
        posts = [
            self._make_post(date=in_window_date),
            self._make_post(date=in_window_date),
            self._make_post(date=out_of_window_date),
        ]
        stats = compute_blog_stats(posts)
        assert stats.posts_in_last_year == 2

    def test_streak_cell_count_matches_post_count(self) -> None:
        """A cell's count reflects the number of posts on that date."""
        today = dt.date.today()
        post_date = dt.datetime.combine(today - dt.timedelta(days=5), dt.time(9, 0))
        posts = [
            self._make_post(date=post_date),
            self._make_post(date=post_date),
        ]
        stats = compute_blog_stats(posts)
        target = post_date.date()
        # Check across the 9-month variant (which always covers 5 days ago).
        variant = stats.streak_variants[2]
        matching = [
            cell
            for week in variant.weeks
            for cell in week
            if cell is not None and cell.date == target
        ]
        assert len(matching) == 1
        assert matching[0].count == 2

    def test_streak_cell_count_zero_for_day_with_no_posts(self) -> None:
        """Days inside the window with no posts have count == 0."""
        stats = compute_blog_stats([])
        today = dt.date.today()
        yesterday = today - dt.timedelta(days=1)
        variant = stats.streak_variants[2]  # 9-month variant
        matching = [
            cell
            for week in variant.weeks
            for cell in week
            if cell is not None and cell.date == yesterday
        ]
        assert len(matching) == 1
        assert matching[0].count == 0

    def test_streak_cell_in_window_flag(self) -> None:
        """All non-None streak cells have in_window == True."""
        stats = compute_blog_stats([])
        for variant in stats.streak_variants:
            for week in variant.weeks:
                for cell in week:
                    if cell is not None:
                        assert cell.in_window is True

    def test_streak_cell_dataclass_fields(self) -> None:
        """StreakChartCell exposes date, count, and in_window attributes."""
        cell = StreakChartCell(date=dt.date(2024, 6, 1), count=3, in_window=True)
        assert cell.date == dt.date(2024, 6, 1)
        assert cell.count == 3
        assert cell.in_window is True

    def test_streak_variant_dataclass_fields(self) -> None:
        """StreakChartVariant exposes months, posts_count, month_label_positions, weeks."""
        variant = StreakChartVariant(
            months=3,
            posts_count=5,
            month_label_positions=[("Apr", 1)],
            weeks=[],
        )
        assert variant.months == 3
        assert variant.posts_count == 5
        assert variant.month_label_positions == [("Apr", 1)]
        assert variant.weeks == []

    def test_month_label_positions_are_ordered(self) -> None:
        """month_label_positions are in ascending column order."""
        stats = compute_blog_stats([])
        for variant in stats.streak_variants:
            cols = [col for _, col in variant.month_label_positions]
            assert cols == sorted(cols)

    def test_month_label_count_matches_months(self) -> None:
        """Each variant has approximately as many month labels as months covered."""
        stats = compute_blog_stats([])
        for variant in stats.streak_variants:
            # Allow 1 extra label for partial months at the boundary.
            assert (
                variant.months
                <= len(variant.month_label_positions)
                <= variant.months + 1
            )

    def test_posts_count_per_variant(self) -> None:
        """Each variant's posts_count matches posts within its own window."""
        today = dt.date.today()
        # Post that is always within all variants (5 days ago).
        recent_date = dt.datetime.combine(today - dt.timedelta(days=5), dt.time(9, 0))
        # Post that is far in the past (always outside any variant window).
        old_date = dt.datetime.combine(today - dt.timedelta(days=400), dt.time(9, 0))
        posts = [
            self._make_post(date=recent_date),
            self._make_post(date=old_date),
        ]
        stats = compute_blog_stats(posts)
        for variant in stats.streak_variants:
            assert variant.posts_count == 1  # only the recent post

    def test_timezone_aware_posts_handled(self) -> None:
        """Timezone-aware post dates are normalised before being counted."""
        today = dt.date.today()
        aware_dt = dt.datetime.combine(
            today - dt.timedelta(days=2),
            dt.time(10, 0),
            tzinfo=dt.UTC,
        )
        stats = compute_blog_stats([self._make_post(date=aware_dt)])
        assert stats.posts_in_last_year == 1
