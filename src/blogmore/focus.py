"""Focus by year terms extraction using TF-IDF analysis."""

##############################################################################
# Python imports.
import math
import re
from collections import Counter

# Standard English stop words to filter out of the TF-IDF analysis.
STOP_WORDS: set[str] = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "these",
    "those",
    "was",
    "were",
    "are",
    "been",
    "have",
    "had",
    "has",
    "having",
    "but",
    "not",
    "from",
    "out",
    "into",
    "over",
    "under",
    "about",
    "your",
    "their",
    "them",
    "then",
    "there",
    "they",
    "will",
    "would",
    "should",
    "could",
    "can",
    "may",
    "might",
    "must",
    "shall",
    "some",
    "any",
    "all",
    "each",
    "every",
    "other",
    "another",
    "such",
    "only",
    "more",
    "most",
    "less",
    "least",
    "than",
    "thence",
    "thereby",
    "therefore",
    "therein",
    "thereof",
    "thereon",
    "thereto",
    "therewith",
}


def extract_top_terms_per_year(
    corpus: dict[int, str], top_n: int = 5
) -> dict[int, list[tuple[str, float]]]:
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
        A dictionary mapping each year to a list of tuples containing the
        highest-scoring terms and their weights, sorted in descending order of
        score. If there are no terms for a year, returns an empty list for that
        year. Handles empty corpus and other division by zero edge cases safely.
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

        # Lowercase tokens for TF-IDF calculations
        lowercase_tokens = [w.lower() for w in tokens]

        # Filter out standard stop words using lowercase forms
        filtered_words = [word for word in lowercase_tokens if word not in STOP_WORDS]

        # Calculate counts of the canonical lowercase words
        counter = Counter(filtered_words)
        year_word_counts[year] = counter

        # Keep track of casing variants for the filtered words
        casing_map: dict[str, Counter[str]] = {}
        for original_word in tokens:
            lower_word = original_word.lower()
            if lower_word in counter:
                casing_map.setdefault(lower_word, Counter())[original_word] += 1
        year_casing_counts[year] = casing_map

        for word in counter:
            if word not in word_in_years:
                word_in_years[word] = set()
            word_in_years[word].add(year)

    # Compute IDF for all encountered words
    idf: dict[str, float] = {}
    for word, years_with_word in word_in_years.items():
        num_years = len(years_with_word)
        if num_years > 0:
            idf[word] = math.log(total_years / num_years)
        else:
            idf[word] = 0.0

    # Compute TF-IDF and extract top terms per year
    results: dict[int, list[tuple[str, float]]] = {}
    for year in corpus:
        counts = year_word_counts.get(year, Counter())
        total_terms = sum(counts.values())

        if total_terms == 0:
            results[year] = []
            continue

        tf_idf_scores: list[tuple[str, float]] = []
        casing_map = year_casing_counts.get(year, {})
        for word, count in counts.items():
            tf = count / total_terms
            word_idf = idf.get(word, 0.0)
            score = tf * word_idf

            # Find the best casing (most common original casing)
            casing_counts = casing_map.get(word)
            best_casing = casing_counts.most_common(1)[0][0] if casing_counts else word

            tf_idf_scores.append((best_casing, score))

        # Sort descending by score, then alphabetically for stability
        tf_idf_scores.sort(key=lambda item: (-item[1], item[0]))
        results[year] = tf_idf_scores[:top_n]

    return results


### focus.py ends here
