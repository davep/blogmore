"""TF-IDF and Cosine Similarity content matching engine for blog posts."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from blogmore.markdown.plain_text import html_to_plain_text

if TYPE_CHECKING:
    from blogmore.parser import Post
    from blogmore.site_config import SiteConfig

# Standard list of English stop words to filter out noise
STOP_WORDS: set[str] = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "aren't",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "can't",
    "cannot",
    "could",
    "couldn't",
    "did",
    "didn't",
    "do",
    "does",
    "doesn't",
    "doing",
    "don't",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "hadn't",
    "has",
    "hasn't",
    "have",
    "haven't",
    "having",
    "he",
    "he'd",
    "he'll",
    "he's",
    "her",
    "here",
    "here's",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "how's",
    "i",
    "i'd",
    "i'll",
    "i'm",
    "i've",
    "if",
    "in",
    "into",
    "is",
    "isn't",
    "it",
    "it's",
    "its",
    "itself",
    "let's",
    "me",
    "more",
    "most",
    "mustn't",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "ought",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "shan't",
    "she",
    "she'd",
    "she'll",
    "she's",
    "should",
    "shouldn't",
    "so",
    "some",
    "such",
    "than",
    "that",
    "that's",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "there's",
    "these",
    "they",
    "they'd",
    "they'll",
    "they're",
    "they've",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "wasn't",
    "we",
    "we'd",
    "we'll",
    "we're",
    "we've",
    "were",
    "weren't",
    "what",
    "what's",
    "when",
    "when's",
    "where",
    "where's",
    "which",
    "while",
    "who",
    "who's",
    "whom",
    "why",
    "why's",
    "with",
    "won't",
    "would",
    "wouldn't",
    "you",
    "you'd",
    "you'll",
    "you're",
    "you've",
    "your",
    "yours",
    "yourself",
    "yourselves",
}


def tokenise(text: str) -> list[str]:
    """Tokenise a string into lowercased alphanumeric words, filtering out stop words.

    Args:
        text: Plain text content.

    Returns:
        List of word tokens.
    """
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in STOP_WORDS]


def _sort_oldest_first(posts: list[Post]) -> list[Post]:
    """Sort a list of posts from oldest to newest post date.

    Posts without dates are placed at the end of the list.

    Args:
        posts: List of Post objects.

    Returns:
        A new list of Post objects sorted from oldest to newest.
    """
    from blogmore.parser import post_sort_key

    def key_func(p: Post) -> float:
        val = post_sort_key(p)
        return float("inf") if val == 0.0 else val

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
                raw_related = [p for p in posts if p.path != post.path][
                    : self.site_config.related_count
                ]
                post.related_posts = _sort_oldest_first(raw_related)
            return

        current_paths = {p.path for p in posts}
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

        post_map = {p.path: p for p in posts}

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
        plain_text = html_to_plain_text(
            modified_post.html_content, exclude_code_blocks=True
        )
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
            for t in tokens:
                counts[t] = counts.get(t, 0) + 1

            for term, idf in self._cached_vocab.items():
                if term in counts:
                    tf = counts[term] / total_tokens
                    weights[term] = tf * idf

        magnitude = math.sqrt(sum(w**2 for w in weights.values()))
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
        post_map = {p.path: p for p in posts}
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
            plain_text = html_to_plain_text(post.html_content, exclude_code_blocks=True)
            self._cached_tokens[post.path] = tokenise(plain_text)
            try:
                mtime = post.path.stat().st_mtime
            except OSError:
                mtime = 0.0
            self._cached_mtimes[post.path] = mtime

        # Calculate document frequencies
        doc_counts: dict[str, int] = {}
        for tokens in self._cached_tokens.values():
            for t in set(tokens):
                doc_counts[t] = doc_counts.get(t, 0) + 1

        # Keep terms that appear in at least 2 documents and calculate IDF
        num_docs = len(posts)
        term_idfs: list[tuple[str, float]] = []
        for term, count in doc_counts.items():
            if count > 1:
                idf = math.log(num_docs / count) + 1.0
                term_idfs.append((term, idf))

        # Sort by IDF in descending order (highest IDF first)
        term_idfs.sort(key=lambda x: x[1], reverse=True)

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
                for t in tokens:
                    counts[t] = counts.get(t, 0) + 1

                for term, idf in pruned_vocab.items():
                    if term in counts:
                        tf = counts[term] / total_tokens
                        weights[term] = tf * idf

            magnitude = math.sqrt(sum(w**2 for w in weights.values()))
            self._cached_vectors[post.path] = PostVector(
                weights=weights, magnitude=magnitude
            )

        # Pairwise similarities
        self._similarities.clear()
        for i, post_a in enumerate(posts):
            path_a = post_a.path
            if path_a not in self._similarities:
                self._similarities[path_a] = {}

            vector_a = self._cached_vectors[path_a]

            for post_b in posts[i + 1 :]:
                path_b = post_b.path
                if path_b not in self._similarities:
                    self._similarities[path_b] = {}

                vector_b = self._cached_vectors[path_b]

                score = self._calculate_cosine_similarity(vector_a, vector_b)
                self._similarities[path_a][path_b] = score
                self._similarities[path_b][path_a] = score

        # Update related posts
        post_map = {p.path: p for p in posts}
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

            similar_posts.sort(key=lambda x: x[1], reverse=True)

            related = [p for p, _ in similar_posts[:related_count]]

            # Fallback: if we don't have enough related posts, fill with the most recent posts
            if len(related) < related_count:
                seen_paths = {r.path for r in related}
                seen_paths.add(post.path)

                for p in posts:
                    if p.path not in seen_paths:
                        related.append(p)
                        seen_paths.add(p.path)
                        if len(related) >= related_count:
                            break

            post.related_posts = _sort_oldest_first(related)

    def _calculate_cosine_similarity(self, a: PostVector, b: PostVector) -> float:
        """Calculate the cosine similarity between two post vectors.

        Args:
            a: First sparse TF-IDF vector.
            b: Second sparse TF-IDF vector.

        Returns:
            The cosine similarity score (between 0.0 and 1.0).
        """
        if a.magnitude == 0.0 or b.magnitude == 0.0:
            return 0.0

        dot_product = 0.0
        dict_a, dict_b = a.weights, b.weights
        if len(dict_a) > len(dict_b):
            dict_a, dict_b = dict_b, dict_a

        for token, weight in dict_a.items():
            if token in dict_b:
                dot_product += weight * dict_b[token]

        return dot_product / (a.magnitude * b.magnitude)
