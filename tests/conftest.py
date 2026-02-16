"""Shared pytest fixtures for blogmore tests."""

import datetime as dt
from pathlib import Path

import pytest

from blogmore.parser import Page, Post


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def posts_dir(fixtures_dir: Path) -> Path:
    """Return the path to the posts fixtures directory."""
    return fixtures_dir / "posts"


@pytest.fixture
def pages_dir(fixtures_dir: Path) -> Path:
    """Return the path to the pages fixtures directory."""
    return fixtures_dir / "pages"


@pytest.fixture
def templates_dir(fixtures_dir: Path) -> Path:
    """Return the path to the templates fixtures directory."""
    return fixtures_dir / "templates"


@pytest.fixture
def sample_post() -> Post:
    """Return a sample Post object for testing."""
    return Post(
        path=Path("test-post.md"),
        title="Test Post",
        content="This is test content.",
        html_content="<p>This is test content.</p>",
        date=dt.datetime(2024, 1, 15, 12, 0, 0, tzinfo=dt.UTC),
        category="python",
        tags=["python", "testing"],
        draft=False,
        metadata={"title": "Test Post", "category": "python"},
    )


@pytest.fixture
def sample_draft_post() -> Post:
    """Return a sample draft Post object for testing."""
    return Post(
        path=Path("draft-post.md"),
        title="Draft Post",
        content="This is draft content.",
        html_content="<p>This is draft content.</p>",
        date=dt.datetime(2024, 1, 20, 12, 0, 0, tzinfo=dt.UTC),
        category="webdev",
        tags=["javascript", "draft"],
        draft=True,
        metadata={"title": "Draft Post", "draft": True},
    )


@pytest.fixture
def sample_post_without_date() -> Post:
    """Return a sample Post without a date for testing."""
    return Post(
        path=Path("no-date-post.md"),
        title="Post Without Date",
        content="Content without date.",
        html_content="<p>Content without date.</p>",
        date=None,
        category="general",
        tags=["misc"],
        draft=False,
        metadata={"title": "Post Without Date"},
    )


@pytest.fixture
def sample_page() -> Page:
    """Return a sample Page object for testing."""
    return Page(
        path=Path("about.md"),
        title="About",
        content="About page content.",
        html_content="<p>About page content.</p>",
        metadata={"title": "About"},
    )


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Return a temporary output directory for testing."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir
