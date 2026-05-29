"""Gunning Fog Index calculation utilities for blogmore."""

from __future__ import annotations

import re
import string
from functools import cache


def identify_proper_nouns(text: str, words: list[str] | None = None) -> set[str]:
    """Scan text to isolate potential proper nouns.

    A word is designated a proper noun if it is seen title-cased but never
    lowercase anywhere in the text.

    Args:
        text: The plain text to scan.
        words: Optional pre-extracted list of words.

    Returns:
        A set of identified proper nouns in their original casing as seen in
        the text.
    """
    if words is None:
        words = _extract_words(text)
    lowercase_words = {word for word in words if word.islower()}
    title_cased_words = {word for word in words if word and word[0].isupper()}

    proper_nouns = set()
    for word in title_cased_words:
        if word.lower() not in lowercase_words:
            proper_nouns.add(word)
    return proper_nouns


@cache
def count_syllables(word: str) -> int:
    """Calculate the number of syllables in a word using a vowel-group heuristic.

    Heuristic vowel group count (`[aeiouy]+`). Subtracts 1 for trailing
    "e", "es", "ed" (unless ending in "les", "led"). The minimum count is 1.

    Args:
        word: The word to check.

    Returns:
        The heuristic syllable count (at least 1).
    """
    word_lower = word.lower()
    vowel_groups = re.findall(r"[aeiouy]+", word_lower)
    count = len(vowel_groups)
    if word_lower.endswith(("e", "es", "ed")) and not word_lower.endswith(
        ("les", "led")
    ):
        count -= 1
    return max(1, count)


def calculate_gunning_fog_index(text: str) -> float:
    """Calculate the Gunning Fog Index for the given plain text.

    Tokenises sentences using [.!?]+ and words by stripping common
    punctuation. Proper nouns are identified and excluded. Complex words are
    those with 3 or more syllables. The formula is:
    0.4 * ((total_words / total_sentences) + 100 * (complex_words / total_words)).

    Args:
        text: The plain text to analyse.

    Returns:
        The Gunning Fog Index score as a float. Returns 0.0 if the text has
        no words or sentences.
    """
    if not text.strip():
        return 0.0

    # Tokenise sentences
    sentences = [
        sentence.strip() for sentence in re.split(r"[.!?]+", text) if sentence.strip()
    ]
    total_sentences = len(sentences)
    if total_sentences == 0:
        return 0.0

    # Extract all words
    words = _extract_words(text)
    if not words:
        return 0.0

    proper_nouns = identify_proper_nouns(text, words=words)
    proper_nouns_lower = {proper_noun.lower() for proper_noun in proper_nouns}

    # Exclude proper nouns
    filtered_words = [word for word in words if word.lower() not in proper_nouns_lower]
    total_words = len(filtered_words)
    if total_words == 0:
        return 0.0

    # Count complex words (syllables >= 3)
    complex_words = sum(1 for word in filtered_words if count_syllables(word) >= 3)

    # Apply Gunning Fog Index formula
    return 0.4 * ((total_words / total_sentences) + 100 * (complex_words / total_words))


def _extract_words(text: str) -> list[str]:
    """Helper to extract words from text, stripping common punctuation.

    Args:
        text: The text to extract words from.

    Returns:
        A list of word tokens.
    """
    raw_tokens = text.split()
    words = []
    # Strip common punctuation from the ends of the tokens
    # Common punctuation: standard string.punctuation plus smart quotes/apostrophes
    punctuation = string.punctuation + '""\'`‘’“”'
    for token in raw_tokens:
        word = token.strip(punctuation)
        if word:
            words.append(word)
    return words
