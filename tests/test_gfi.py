"""Tests for the gfi module."""

from __future__ import annotations

from blogmore.gfi import (
    calculate_gunning_fog_index,
    count_syllables,
    identify_proper_nouns,
)


class TestGfiProperNouns:
    """Tests for identify_proper_nouns."""

    def test_basic_proper_nouns(self) -> None:
        """Test that words title-cased and never lowercase are proper nouns."""
        text = "Google is a company. It provides search services to everyone."
        # "Google" starts with G and is never seen as "google".
        # "It" starts with I, but "it" is not seen in lowercase either.
        # "is", "a", "company", etc. are lowercase or not title-cased.
        proper_nouns = identify_proper_nouns(text)
        assert "Google" in proper_nouns
        assert "company" not in proper_nouns

    def test_proper_noun_seen_lowercase(self) -> None:
        """Test that if a word is seen in lowercase, it is not a proper noun."""
        text = "Apple makes the Apple iPhone, but apple is also a fruit."
        # "Apple" is seen title-cased and lowercase "apple" is also seen.
        # "iPhone" starts with lowercase i, not title-cased.
        proper_nouns = identify_proper_nouns(text)
        assert "Apple" not in proper_nouns
        # "iPhone" starts with i (lowercase), not title-cased.
        # Wait, "iPhone" is not title-cased (starts with lowercase). So it's not proper noun candidate.


class TestGfiCountSyllables:
    """Tests for count_syllables."""

    def test_simple_vowels(self) -> None:
        """Test simple vowel counts."""
        assert count_syllables("cat") == 1
        assert count_syllables("banana") == 3
        assert count_syllables("meeting") == 2  # ee is one group, i is another

    def test_trailing_e_subtraction(self) -> None:
        """Test that trailing e, es, ed subtracts 1 from syllable count."""
        assert (
            count_syllables("determine") == 3
        )  # de-ter-mine (vowels: e, e, i, e = 4. minus 1 = 3)
        assert count_syllables("plates") == 1  # pla-tes (vowels: a, e = 2. minus 1 = 1)
        assert count_syllables("passed") == 1  # pas-sed (vowels: a, e = 2. minus 1 = 1)

    def test_minimum_count(self) -> None:
        """Test that the minimum syllable count is 1."""
        assert count_syllables("the") == 1
        assert count_syllables("me") == 1

    def test_les_led_exception(self) -> None:
        """Test that trailing les, led do not subtract 1."""
        assert (
            count_syllables("rules") == 2
        )  # ru-les (vowels: u, e = 2. ends in les, so no subtraction)
        assert (
            count_syllables("led") == 1
        )  # vowels: e = 1. ends in led, so no subtraction.
        assert (
            count_syllables("handled") == 2
        )  # han-dled (vowels: a, e = 2. ends in led, no subtraction)


class TestCalculateGunningFogIndex:
    """Tests for calculate_gunning_fog_index."""

    def test_empty_and_whitespace(self) -> None:
        """Test that empty or whitespace strings return 0.0."""
        assert calculate_gunning_fog_index("") == 0.0
        assert calculate_gunning_fog_index("   \n\t   ") == 0.0

    def test_simple_formula(self) -> None:
        """Test GFI calculation with simple sentence and words."""
        # Sentence 1: "This is a simple sentence." (5 words)
        # Sentence 2: "We test readability here." (4 words)
        # Total sentences: 2
        # Total words: 9
        # Sentence-starting words "This" and "We" are seen title-cased but never lowercase,
        # so they are excluded as proper nouns.
        # Remaining words: ["is", "a", "simple", "sentence", "test", "readability", "here"] (7 words)
        # Complex words: "readability" (re-a-di-bi-li-ty: vowels e, a, i, i, y = 5.
        # Ends in y, no subtraction => 5 syllables)
        # So only 1 complex word: "readability".
        # Formula: 0.4 * ((total_words / total_sentences) + 100 * (complex_words / total_words))
        # = 0.4 * ((7 / 2) + 100 * (1 / 7))
        # = 0.4 * (3.5 + 14.285714...)
        # = 0.4 * 17.785714...
        # = 7.1142857...
        text = "This is a simple sentence. We test readability here."
        gfi = calculate_gunning_fog_index(text)
        assert abs(gfi - 7.114285714285714) < 1e-5

    def test_with_proper_nouns(self) -> None:
        """Test that proper nouns are excluded from word and complex word counts."""
        # Text: "Google is a great organization."
        # Proper noun: "Google" (is never lowercase)
        # Remaining words: "is", "a", "great", "organization" (4 words)
        # "organization" (vowels: o, a, i, a, i, o = 6. ends in o/no subtraction = 6 syllables) -> complex word
        # Total sentences: 1
        # Total words: 4
        # Complex words: 1
        # GFI = 0.4 * ((4 / 1) + 100 * (1 / 4)) = 0.4 * (4 + 25) = 11.6
        text = "Google is a great organization."
        gfi = calculate_gunning_fog_index(text)
        assert abs(gfi - 11.6) < 1e-5
