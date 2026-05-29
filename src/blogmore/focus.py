"""Focus by year terms extraction using TF-IDF analysis."""

from __future__ import annotations

##############################################################################
# Python imports.
import math
import re
from collections import Counter

from blogmore.stop_words import STOP_WORDS


class FocusTerm(tuple[str, float]):
    """Represents a focus term with its score, exclusivity, and raw count.

    Acts as a 2-tuple (word, score) for backward-compatible unpacking in
    templates and tests.
    """

    def __new__(
        cls, word: str, score: float, exclusivity: int, raw_count: int
    ) -> FocusTerm:
        """Create a new FocusTerm instance.

        Args:
            word: The term string.
            score: The TF-IDF score.
            exclusivity: Percentage of total uses that occurred in this year.
            raw_count: Number of times used in this year.

        Returns:
            A new FocusTerm tuple instance.
        """
        return super().__new__(cls, (word, score))

    def __init__(
        self, word: str, score: float, exclusivity: int, raw_count: int
    ) -> None:
        """Initialize the FocusTerm instance.

        Args:
            word: The term string.
            score: The TF-IDF score.
            exclusivity: Percentage of total uses that occurred in this year.
            raw_count: Number of times used in this year.
        """
        self.word = word
        self.score = score
        self.exclusivity = exclusivity
        self.raw_count = raw_count


def extract_top_terms_per_year(
    corpus: dict[int, str], top_n: int = 5
) -> dict[int, list[FocusTerm]]:
    """Extract the top terms per year from a dictionary of year-to-prose corpus.

    Computes TF-IDF for each word per year. Fenced code blocks must not be
    included (this is handled by the caller who passes the prose corpus).
    Words are tokenised case-insensitively using the regular expression
    `\\b[a-zA-Z]{3,}\\b` and standard English stop words are filtered out.
    Calculations are performed in a case-insensitive manner (using the lowercase
    form of each term), but the returned terms retain their most common (best)
    original casing from the corpus for each year.

    Args:
        corpus: A dictionary mapping each year to a single aggregated string of
            prose text for that year.
        top_n: The maximum number of top terms to return per year.

    Returns:
        A dictionary mapping each year to a list of FocusTerm objects,
        sorted in descending order of score. If there are no terms for a year,
        returns an empty list for that year. Handles empty corpus and other
        division by zero edge cases safely.
    """
    if not corpus:
        return {}

    # Total number of documents (years)
    total_years = len(corpus)

    # Tokenise each year and compute term counts per year
    year_word_counts: dict[int, Counter[str]] = {}
    word_in_years: dict[str, set[int]] = {}
    # Track casing variants: year -> lowercase_word -> Counter[original_casing]
    year_casing_counts: dict[int, dict[str, Counter[str]]] = {}

    word_pattern = re.compile(r"\b[a-zA-Z]{3,}\b")

    for year, text in corpus.items():
        # Find all matching words in their original casing
        tokens = word_pattern.findall(text)

        filtered_words: list[str] = []
        casing_map: dict[str, Counter[str]] = {}

        for original_word in tokens:
            lower_word = original_word.lower()
            if lower_word not in STOP_WORDS:
                filtered_words.append(lower_word)
                if lower_word not in casing_map:
                    casing_map[lower_word] = Counter()
                casing_map[lower_word][original_word] += 1

        # Calculate counts of the canonical lowercase words
        counter = Counter(filtered_words)
        year_word_counts[year] = counter
        year_casing_counts[year] = casing_map

        for word in counter:
            if word not in word_in_years:
                word_in_years[word] = set()
            word_in_years[word].add(year)

    # Calculate lifetime counts of each lowercase word across the entire corpus
    lifetime_word_counts: Counter[str] = Counter()
    for counter in year_word_counts.values():
        lifetime_word_counts.update(counter)

    # Compute IDF for all encountered words
    idf: dict[str, float] = {}
    for word, years_with_word in word_in_years.items():
        num_years = len(years_with_word)
        idf[word] = math.log(total_years / num_years) if num_years > 0 else 0.0

    # Compute TF-IDF and extract top terms per year
    results: dict[int, list[FocusTerm]] = {}
    for year in corpus:
        counts = year_word_counts.get(year, Counter())
        total_terms = sum(counts.values())

        if total_terms == 0:
            results[year] = []
            continue

        tf_idf_scores: list[FocusTerm] = []
        casing_map = year_casing_counts.get(year, {})
        for word, count in counts.items():
            tf = count / total_terms
            word_idf = idf.get(word, 0.0)
            score = tf * word_idf

            # Find the best casing (most common original casing)
            casing_counts = casing_map.get(word)
            best_casing = casing_counts.most_common(1)[0][0] if casing_counts else word

            # Calculate exclusivity (percentage of total uses that occurred in this year)
            lifetime_count = lifetime_word_counts.get(word, 1)
            exclusivity = round(100 * count / lifetime_count)

            tf_idf_scores.append(FocusTerm(best_casing, score, exclusivity, count))

        # Sort descending by score, then alphabetically for stability
        tf_idf_scores.sort(key=lambda item: (-item[1], item[0]))
        results[year] = tf_idf_scores[:top_n]

    return results


### focus.py ends here
