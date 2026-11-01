"""All five outputs for one run (spec 8.16), written to runs/<run_id>/outputs/."""

from pathlib import Path

from spec_review.models import ContractModel
from spec_review.outputs.addendum_diff import write_addendum_diff
from spec_review.outputs.compliance_xlsx import write_compliance_matrix
from spec_review.outputs.letter_docx import write_letter
from spec_review.outputs.markup_pdf import write_markup
from spec_review.outputs.questions import write_questions
from spec_review.review.run_view import RunView

OUTPUT_NAMES = ("compliance_matrix.xlsx", "exceptions_and_clarifications.docx", "clarification_questions.md",
                "addendum_diff.md")


class OutputsResult(ContractModel):
    files: list[str] = []  # names inside the outputs folder
    skipped: list[str] = []
    draft_banner: str | None = None


def write_outputs(view: RunView, out_dir: Path) -> OutputsResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_compliance_matrix(view, out_dir / OUTPUT_NAMES[0])
    write_letter(view, out_dir / OUTPUT_NAMES[1])
    write_questions(view, out_dir / OUTPUT_NAMES[2])
    write_addendum_diff(view, out_dir / OUTPUT_NAMES[3])
    files, skipped = list(OUTPUT_NAMES), []
    if view.info is None:
        skipped.append("no run.json, so the package folder is unknown: the marked-up PDF was skipped")
    else:
        marked, skipped = write_markup(view, Path(view.info.package_dir), out_dir)
        files += [p.name for p in marked]
    return OutputsResult(files=files, skipped=skipped, draft_banner=view.draft_banner)
