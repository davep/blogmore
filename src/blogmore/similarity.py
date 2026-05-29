"""TF-IDF and Cosine Similarity content matching engine for blog posts."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blogmore.parser import Post
    from blogmore.site_config import SiteConfig

from blogmore.stop_words import STOP_WORDS


def tokenise(text: str) -> list[str]:
    """Tokenise a string into lowercased alphanumeric words, filtering out stop words.

    Args:
        text: Plain text content.

    Returns:
        List of word tokens.
    """
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [word for word in words if word not in STOP_WORDS]


def _sort_oldest_first(posts: list[Post]) -> list[Post]:
    """Sort a list of posts from oldest to newest post date.

    Posts without dates are placed at the end of the list.

    Args:
        posts: List of Post objects.

    Returns:
        A new list of Post objects sorted from oldest to newest.
    """
    from blogmore.parser import post_sort_key

    def key_func(post: Post) -> float:
        sort_value = post_sort_key(post)
        return float("inf") if sort_value == 0.0 else sort_value

    return sorted(posts, key=key_func)


@dataclass
class PostVector:
    """Represents a sparse TF-IDF vector for a post.

    Attributes:
        weights: Mapping from term to its TF-IDF weight.
        magnitude: Pre-computed Euclidean norm (magnitude) of the vector.
    """

    weights: dict[str, float]
    magnitude: float


class SimilarityEngine:
    """Calculates document similarity using TF-IDF and Cosine Similarity."""

    def __init__(self, site_config: SiteConfig) -> None:
        """Initialize the similarity engine.

        Args:
            site_config: Configuration for the site.
        """
        self.site_config = site_config

        # Memory cache for preview server
        self._cached_tokens: dict[Path, list[str]] = {}
        self._cached_vectors: dict[Path, PostVector] = {}
        self._cached_vocab: dict[str, float] = {}  # term -> idf
        self._cached_mtimes: dict[Path, float] = {}
        self._similarities: dict[Path, dict[Path, float]] = {}
        self._last_prune_vocab_size: int | None = None

    def calculate_related_posts(self, posts: list[Post]) -> None:
        """Populate the related_posts attribute on each Post object.

        Automatically detects if we can run a fast-path rebuild when exactly one
        post has been modified. Falls back to a full O(N^2) calculation on changes
        affecting multiple files or additions/deletions.

        Args:
            posts: List of parsed Post objects.
        """
        # If the prune vocabulary size setting changed, clear cache to force full recalculation.
        if self._last_prune_vocab_size != self.site_config.related_prune_vocab_size:
            self._cached_vectors.clear()
            self._cached_vocab.clear()
            self._similarities.clear()

        # Graceful degradation: if fewer than 3 posts, fall back to most recent posts.
        if len(posts) < 3:
            for post in posts:
                # Exclude the post itself and limit to related_count
                raw_related = [
                    other_post for other_post in posts if other_post.path != post.path
                ][: self.site_config.related_count]
                post.related_posts = _sort_oldest_first(raw_related)
            return

        current_paths = {post.path for post in posts}
        cached_paths = set(self._cached_mtimes.keys())

        # Determine changes
        added_paths = current_paths - cached_paths
        deleted_paths = cached_paths - current_paths

        modified_paths: set[Path] = set()
        for post in posts:
            if post.path in cached_paths:
                try:
                    mtime = post.path.stat().st_mtime
                except OSError:
                    mtime = 0.0
                if mtime != self._cached_mtimes[post.path]:
                    modified_paths.add(post.path)

        post_map = {post.path: post for post in posts}

        # Check if we can run the fast path (exactly 1 modified, 0 added, 0 deleted)
        if (
            self._cached_vectors
            and len(added_paths) == 0
            and len(deleted_paths) == 0
            and len(modified_paths) == 1
        ):
            modified_path = next(iter(modified_paths))
            modified_post = post_map[modified_path]
            self._run_fast_path(modified_post, posts)
        elif (
            self._cached_vectors
            and len(added_paths) == 0
            and len(deleted_paths) == 0
            and len(modified_paths) == 0
        ):
            # No files changed, just set related posts from cache
            self._populate_posts_from_cache(posts, post_map)
        else:
            # Full recalculation
            self._run_full_calculation(posts)

    def _run_fast_path(self, modified_post: Post, posts: list[Post]) -> None:
        """Compute the updated vector and similarities for a single modified post.

        Args:
            modified_post: The modified Post object.
            posts: The list of all Post objects in the current build.
        """
        # Clean and tokenise the modified post
        plain_text = modified_post.prose_text
        tokens = tokenise(plain_text)

        # Update cached tokens
        self._cached_tokens[modified_post.path] = tokens

        # Get current mtime
        try:
            mtime = modified_post.path.stat().st_mtime
        except OSError:
            mtime = 0.0
        self._cached_mtimes[modified_post.path] = mtime

        # Compute new vector using cached vocabulary & IDFs
        total_tokens = len(tokens)
        weights: dict[str, float] = {}
        if total_tokens > 0:
            counts: dict[str, int] = {}
            for token in tokens:
                counts[token] = counts.get(token, 0) + 1

            for term, idf in self._cached_vocab.items():
                if term in counts:
                    term_frequency = counts[term] / total_tokens
                    weights[term] = term_frequency * idf

        magnitude = math.sqrt(sum(weight**2 for weight in weights.values()))
        new_vector = PostVector(weights=weights, magnitude=magnitude)

        # Update cache
        self._cached_vectors[modified_post.path] = new_vector

        # Perform single-pass comparison against all other cached vectors
        mod_path = modified_post.path
        if mod_path not in self._similarities:
            self._similarities[mod_path] = {}

        for post in posts:
            other_path = post.path
            if other_path == mod_path:
                continue

            other_vector = self._cached_vectors.get(other_path)
            if other_vector is None:
                continue

            score = self._calculate_cosine_similarity(new_vector, other_vector)

            # Update bidirectional similarities
            self._similarities[mod_path][other_path] = score
            if other_path not in self._similarities:
                self._similarities[other_path] = {}
            self._similarities[other_path][mod_path] = score

        # Update related posts
        post_map = {post.path: post for post in posts}
        self._populate_posts_from_cache(posts, post_map)

    def _run_full_calculation(self, posts: list[Post]) -> None:
        """Run the full O(N^2) pairwise similarity calculation and rebuild the cache.

        Args:
            posts: List of parsed Post objects.
        """
        # Tokenise all posts
        self._cached_tokens.clear()
        self._cached_mtimes.clear()

        for post in posts:
            plain_text = post.prose_text
            self._cached_tokens[post.path] = tokenise(plain_text)
            try:
                mtime = post.path.stat().st_mtime
            except OSError:
                mtime = 0.0
            self._cached_mtimes[post.path] = mtime

        # Calculate document frequencies
        doc_counts: dict[str, int] = {}
        for tokens in self._cached_tokens.values():
            for token in set(tokens):
                doc_counts[token] = doc_counts.get(token, 0) + 1

        # Keep terms that appear in at least 2 documents and calculate IDF
        num_docs = len(posts)
        term_idfs: list[tuple[str, float]] = []
        for term, count in doc_counts.items():
            if count > 1:
                idf = math.log(num_docs / count) + 1.0
                term_idfs.append((term, idf))

        # Sort by IDF in descending order (highest IDF first)
        term_idfs.sort(key=lambda term_idf: term_idf[1], reverse=True)

        # Prune global vocabulary
        pruned_vocab = dict(term_idfs[: self.site_config.related_prune_vocab_size])
        self._cached_vocab = pruned_vocab
        self._last_prune_vocab_size = self.site_config.related_prune_vocab_size

        # Generate vectors
        self._cached_vectors.clear()
        for post in posts:
            tokens = self._cached_tokens[post.path]
            total_tokens = len(tokens)
            weights: dict[str, float] = {}

            if total_tokens > 0:
                counts: dict[str, int] = {}
                for token in tokens:
                    counts[token] = counts.get(token, 0) + 1

                for term, idf in pruned_vocab.items():
                    if term in counts:
                        term_frequency = counts[term] / total_tokens
                        weights[term] = term_frequency * idf

            magnitude = math.sqrt(sum(weight**2 for weight in weights.values()))
            self._cached_vectors[post.path] = PostVector(
                weights=weights, magnitude=magnitude
            )

        # Pairwise similarities
        self._similarities.clear()
        for index, post_a in enumerate(posts):
            path_a = post_a.path
            if path_a not in self._similarities:
                self._similarities[path_a] = {}

            vector_a = self._cached_vectors[path_a]

            for post_b in posts[index + 1 :]:
                path_b = post_b.path
                if path_b not in self._similarities:
                    self._similarities[path_b] = {}

                vector_b = self._cached_vectors[path_b]

                score = self._calculate_cosine_similarity(vector_a, vector_b)
                self._similarities[path_a][path_b] = score
                self._similarities[path_b][path_a] = score

        # Update related posts
        post_map = {post.path: post for post in posts}
        self._populate_posts_from_cache(posts, post_map)

    def _populate_posts_from_cache(
        self, posts: list[Post], post_map: dict[Path, Post]
    ) -> None:
        """Populate the related posts lists using cached similarity scores.

        Handles fallback to most recent posts for any post that does not have
        enough non-zero similarity matches.

        Args:
            posts: List of parsed Post objects to populate.
            post_map: Mapping from post Path to the current Post object.
        """
        related_count = self.site_config.related_count

        for post in posts:
            path = post.path
            scores = self._similarities.get(path, {})

            # Filter out zero-similarity posts, and sort by score in descending order
            similar_posts: list[tuple[Post, float]] = []
            for other_path, score in scores.items():
                if score > 0.0 and other_path in post_map:
                    similar_posts.append((post_map[other_path], score))

            similar_posts.sort(
                key=lambda post_score_pair: post_score_pair[1], reverse=True
            )

            related = [
                related_post for related_post, _ in similar_posts[:related_count]
            ]

            # Fallback: if we don't have enough related posts, fill with the most recent posts
            if len(related) < related_count:
                seen_paths = {related_post.path for related_post in related}
                seen_paths.add(post.path)

                for fallback_post in posts:
                    if fallback_post.path not in seen_paths:
                        related.append(fallback_post)
                        seen_paths.add(fallback_post.path)
                        if len(related) >= related_count:
                            break

            post.related_posts = _sort_oldest_first(related)

    def _calculate_cosine_similarity(
        self, vector_a: PostVector, vector_b: PostVector
    ) -> float:
        """Calculate the cosine similarity between two post vectors.

        Args:
            vector_a: First sparse TF-IDF vector.
            vector_b: Second sparse TF-IDF vector.

        Returns:
            The cosine similarity score (between 0.0 and 1.0).
        """
        if vector_a.magnitude == 0.0 or vector_b.magnitude == 0.0:
            return 0.0

        dot_product = 0.0
        weights_a, weights_b = vector_a.weights, vector_b.weights
        if len(weights_a) > len(weights_b):
            weights_a, weights_b = weights_b, weights_a

        for token, weight in weights_a.items():
            if token in weights_b:
                dot_product += weight * weights_b[token]

        return dot_product / (vector_a.magnitude * vector_b.magnitude)
