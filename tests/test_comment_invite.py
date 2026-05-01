"""Tests for the comment_invite module."""

##############################################################################
# Standard-library imports.
import datetime as dt
from pathlib import Path

##############################################################################
# Third-party imports.
import pytest

##############################################################################
# Application imports.
from blogmore.comment_invite import build_mailto_url, get_invite_email_for_post
from blogmore.parser import Post

##############################################################################
# Fixtures.


@pytest.fixture
def dated_post() -> Post:
    """Return a post with a full date and metadata."""
    return Post(
        path=Path("2024-01-15-my-great-article.md"),
        title="My Great Article",
        content="Content here.",
        html_content="<p>Content here.</p>",
        date=dt.datetime(2024, 1, 15, 9, 30, 5, tzinfo=dt.UTC),
        category="Python",
        tags=["python", "blog"],
        draft=False,
        metadata={"title": "My Great Article", "author": "Dave Pearson"},
    )


@pytest.fixture
def undated_post() -> Post:
    """Return a post with no date."""
    return Post(
        path=Path("timeless-post.md"),
        title="Timeless",
        content="Content.",
        html_content="<p>Content.</p>",
        date=None,
        category=None,
        tags=[],
        draft=False,
        metadata={"title": "Timeless"},
    )


@pytest.fixture
def post_no_metadata() -> Post:
    """Return a post with no metadata dict."""
    return Post(
        path=Path("bare-post.md"),
        title="Bare Post",
        content="Content.",
        html_content="<p>Content.</p>",
        date=dt.datetime(2024, 6, 1, tzinfo=dt.UTC),
        category=None,
        tags=[],
        draft=False,
        metadata=None,
    )


##############################################################################
# get_invite_email_for_post tests.


class TestGetInviteEmailForPost:
    """Tests for get_invite_email_for_post."""

    def test_global_off_returns_none(self, dated_post: Post) -> None:
        """Returns None when invite_comments is False and no frontmatter."""
        result = get_invite_email_for_post(
            dated_post, invite_comments=False, invite_comments_to="user@example.com"
        )
        assert result is None

    def test_global_on_no_email_returns_none(self, dated_post: Post) -> None:
        """Returns None when invite_comments is True but invite_comments_to is None."""
        result = get_invite_email_for_post(
            dated_post, invite_comments=True, invite_comments_to=None
        )
        assert result is None

    def test_global_on_with_plain_email(self, dated_post: Post) -> None:
        """Returns the plain email when globally enabled with a plain address."""
        result = get_invite_email_for_post(
            dated_post, invite_comments=True, invite_comments_to="me@example.com"
        )
        assert result == "me@example.com"

    def test_global_on_with_template_email(self, dated_post: Post) -> None:
        """Returns the expanded email when globally enabled with a template."""
        result = get_invite_email_for_post(
            dated_post,
            invite_comments=True,
            invite_comments_to="me+{slug}@example.com",
        )
        assert result == "me+my-great-article@example.com"

    def test_frontmatter_invite_false_overrides_global_true(
        self, dated_post: Post
    ) -> None:
        """Front-matter invite_comments=False overrides global True."""
        dated_post.metadata = dict(dated_post.metadata or {})
        dated_post.metadata["invite_comments"] = False
        result = get_invite_email_for_post(
            dated_post, invite_comments=True, invite_comments_to="me@example.com"
        )
        assert result is None

    def test_frontmatter_invite_true_overrides_global_false(
        self, dated_post: Post
    ) -> None:
        """Front-matter invite_comments=True overrides global False."""
        dated_post.metadata = dict(dated_post.metadata or {})
        dated_post.metadata["invite_comments"] = True
        result = get_invite_email_for_post(
            dated_post, invite_comments=False, invite_comments_to="me@example.com"
        )
        assert result == "me@example.com"

    def test_frontmatter_invite_to_used_directly(self, dated_post: Post) -> None:
        """Front-matter invite_comments_to is used as a literal address."""
        dated_post.metadata = dict(dated_post.metadata or {})
        dated_post.metadata["invite_comments_to"] = "specific@example.com"
        result = get_invite_email_for_post(
            dated_post,
            invite_comments=True,
            invite_comments_to="template+{slug}@ex.com",
        )
        assert result == "specific@example.com"

    def test_frontmatter_invite_to_no_template_expansion(
        self, dated_post: Post
    ) -> None:
        """Front-matter invite_comments_to is NOT expanded as a template."""
        dated_post.metadata = dict(dated_post.metadata or {})
        dated_post.metadata["invite_comments_to"] = "me+{slug}@example.com"
        result = get_invite_email_for_post(
            dated_post, invite_comments=True, invite_comments_to=None
        )
        assert result == "me+{slug}@example.com"

    def test_no_metadata_global_on(self, post_no_metadata: Post) -> None:
        """Works correctly when post has no metadata dict."""
        result = get_invite_email_for_post(
            post_no_metadata,
            invite_comments=True,
            invite_comments_to="u@example.com",
        )
        assert result == "u@example.com"

    def test_no_metadata_global_off(self, post_no_metadata: Post) -> None:
        """Returns None for post with no metadata when globally disabled."""
        result = get_invite_email_for_post(
            post_no_metadata,
            invite_comments=False,
            invite_comments_to="u@example.com",
        )
        assert result is None

    def test_frontmatter_invite_to_empty_string_returns_none(
        self, dated_post: Post
    ) -> None:
        """An empty invite_comments_to in frontmatter returns None."""
        dated_post.metadata = dict(dated_post.metadata or {})
        dated_post.metadata["invite_comments_to"] = ""
        result = get_invite_email_for_post(
            dated_post, invite_comments=True, invite_comments_to="me@example.com"
        )
        assert result is None


##############################################################################
# build_mailto_url tests.


class TestBuildMailtoUrl:
    """Tests for build_mailto_url."""

    def test_basic_url(self) -> None:
        """Returns a valid mailto URL with percent-encoded subject."""
        result = build_mailto_url("me@example.com", "Hello World")
        assert result == "mailto:me@example.com?subject=Hello%20World"

    def test_special_characters_encoded(self) -> None:
        """Special characters in subject are percent-encoded."""
        result = build_mailto_url("me@example.com", "A & B: The Story")
        assert "%" in result
        assert result.startswith("mailto:me@example.com?subject=")

    def test_plain_subject_no_special_chars(self) -> None:
        """A subject with no special characters passes through cleanly."""
        result = build_mailto_url("a@b.com", "SimpleSubject")
        assert result == "mailto:a@b.com?subject=SimpleSubject"

    def test_subject_with_brackets(self) -> None:
        """Square brackets in subject are percent-encoded."""
        result = build_mailto_url("a@b.com", "Post [2024]")
        assert "%" in result
        assert result.startswith("mailto:a@b.com?subject=")


### test_comment_invite.py ends here
