import pytest

from spec_review.extract.text import norm_text, numbers_in, split_sentences, strip_marker


@pytest.mark.parametrize("text,expected", [
    ("The system shall treat 2.0 MGD. It shall operate unattended.",
     ["The system shall treat 2.0 MGD.", "It shall operate unattended."]),
    ("Submit data per Section 01 33 00. Provide O&M manuals.",
     ["Submit data per Section 01 33 00.", "Provide O&M manuals."]),
    ("Provide No. 2 finish, e.g. as specified.", ["Provide No. 2 finish, e.g. as specified."]),
    ("Effluent phosphorus not exceeding 0.1 mg/L as a monthly average.",
     ["Effluent phosphorus not exceeding 0.1 mg/L as a monthly average."]),
    ("Pipe shall be 6 in. diameter. Valves shall be bronze.",
     ["Pipe shall be 6 in. diameter.", "Valves shall be bronze."]),
    ("Comply with ANSI/HI 14.6. Test per ASME PTC 13.", ["Comply with ANSI/HI 14.6.", "Test per ASME PTC 13."]),
])
def test_split_sentences(text: str, expected: list[str]) -> None:
    assert split_sentences(text) == expected


def test_norm_text_unicode_and_hyphens() -> None:
    assert norm_text("“Over ﬂow” equali- zation – 2") == '"Over flow" equalization - 2'


def test_numbers_in_spelled_and_separators() -> None:
    assert numbers_in("at least three (3) installations, $1,500 per day, 2 to 4 psi") == [3, 3, 1500, 2, 4]
    assert numbers_in("0.1 mg/L; -- ; Report") == [0.1]


@pytest.mark.parametrize("text,expected", [
    ("A. Membranes shall be PVDF.", "Membranes shall be PVDF."), ("2.03 MATERIALS", "MATERIALS"),
    ("3.2 Proposals shall be sealed.", "Proposals shall be sealed."), ("a) Gaskets.", "Gaskets."),
    ("(1) Bolts.", "Bolts."), ("Plain text.", "Plain text."), ("0.1 mg/L is the limit.", "0.1 mg/L is the limit."),
])
def test_strip_marker(text: str, expected: str) -> None:
    assert strip_marker(text) == expected
