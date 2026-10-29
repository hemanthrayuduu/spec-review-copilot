from spec_review.segment.paths import PathBuilder, display_number, part_of, path_key, section_key


def test_keys() -> None:
    assert section_key("46 21 00") == section_key("462100") == "462100"
    assert section_key("46_51_42.01") == "46514201" and display_number("46_51_42.01") == "46 51 42.01"
    assert display_number("46  51 00.00 10") == "46 51 00.00 10"
    assert path_key("2.03.B.4") == path_key("2.3.b.4") == "2.3.B.4"
    assert part_of("2.03.B") == "products" and part_of("1.2.a") == "general" and part_of("3.08.C.7") == "execution"
    assert part_of(None) == "none" and part_of("9.1") == "none"


def test_csi_path_builder() -> None:
    b = PathBuilder()
    b.start_section()
    assert [b.feed(t) for t in ["2.03 MATERIALS", "A. Frames:", "1. Stainless steel.", "a. Type 316.", "Plain text.",
                                "B. Bolts."]] == ["2.03", "2.03.A", "2.03.A.1", "2.03.A.1.a", "2.03.A.1.a", "2.03.B"]


def test_dotted_paths_reset_deeper_levels() -> None:
    b = PathBuilder()
    b.start_section()
    assert [b.feed(t) for t in ["1.2 SUBMITTALS", "a. Shop drawings.", "1.2.1 Certificates", "a. Test reports."]] == \
           ["1.2", "1.2.a", "1.2.1", "1.2.1.a"]


def test_deep_levels_and_parentheses() -> None:
    b = PathBuilder()
    b.start_section()
    assert [b.feed(t) for t in ["2.01 PUMPS", "A. Pumps:", "1. Casing:", "a. Cast iron:", "(1) Class 30.",
                                "(a) Tested.", "2) Second."]] == \
           ["2.01", "2.01.A", "2.01.A.1", "2.01.A.1.a", "2.01.A.1.a.1", "2.01.A.1.a.1.a", "2.01.A.1.a.2"]


def test_part_line_resets_and_guards_stray_decimals() -> None:
    b = PathBuilder()
    b.start_section()
    assert b.feed("1.05 SUBMITTALS") == "1.05"
    assert b.feed("PART 2 PRODUCTS") is None
    assert b.feed("2.01 MANUFACTURERS") == "2.01"
    assert b.feed("A. Text that ends on the page.") == "2.01.A"
    assert b.feed("0.1 mg/L as a monthly average.") == "2.01.A"  # continuation of a sentence from the previous page
    assert b.feed("4.2 MGD at peak flow.") == "2.01.A"  # Part 2 articles start with 2.
    assert b.feed("2.02 DESIGN CRITERIA") == "2.02"
    assert b.feed("END OF SECTION") is None


def test_letter_paren_marker_level() -> None:  # final review I4
    b = PathBuilder()
    b.start_section()
    assert [b.feed(t) for t in ["2.03 COUPLINGS", "E. Couplings:", "3. Rigid:", "a) Victaulic, Style 107.",
                                "b) Gruvlok."]] == ["2.03", "2.03.E", "2.03.E.3", "2.03.E.3.a", "2.03.E.3.b"]
