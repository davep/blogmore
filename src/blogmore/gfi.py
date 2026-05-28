"""Gunning Fog Index calculation utilities for blogmore."""

from __future__ import annotations

import re
import string


def identify_proper_nouns(text: str) -> set[str]:
    """Scan text to isolate potential proper nouns.

    A word is designated a proper noun if it is seen title-cased but never
    lowercase anywhere in the text.

    Args:
        text: The plain text to scan.

    Returns:
        A set of identified proper nouns in their original casing as seen in
        the text.
    """
    words = _extract_words(text)
    lowercase_words = {w for w in words if w.islower()}
    title_cased_words = {w for w in words if w and w[0].isupper()}

    proper_nouns = set()
    for w in title_cased_words:
        if w.lower() not in lowercase_words:
            proper_nouns.add(w)
    return proper_nouns


def count_syllables(word: str) -> int:
    """Calculate the number of syllables in a word using a vowel-group heuristic.

    Heuristic vowel group count (`[aeiouy]+`). Subtracts 1 for trailing
    "e", "es", "ed" (unless ending in "les", "led"). The minimum count is 1.

    Args:
        word: The word to check.

    Returns:
        The heuristic syllable count (at least 1).
    """
    w = word.lower()
    vowel_groups = re.findall(r"[aeiouy]+", w)
    count = len(vowel_groups)
    if w.endswith(("e", "es", "ed")) and not w.endswith(("les", "led")):
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
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    total_sentences = len(sentences)
    if total_sentences == 0:
        return 0.0

    # Extract all words
    words = _extract_words(text)
    if not words:
        return 0.0

    proper_nouns = identify_proper_nouns(text)
    proper_nouns_lower = {pn.lower() for pn in proper_nouns}

    # Exclude proper nouns
    filtered_words = [w for w in words if w.lower() not in proper_nouns_lower]
    total_words = len(filtered_words)
    if total_words == 0:
        return 0.0

    # Count complex words (syllables >= 3)
    complex_words = sum(1 for w in filtered_words if count_syllables(w) >= 3)

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
