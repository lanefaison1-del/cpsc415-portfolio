"""No-key tests for the transcript checker (spec behaviors 29, 32 and 33).

    .venv/bin/python -m pytest voice/tests/test_check.py -v     # from the repository root
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from check import compare, survives, wer, words  # noqa: E402

SAID = "My name is Lane Faison and I study CPSC 415 at Trinity College."    # 13 words


def test_words_ignore_case_and_punctuation():
    assert words("Hello, World!  It's 415.") == ["hello", "world", "it's", "415"]


def test_perfect_transcript_scores_zero():
    assert wer(SAID, SAID) == 0.0
    assert wer(SAID, "my name is lane faison, and i study cpsc 415 at trinity college") == 0.0


def test_one_substitution_in_thirteen_words():
    assert abs(wer(SAID, SAID.replace("Faison", "Faisan")) - 1 / 13) < 1e-9


def test_empty_transcript_is_a_failed_transcript_not_a_crash():
    assert wer(SAID, "") == 1.0
    assert wer(SAID, None) == 1.0
    for got in (None, "", "   ", "..."):
        result = compare(SAID, got)
        assert result["empty"] and not result["ok"]


def test_a_name_that_must_survive_is_reported_within_tolerance():
    result = compare(SAID, SAID.replace("Faison", "Faisan"), must_contain=["Faison", "415"])
    assert result["wer"] <= 0.15                     # the rate alone would have passed
    assert result["missing"] == ["Faison"]
    assert not result["ok"]


def test_small_drift_within_tolerance_is_ok():
    got = "My name is Lane Faison and I study CPSC 415 at Trinity."          # one word dropped
    result = compare(SAID, got, must_contain=["Lane", "Faison", "CPSC 415"])
    assert result["ok"] and result["wer"] == round(1 / 13, 3)


def test_a_number_read_as_words_is_a_miss():
    got = SAID.replace("415", "four fifteen")
    assert compare(SAID, got, must_contain=["CPSC 415"])["missing"] == ["CPSC 415"]


def test_spacing_and_case_do_not_count():
    got = "compared with a Boot Camp graduate from cpsc415"
    assert compare("x", got, must_contain=["bootcamp", "CPSC 415"], max_wer=9)["missing"] == []
    assert survives("CPSC 415", "I study C P S C 415.")


def test_whole_words_only():
    got = SAID.replace("Lane", "plane")
    assert compare(SAID, got, must_contain=["Lane"])["missing"] == ["Lane"]
    assert not survives("415", "room 4150")
    assert not survives("Faison", "Faisonne")


def test_a_possessive_still_counts():
    said = "What did Lane Faison's capstone team build at Trinity?"
    assert compare(said, said, must_contain=["Lane", "Faison", "capstone", "Trinity"])["ok"]
