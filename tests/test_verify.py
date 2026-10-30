import pytest

from spec_review.extract.verify import clean_quote, locate, number_check, unit_present
from spec_review.models import Block
from tests.block_fixtures import blocks_from


def blk(text: str, page: int, path: str | None = None) -> Block:
    return Block(doc_id="rfp", page=page, bbox=(72, 100, 540, 112), text=text, kind="list_item", paragraph_path=path)


def test_quote_located_across_unicode_variants() -> None:
    blocks = blocks_from(["B. Provide “overflow” weirs – type 316 stainless steel."])
    assert locate('Provide "overﬂow" weirs - type 316 stainless steel.', blocks) == (0, 0)


def test_rendered_prefix_in_quote_is_stripped() -> None:
    assert clean_quote("[p134] 2.03.B B. Membrane modules shall be PVDF.") == "Membrane modules shall be PVDF."
    assert clean_quote("3.2 Proposals shall be delivered sealed.") == "Proposals shall be delivered sealed."
    assert clean_quote("0.1 mg/L is the monthly limit.") == "0.1 mg/L is the monthly limit."


def test_quote_across_blocks_and_pages() -> None:
    blocks = [blk("7.2 The selected Supplier shall furnish a performance bond in the amount of 100 percent of the", 3),
              blk("contract price.", 4)]
    assert locate("The selected Supplier shall furnish a performance bond in the amount of 100 percent "
                  "of the contract price.", blocks) == (0, 1)


def test_long_quote_does_not_match_a_short_block() -> None:
    blocks = [blk("contract price.", 4)]
    assert locate("The selected Supplier shall furnish a bond of 100 percent of the contract price.", blocks) is None


def test_invented_quote_is_not_located() -> None:
    assert locate("Membranes shall be ceramic.", blocks_from(["A. Membranes shall be PVDF."])) is None


def test_duplicate_sentence_prefers_the_candidate_block() -> None:
    blocks = [blk("A. Submit shop drawings.", 2, "1.03.A"), blk("A. Submit shop drawings.", 5, "1.05.A")]
    assert locate("Submit shop drawings.", blocks) == (0, 0)
    assert locate("Submit shop drawings.", blocks, prefer={1}) == (1, 1)


@pytest.mark.parametrize("value,text,ok", [
    ("3", "at least three (3) installations", True), ("1500", "$1,500 per day", True),
    ("2 to 4", "between 2 and 4 psi", True), ("0.2", "not exceeding 0.1 mg/L", False), (None, "anything", True),
    ("PVDF", "Membranes shall be PVDF.", True)])
def test_number_check(value: str | None, text: str, ok: bool) -> None:
    assert number_check(value, text) is ok


def test_unit_present() -> None:
    assert unit_present("mg/L", "not exceeding 0.1 MG/L") and unit_present(None, "x")
    assert not unit_present("gpm", "Flux shall not exceed 15 gfd.")
