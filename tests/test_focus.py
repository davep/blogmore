"""Tests for the focus module."""

import math
from typing import Any

from blogmore.focus import extract_top_terms_per_year


def test_extract_top_terms_empty_corpus() -> None:
    """An empty corpus returns an empty dictionary."""
    assert extract_top_terms_per_year({}) == {}


def test_extract_top_terms_empty_text() -> None:
    """Years with empty text or no valid words return empty lists."""
    corpus = {
        2020: "",
        2021: "and the for with",  # all stop words
        2022: "ab cd ef",  # all words under 3 letters
    }
    results = extract_top_terms_per_year(corpus)
    assert results == {2020: [], 2021: [], 2022: []}


def test_extract_top_terms_simple_tf_idf() -> None:
    """Verify TF-IDF scoring and sorting.

    Let's construct a simple corpus:
    2020: "apple banana apple"
      - total words = 3
      - counts: apple: 2, banana: 1
    2021: "banana cherry"
      - total words = 2
      - counts: banana: 1, cherry: 1

    Total documents D = 2.
    Document frequency (DF):
      apple: 1 (only 2020)
      banana: 2 (both 2020 and 2021)
      cherry: 1 (only 2021)

    IDF:
      apple: ln(2/1) = ln(2)
      banana: ln(2/2) = ln(1) = 0.0
      cherry: ln(2/1) = ln(2)

    Scores:
      2020:
        apple: TF = 2/3, TF-IDF = (2/3) * ln(2) approx 0.6667 * 0.6931 = 0.4621
        banana: TF = 1/3, TF-IDF = (1/3) * 0 = 0.0
      2021:
        cherry: TF = 1/2, TF-IDF = (1/2) * ln(2) approx 0.5 * 0.6931 = 0.3466
        banana: TF = 1/2, TF-IDF = (1/2) * 0 = 0.0
    """
    corpus = {
        2020: "apple banana apple",
        2021: "banana cherry",
    }
    results = extract_top_terms_per_year(corpus, top_n=5)

    assert 2020 in results
    assert 2021 in results

    # 2020 top term should be apple
    assert results[2020][0][0] == "apple"
    assert results[2020][0][1] == pytest_approx((2 / 3) * math.log(2))
    assert results[2020][1][0] == "banana"
    assert results[2020][1][1] == 0.0

    # 2021 top term should be cherry
    assert results[2021][0][0] == "cherry"
    assert results[2021][0][1] == pytest_approx((1 / 2) * math.log(2))
    assert results[2021][1][0] == "banana"
    assert results[2021][1][1] == 0.0


def pytest_approx(val: float) -> Any:
    """Helper to do approximate comparison."""
    import pytest

    return pytest.approx(val)


def test_extract_top_terms_case_preservation() -> None:
    """Verify case-insensitive calculation but retaining the best original casing."""
    corpus = {
        2020: "MRE mre MRE iMac IMAC iMac iMac",
        2021: "mre IMAC",
    }
    results = extract_top_terms_per_year(corpus, top_n=5)

    assert 2020 in results
    assert 2021 in results

    terms_2020 = [t for t, _ in results[2020]]
    terms_2021 = [t for t, _ in results[2021]]

    # For 2020, iMac was used 3 times (MRE 2x, IMAC 1x, mre 1x), so:
    # 'imac' casing: iMac (3), IMAC (1) -> best iMac
    # 'mre' casing: MRE (2), mre (1) -> best MRE
    assert "iMac" in terms_2020
    assert "MRE" in terms_2020
    assert "Imac" not in terms_2020
    assert "Mre" not in terms_2020

    # For 2021, mre used once, IMAC used once:
    assert "mre" in terms_2021
    assert "IMAC" in terms_2021


def test_focus_term_attributes_and_unpacking() -> None:
    """Verify that FocusTerm has extra attributes but unpacks exactly as a 2-tuple."""
    corpus = {
        2020: "apple banana apple",
        2021: "banana cherry",
    }
    results = extract_top_terms_per_year(corpus, top_n=5)

    assert 2020 in results
    assert 2021 in results

    # Get FocusTerm objects
    terms_2020 = results[2020]
    apple_term = next(t for t in terms_2020 if t.word == "apple")

    # Attributes
    assert apple_term.word == "apple"
    assert apple_term.raw_count == 2
    # apple was used 2 times in 2020 and 0 times in 2021, so 100% exclusivity
    assert apple_term.exclusivity == 100

    # Unpacking / Indexing compatibility
    word, score = apple_term
    assert word == "apple"
    assert score == apple_term.score
    assert apple_term[0] == "apple"
    assert apple_term[1] == apple_term.score
    assert len(apple_term) == 2

    banana_term_2020 = next(t for t in terms_2020 if t.word == "banana")
    # banana was used 1 time in 2020 and 1 time in 2021, so 50% exclusivity
    assert banana_term_2020.raw_count == 1
    assert banana_term_2020.exclusivity == 50


def test_focus_custom_stop_words() -> None:
    """Verify that custom stop words are filtered out by extract_top_terms_per_year."""
    from blogmore.stop_words import STOP_WORDS, reset_stop_words

    # Register custom stop word
    reset_stop_words(["apple"])
    try:
        assert "apple" in STOP_WORDS
        corpus = {
            2020: "apple banana cherry",
        }
        results = extract_top_terms_per_year(corpus, top_n=5)
        words = [t[0] for t in results[2020]]
        # apple should be filtered out because it is in custom stop words
        assert "apple" not in words
        assert "banana" in words
        assert "cherry" in words
    finally:
        # Reset back to defaults to not affect other tests
        reset_stop_words()
