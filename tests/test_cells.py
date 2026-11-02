"""Text bound for xlsx and docx cells: none of it may stop a writer (Avila Beach, hosted, 2026-11-02)."""

from spec_review.outputs.cells import printable


def test_dashes_and_quotes_the_model_wrote_without_their_high_byte_come_back() -> None:
    """gpt-5-mini wrote the page's en dash U+2013 as \\u0013; U+2010 to U+201F lose the same byte."""
    assert printable("Proposal Form \x13 Section 3") == "Proposal Form – Section 3"
    assert printable("don\x19t \x1cnow\x1d") == "don’t “now”"


def test_other_control_characters_become_spaces_and_tabs_and_newlines_stay() -> None:
    assert printable("a\x0cb\x00c\x0bd") == "a b c d"
    assert printable("a\tb\nc\rd") == "a\tb\nc\rd"


def test_values_that_are_not_text_pass_through() -> None:
    assert printable(7) == 7 and printable(None) is None and printable(0.5) == 0.5
