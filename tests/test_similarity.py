"""Tests for the similarity module."""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from blogmore.parser import Post
from blogmore.similarity import (
    PostVector,
    SimilarityEngine,
    tokenise,
)
from blogmore.site_config import SiteConfig


def test_tokenise_basic() -> None:
    """Test basic tokenisation, lowercasing, and punctuation stripping."""
    text = "Hello, World! This is a test."
    tokens = tokenise(text)
    # "this", "is", "a" are stop words and should be removed
    assert tokens == ["hello", "world", "test"]


def test_tokenise_only_stop_words() -> None:
    """Test that text consisting of only stop words returns an empty list."""
    text = "the a and of to in is that it"
    assert tokenise(text) == []


def test_tokenise_numbers() -> None:
    """Test that numbers are preserved as alphanumeric tokens."""
    text = "Python 3.12 is cool."
    # "is" is a stop word
    assert tokenise(text) == ["python", "3", "12", "cool"]


class TestCosineSimilarity:
    """Tests for cosine similarity calculation."""

    def test_identical_vectors(self) -> None:
        """Identical vectors should have a similarity of 1.0."""
        vec = PostVector(weights={"hello": 0.5, "world": 0.5}, magnitude=math.sqrt(0.5))
        engine = SimilarityEngine(MagicMock())
        score = engine._calculate_cosine_similarity(vec, vec)
        assert pytest.approx(score) == 1.0

    def test_orthogonal_vectors(self) -> None:
        """Orthogonal vectors (no shared terms) should have a similarity of 0.0."""
        vec_a = PostVector(weights={"hello": 1.0}, magnitude=1.0)
        vec_b = PostVector(weights={"world": 1.0}, magnitude=1.0)
        engine = SimilarityEngine(MagicMock())
        score = engine._calculate_cosine_similarity(vec_a, vec_b)
        assert score == 0.0

    def test_zero_magnitude_vector(self) -> None:
        """Vectors with zero magnitude should return 0.0 similarity."""
        vec_a = PostVector(weights={}, magnitude=0.0)
        vec_b = PostVector(weights={"hello": 1.0}, magnitude=1.0)
        engine = SimilarityEngine(MagicMock())
        assert engine._calculate_cosine_similarity(vec_a, vec_b) == 0.0
        assert engine._calculate_cosine_similarity(vec_b, vec_a) == 0.0

    def test_partial_similarity(self) -> None:
        """Verify correct math calculation on partial match."""
        # A = [1.0, 2.0], B = [2.0, 3.0]
        # dot = 1*2 + 2*3 = 8
        # mag_a = sqrt(1 + 4) = sqrt(5)
        # mag_b = sqrt(4 + 9) = sqrt(13)
        # similarity = 8 / (sqrt(5) * sqrt(13)) = 8 / sqrt(65) ≈ 0.992277
        vec_a = PostVector(weights={"t1": 1.0, "t2": 2.0}, magnitude=math.sqrt(5.0))
        vec_b = PostVector(weights={"t1": 2.0, "t2": 3.0}, magnitude=math.sqrt(13.0))
        engine = SimilarityEngine(MagicMock())
        score = engine._calculate_cosine_similarity(vec_a, vec_b)
        assert pytest.approx(score) == 8.0 / math.sqrt(65.0)


