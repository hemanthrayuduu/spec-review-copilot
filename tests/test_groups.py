from spec_review.extract.candidates import section_candidates
from spec_review.extract.groups import Group, article_of, build_groups, render_candidates, render_text
from spec_review.models import Block, Section


def blk(text: str, page: int = 134, kind: str = "list_item", path: str | None = None) -> Block:
    return Block(doc_id="specs", page=page, bbox=(72, 100, 540, 112), text=text, kind=kind,  # type: ignore[arg-type]
                 paragraph_path=path)


def section_of(blocks: list[Block], style: str = "csi") -> Section:
    return Section(section_id="specs#8", number="46 61 00", title="MEMBRANE FILTRATION EQUIPMENT",
                   numbering_style=style, doc_id="specs", page_start=134, page_end=136,  # type: ignore[arg-type]
                   blocks=blocks)


def groups_of(blocks: list[Block], max_chars: int = 6000, style: str = "csi") -> list[Group]:
    s = section_of(blocks, style)
    return build_groups(s, section_candidates(s), max_chars=max_chars)


def test_article_of() -> None:
    assert article_of("2.03.B.4", "csi") == "2.03" and article_of("2.03", "csi") == "2.03"
    assert article_of("3.2", "front_end") == "3" and article_of(None, "csi") is None


def test_groups_follow_articles_and_skip_candidate_free_ones() -> None:
    gs = groups_of([blk("1.01 SUMMARY", kind="heading", path="1.01"),
                    blk("A. Section includes membranes.", path="1.01.A"),
                    blk("2.01 MANUFACTURERS", kind="heading", path="2.01"),
                    blk("A. Membranes shall be PVDF.", path="2.01.A"),
                    blk("B. Modules shall be removable.", path="2.01.B"),
                    blk("2.02 DESIGN", kind="heading", path="2.02"),
                    blk("A. Flux shall not exceed 15 gfd.", path="2.02.A")])
    assert [g.group_id for g in gs] == ["specs#8:g1", "specs#8:g2", "specs#8:g3"]
    assert [len(g.candidates) for g in gs] == [1, 2, 1]
    assert gs[1].blocks[0].text == "2.01 MANUFACTURERS"


def test_group_without_candidates_is_dropped() -> None:
    gs = groups_of([blk("1.01 SUMMARY", kind="heading", path="1.01"), blk("2.03 MATERIALS", kind="heading", path="2.03"),
                    blk("A. Gaskets shall be EPDM.", path="2.03.A")])
    assert [g.group_id for g in gs] == ["specs#8:g1"] and gs[0].blocks[0].text == "2.03 MATERIALS"


def test_long_article_splits_at_block_boundaries() -> None:
    items = [blk(f"{chr(65 + i)}. Item {i} shall be stainless steel type 316 throughout.", path=f"2.03.{chr(65 + i)}")
             for i in range(10)]
    gs = groups_of(items, max_chars=200)
    assert len(gs) > 1 and all(sum(len(b.text) for b in g.blocks) <= 200 for g in gs)
    assert sum(len(g.candidates) for g in gs) == 10


def test_table_run_stays_with_its_lead_in() -> None:
    rows = [blk(f"Parameter: P{i}; Value: {i}.0 MGD", kind="table_row", path="2.02.B") for i in range(39)]
    gs = groups_of([blk("A. Supply the system.", path="2.02.A"), blk("B. Design criteria:", path="2.02.B"), *rows],
                   max_chars=1200)
    table_group = next(g for g in gs if any(b.kind == "table_row" for b in g.blocks))
    assert sum(b.kind == "table_row" for b in table_group.blocks) == 39
    assert table_group.blocks[0].text == "B. Design criteria:"


def test_render_lines() -> None:
    (g,) = groups_of([blk("B. Membrane modules shall be PVDF.", path="2.03.B")])
    assert render_text(g).splitlines()[0] == "[p134] 2.03.B B. Membrane modules shall be PVDF."
    assert render_candidates(g) == "specs#8:c1: Membrane modules shall be PVDF."