class TestSimilarityEngine:
    """Tests for the SimilarityEngine orchestration and behavior."""

    @pytest.fixture
    def site_config(self) -> SiteConfig:
        """Return a SiteConfig fixture."""
        config = MagicMock(spec=SiteConfig)
        config.related_count = 3
        config.related_prune_vocab_size = 5
        return config

    def test_graceful_degradation_few_posts(self, site_config: SiteConfig) -> None:
        """If there are fewer than 3 posts, related posts should fall back to other posts."""
        post1 = Post(
            path=Path("post1.md"),
            title="Post 1",
            content="",
            html_content="<p>hello</p>",
        )
        post2 = Post(
            path=Path("post2.md"),
            title="Post 2",
            content="",
            html_content="<p>world</p>",
        )

        engine = SimilarityEngine(site_config)
        engine.calculate_related_posts([post1, post2])

        assert post1.related_posts == [post2]
        assert post2.related_posts == [post1]

    def test_full_calculation(self, site_config: SiteConfig) -> None:
        """Verify full calculation matches posts contextually."""
        # Post 1 and Post 2 both talk about "python programming"
        # Post 3 talks about "banana recipe"
        post1 = Post(
            path=Path("p1.md"),
            title="Python 1",
            content="",
            html_content="<p>python programming guides</p>",
        )
        post2 = Post(
            path=Path("p2.md"),
            title="Python 2",
            content="",
            html_content="<p>python programming tutorials</p>",
        )
        post3 = Post(
            path=Path("p3.md"),
            title="Banana",
            content="",
            html_content="<p>banana split recipes dessert</p>",
        )

        engine = SimilarityEngine(site_config)
        engine.calculate_related_posts([post1, post2, post3])

        # Post 1's closest match should be Post 2
        assert post1.related_posts[0] == post2
        # Post 2's closest match should be Post 1
        assert post2.related_posts[0] == post1

        # Post 3 has no similarity with post1 or post2, so it should fall back to most recent (p1, p2)
        assert post3.related_posts == [post1, post2]

    def test_smart_caching_fast_path(
        self, site_config: SiteConfig, tmp_path: Path
    ) -> None:
        """Verify fast-path is used when exactly one post changes."""
        p1_file = tmp_path / "p1.md"
        p2_file = tmp_path / "p2.md"
        p3_file = tmp_path / "p3.md"

        p1_file.write_text("dummy")
        p2_file.write_text("dummy")
        p3_file.write_text("dummy")

        post1 = Post(
            path=p1_file,
            title="Python 1",
            content="",
            html_content="<p>python programming banana</p>",
        )
        post2 = Post(
            path=p2_file,
            title="Python 2",
            content="",
            html_content="<p>python programming</p>",
        )
        post3 = Post(
            path=p3_file,
            title="Banana",
            content="",
            html_content="<p>banana split dessert banana</p>",
        )

        engine = SimilarityEngine(site_config)

        # First run (full calculation)
        engine.calculate_related_posts([post1, post2, post3])
        assert post1.related_posts[0] == post2

        # Mock the full calculation to verify it isn't called again
        from unittest.mock import patch

        with (
            patch.object(engine, "_run_full_calculation") as mock_full,
            patch.object(
                engine, "_run_fast_path", wraps=engine._run_fast_path
            ) as mock_fast,
        ):
            # Modify post1 content and mtime
            post1_modified = Post(
                path=p1_file,
                title="Python 1",
                content="",
                html_content="<p>banana split</p>",
            )
            # Update mtime on disk to trick stat().st_mtime check
            p1_file.write_text("modified")

            posts_new = [post1_modified, post2, post3]
            engine.calculate_related_posts(posts_new)

            # Fast path should be called
            mock_fast.assert_called_once_with(post1_modified, posts_new)
            mock_full.assert_not_called()

            # Related posts should be updated: post1 now matches post3 (banana)
            assert post1_modified.related_posts[0] == post3

    def test_cache_invalidation_on_prune_vocab_size_change(
        self, site_config: SiteConfig, tmp_path: Path
    ) -> None:
        """Verify cache is invalidated and full calculation is triggered when vocab size setting changes."""
        p1_file = tmp_path / "p1.md"
        p2_file = tmp_path / "p2.md"
        p3_file = tmp_path / "p3.md"

        p1_file.write_text("dummy")
        p2_file.write_text("dummy")
        p3_file.write_text("dummy")

        post1 = Post(
            path=p1_file,
            title="Python 1",
            content="",
            html_content="<p>python programming banana</p>",
        )
        post2 = Post(
            path=p2_file,
            title="Python 2",
            content="",
            html_content="<p>python programming</p>",
        )
        post3 = Post(
            path=p3_file,
            title="Banana",
            content="",
            html_content="<p>banana split dessert banana</p>",
        )

        engine = SimilarityEngine(site_config)

        # First run (full calculation)
        engine.calculate_related_posts([post1, post2, post3])
        assert engine._last_prune_vocab_size == 5

        from unittest.mock import patch

        with (
            patch.object(
                engine, "_run_full_calculation", wraps=engine._run_full_calculation
            ) as mock_full,
            patch.object(engine, "_run_fast_path") as mock_fast,
        ):
            # Change configuration option
            site_config.related_prune_vocab_size = 3

            # Run again with no files modified
            engine.calculate_related_posts([post1, post2, post3])

            # Should perform a full calculation because the config option changed, NOT fast path
            mock_full.assert_called_once()
            mock_fast.assert_not_called()
            assert engine._last_prune_vocab_size == 3

    def test_related_posts_are_sorted_oldest_first(
        self, site_config: SiteConfig
    ) -> None:
        """Verify related posts are sorted from oldest to newest post date."""
        import datetime as dt

        # post1 is newer (2025), post2 is older (2024), post3 is oldest (2023)
        post1 = Post(
            path=Path("p1.md"),
            title="Python 1",
            content="",
            html_content="<p>python programming banana</p>",
            date=dt.datetime(2025, 1, 1),
        )
        post2 = Post(
            path=Path("p2.md"),
            title="Python 2",
            content="",
            html_content="<p>python programming</p>",
            date=dt.datetime(2024, 1, 1),
        )
        post3 = Post(
            path=Path("p3.md"),
            title="Banana",
            content="",
            html_content="<p>banana split dessert banana</p>",
            date=dt.datetime(2023, 1, 1),
        )

        engine = SimilarityEngine(site_config)
        engine.calculate_related_posts([post1, post2, post3])

        # For post1, related posts (post2 and post3) should be sorted oldest to newest:
        # oldest is post3 (2023), then post2 (2024)
        assert post1.related_posts == [post3, post2]
