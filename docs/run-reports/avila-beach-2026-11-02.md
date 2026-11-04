# Avila Beach run: what went in, and how each decision was made

The facts behind the real-document demo run. Every number comes from the run's own files, listed at the end.

| | |
|---|---|
| Run | `20261102T201101Z-17f3a0` on the hosted app (Azure Container Apps, Germany West Central) |
| Started | 2026-11-02 20:11 UTC; model calls ran for 17 min 8 s |
| Code | The frozen pipeline: tag [`phase4-freeze`](https://github.com/hemanthrayuduu/spec-review-copilot/tree/phase4-freeze), recorded in [`docs/FREEZE.md`](../FREEZE.md) |
| Result | 1,425 requirements, every one with an AI status; 0 failed calls; 0 silent drops |
| Cost | $2.04 for 1,514 model calls |

## 1. The document

| | |
|---|---|
| What | Avila Beach Community Services District (California): *Request for Proposals, Membrane Bioreactor System*. It is an MBR equipment preselection RFP with a scoring table and technical data forms. |
| Link | https://www.avilabeachcsd.org/files/fa6aff98f/Request+for+Proposals+Membrane+Bioreactor+System.pdf |
| File | `avila_beach_mbr_rfp.pdf`, 1.8 MB, 151 pages. 150 pages have a text layer, 1 is blank, and none needed OCR. |
| SHA-256 | `f318b73ab7d5c0fbc753248fe4272bf62836eb94c75c3ad1d3f8701635ed1843` |
| How it went in | One PDF, uploaded through the hosted app's Run a package page |
| Real or made up | Real and public. It is listed in [`data/sources.yaml`](../../data/sources.yaml) as `avila_beach_mbr_rfp`, role `demo`. It has no answer key, so this run shows behaviour, not accuracy. |

## 2. What the pipeline did, stage by stage

| Stage | What it does | On this run |
|---|---|---|
| Ingest | Text and tables with PyMuPDF and pdfplumber. Pages with no text go to Document Intelligence for OCR. | 151 pages, 2,229 text blocks, 272 repeated header and footer lines removed, 0 pages sent to OCR |
| Segment | Splits the document into sections by CSI MasterFormat numbering | 3 sections: front matter (pp. 1–75), plus two "sections" made from numbered sentences ("9 County streets…" and "16 Compaction of backfill…"). The RFP doesn't use CSI numbering, so this is the weak step. |
| Addenda, cross references | Merges addenda (newest text wins) and follows "per Section …" references | No addenda. 2 cross references could not be resolved. |
| Filter | Keeps the sections that matter to the product lines. When unsure, it keeps the section and logs why. | Kept all 3 sections (150 pages) |
| Candidates | Rules flag every sentence that might be a requirement | 2,021 candidate sentences |
| Extract (LLM) | Turns flagged sentences into structured requirements. Every candidate ends with an outcome. | 66 calls over 65 text groups. 1,460 became requirements, 522 not a requirement (with a reason), 39 sent to an engineer. 0 had no outcome. |
| Verify | Checks each record's quote and numbers against the page | 1,433 records. Quote check passed 1,430 (99.8%), number check 1,428 (99.7%). 1,425 kept, each with a valid page citation. |
| Permits (LLM) | Extracts discharge-permit limits | 1 call, no permit limits in this RFP |
| Brief | Deadlines, required forms, red flags and key requirements, each with its page | 63 deadlines, 17 forms, 23 red flags, 15 key requirements |
| Match | Rule check, then evidence search, then the LLM judge, then the confidence gate (section 5) | The rule check settled 0, so the judge decided all 1,425. 0 judge calls failed. The gate changed 0. |
| Coverage | Counts every page, block and candidate, so nothing is dropped unseen | 0 silent drops |

## 3. Results

| AI status | Items | Share |
|---|---|---|
| needs_engineer | 651 | 46% |
| not_applicable | 572 | 40% |
| comply | 111 | 8% |
| comply_with_clarification | 46 | 3% |
| deviation | 45 | 3% |

| What the decision rests on | Items |
|---|---|
| Real public sources only | 100 (6 comply, 1 clarification, 6 deviation, 87 needs engineer) |
| Real and synthetic | 412 |
| Synthetic only | 331 |
| No evidence cited (mostly not applicable) | 582 |

| Review group | Items |
|---|---|
| Performance & process | 149 |
| Design & materials | 515 |
| Testing & certification | 72 |
| Commercial & contract | 179 |
| Bidder qualification | 47 |
| Submittals & schedule | 463 |

**Good examples to open.** Each one rests only on real sources and links to the cited brochure page.

| Page | Requirement | AI status | Cited source |
|---|---|---|---|
| p.75 | All materials in contact with potable water must meet NSF/ANSI 61 | comply | SiC-FSM datasheet (2017), p.5; SiC Advanced Reuse brochure, p.1 |
| p.52 | Screening ahead of the MBR, 2 mm minimum | comply | CF100 and CF200 product pages (apertures include 2 mm) |
| p.52 | Maximum allowable MLSS in the bioreactor | comply_with_clarification | SiC MBR brochure, p.5 |

**Known misses on this run:**
- **p.21 and p.38, "minimum 0.025 MGD" (comply):** the judge used screen capacity for what is an MBR-system requirement.
- **p.125, head loss "6.5" with no units (deviation):** the reasoning is muddled.

## 4. Knowledge used

The judge searches one index, `idx-knowledge` in Azure AI Search, which holds **263 items**:

| Part | Items | What it is | Real or synthetic |
|---|---|---|---|
| Capability rows: [`data/knowledge/capabilities.csv`](../../data/knowledge/capabilities.csv) | 100 | One product line and parameter per row, with the value, source, page, quoted words and basis | 36 public (26 typical, 10 claim). 64 synthetic (60 guaranteed, 4 typical), each labeled `origin=synthetic`. |
| Past exceptions: [`data/knowledge/past_exceptions.csv`](../../data/knowledge/past_exceptions.csv) | 20 | Earlier bid exceptions and how they were answered | Fictional, and labeled so |
| Product document pages | 143 | Page chunks from the 18 public documents below | Public |

**Why there is synthetic data:** public brochures state typical values and claims, never guarantees. Warranties, standard terms and guaranteed performance had to be filled with fictional rows that cite a fictional document (`synthetic_product_data`). The rules:
- a synthetic row never replaces a public one;
- a synthetic row never covers nutrient effluent;
- the app marks synthetic evidence "SYNTHETIC (fictional, no source)".

**Public product documents** (from [`data/sources.yaml`](../../data/sources.yaml); "cited" counts citations in this run):

| Source | What it is | Cited | Link |
|---|---|---|---|
| `ovivo_sic_mbr_brochure` | SiC MBR brochure | 265 | [PDF](https://web.archive.org/web/20260405193905id_/https://www.chathamcountync.gov/home/showpublisheddocument/56841/637641221802170000) |
| `ovivo_cf100_band_screen` | CF100 band screen brochure | 212 | [PDF](https://web.archive.org/web/20260814092022id_/https://ovivo.getbynder.com/m/156b5204fdb7b4dd/original/CF100-Band-Screen.pdf) |
| `ovivo_sic_fsm_datasheet_2017` | SiC-FSM filter rack datasheet (2017) | 135 | [PDF](https://www.messe.de/apollo/surface_technology_2020/obs/Binary/A1045116/1045116_02324618.pdf) |
| `ovivo_cf100_cf200_2010` | CF100 and CF200 band screens brochure (2010) | 125 | [PDF](https://www.enviropro.co.uk/Docs/Ovivo_CF100CF200_ML/preview/CF100-and-CF200-band-screens.pdf) |
| `ovivo_reactor_clarifier` | Reactor clarifier (solids contact) brochure | 95 | [PDF](https://web.archive.org/web/20260814084014id_/https://ovivo.getbynder.com/m/4c5bd7cb07a22211/original/Reactor-Clarifier-Solids-Contact-Clarifiers.pdf) |
| `ovivo_filterboxx_sic_mbr` | FilterBoxx SiC MBR profile | 74 | [PDF](https://www.ovivowater.com/app/uploads/2026/09/FBFilterBoxxSiCMBR-11-2020-WEB.pdf) |
| `ovivo_cf100_page` | CF100 product page | 63 | [page](https://www.ovivowater.com/en/product/brackett-bosker-cf100-band-screen/) |
| `ovivo_carrousel_retrofits` | Carrousel retrofits | 39 | [PDF](https://web.archive.org/web/20260814085553id_/https://ovivo.getbynder.com/m/66ee637c5cbb79af/original/Carrousel-Retrofits.pdf) |
| `ovivo_carrousel_bnr_2025` | Carrousel BNR brochure (2025) | 25 | [PDF](https://municipal.ovivowater.com/app/uploads/2025/05/Ovivo-CARROUSEL-aeration-v250829-0940-DIGITAL-HIGH-1.pdf) |
| `ovivo_ringstrip` | RingStrip aeration systems | 25 | [PDF](https://web.archive.org/web/20260814085406id_/https://ovivo.getbynder.com/m/7b1e442522964f80/original/RingStrip-Systems.pdf) |
| `ovivo_carrousel_brochure` | Carrousel brochure | 24 | [PDF](https://web.archive.org/web/20220624215644id_/https://ovivo.getbynder.com/m/56d907ea2c275950/original/Carrousel-Brochure-0219-WEB.pdf) |
| `ovivo_ifas` | IFAS brochure | 16 | [PDF](https://web.archive.org/web/20260814101837id_/https://ovivo.getbynder.com/m/323a08695a1c77f7/original/Ovivo-IFAS_04-2022.pdf) |
| `ovivo_sic_case_southern_jackson` | SiC case study, Southern Jackson | 15 | [PDF](https://www.ovivowater.com/app/uploads/2026/09/SiC-Southern-Jackson.pdf) |
| `ovivo_sic_advanced_reuse` | SiC advanced reuse | 14 | [PDF](https://www.ovivowater.com/app/uploads/2026/09/SiC-Advanced-Reuse.pdf) |
| `ecoblox_title22_report_2025` | Title 22 engineering report with an ecoBLOX system (2025) | 12 | [PDF](https://files.ceqanet.lci.ca.gov/286629-2/attachment/sm52WBZkDkEuSbY-wVSXaZE_dapzsUSAwETpVV5p-3Rg2Ts8ouNvvT7l9TiQ3QkBXQJwpWvUgAAq9ZfS0) |
| `ovivo_cf200_page` | CF200 product page | 11 | [page](https://www.ovivowater.com/en/product/brackett-green-cf200-band-screen/) |
| `ovivo_gravity_clarifier` | Gravity clarifier highlight | 2 | [PDF](https://industrial.ovivowater.com/wp-content/uploads/2024/01/Technology-Highlight-Ovivo-industrial-GRAVITY-CLARIFIER-web.pdf) |
| `ovivo_pfas_highlight` | PFAS highlight | 0 | [PDF](https://industrial.ovivowater.com/wp-content/uploads/2024/01/Technology-Highlight-Ovivo-industrial-PFAS.pdf) |

Several Ovivo links are Internet Archive copies, because the original `ovivo.getbynder.com` host stopped resolving in October 2026.

**Citations in this run:** 2,871 citations across the 1,425 decisions, drawn from 199 distinct knowledge items.

| Kind of citation | Citations | Share |
|---|---|---|
| Public (brochure page chunks 825, public capability rows 327) | 1,152 | 40% |
| Synthetic capability rows | 1,679 | 58% |
| Fictional past exceptions | 40 | 2% |

## 5. How each decision was made

1. **Rule check** ([`spec_review/match/rules.py`](https://github.com/hemanthrayuduu/spec-review-copilot/blob/phase4-freeze/spec_review/match/rules.py)). A numeric requirement with exactly one matching capability row is decided by arithmetic, with no model. On Avila it settled none, so the judge decided all 1,425.
2. **Evidence search**, once per requirement ([`spec_review/match/evidence.py`](https://github.com/hemanthrayuduu/spec-review-copilot/blob/phase4-freeze/spec_review/match/evidence.py)):
   - **Query:** the section title, the requirement's parameter, and the requirement sentence.
   - **Keyword search:** BM25+ (`rank_bm25`) over the item texts, top 20.
   - **Vector search:** the query embedded with `text-embedding-3-small`, then cosine search in Azure AI Search, top 20.
   - **Fusion:** Reciprocal Rank Fusion with k = 60.
   - **Selection:** the judge gets up to 8 items, with 5 slots kept for capability rows, because they are the only evidence that can settle a status.
3. **The LLM judge** with prompt `judge_v4` (section 6). It decides in steps: first whether the requirement puts an obligation on the equipment, services or terms at all, then what the evidence supports. It returns a status, a reason, the evidence ids it relied on, and a confidence.
4. **Evidence rules, enforced in code after the model** ([`spec_review/match/judge.py`](https://github.com/hemanthrayuduu/spec-review-copilot/blob/phase4-freeze/spec_review/match/judge.py), `enforce`):
   - A comply, clarification or deviation with no cited evidence becomes needs_engineer.
   - It also becomes needs_engineer when the cited evidence is only claims, brochure text or past exceptions. Only guaranteed or typical capability rows can settle a status.
   - A phosphorus, nitrogen or ammonia limit is settled only by a capability row about that nutrient.
   - Evidence ids the model invents are dropped and logged.
5. **Confidence gate** ([`spec_review/match/gate.py`](https://github.com/hemanthrayuduu/spec-review-copilot/blob/phase4-freeze/spec_review/match/gate.py)). A model decision below 0.6 confidence becomes needs_engineer. It changed 0 items on this run.
6. **The engineer decides.** Every status is a draft until someone reviews it, and the outputs carry a DRAFT banner until then.

## 6. Prompts

Each prompt is a versioned file; a new version is a new file, never an edit. The scored versions are named in [`docs/FREEZE.md`](../FREEZE.md).

| Step | Prompt | Link |
|---|---|---|
| Requirement extraction | `extract_v2` | [spec_review/extract/prompts/extract_v2.md](https://github.com/hemanthrayuduu/spec-review-copilot/blob/phase4-freeze/spec_review/extract/prompts/extract_v2.md) |
| Permit limits | `permit_v1` | [spec_review/extract/prompts/permit_v1.md](https://github.com/hemanthrayuduu/spec-review-copilot/blob/phase4-freeze/spec_review/extract/prompts/permit_v1.md) |
| Compliance judge | `judge_v4` | [spec_review/match/prompts/judge_v4.md](https://github.com/hemanthrayuduu/spec-review-copilot/blob/phase4-freeze/spec_review/match/prompts/judge_v4.md) |

Earlier versions (`extract_v1`, `judge_v1` to `judge_v3`) are kept next to them. They were tuned on the dev package, Lakeview, only.

## 7. Models, services and cost

| | |
|---|---|
| Chat model | `gpt-5-mini`, version 2025-08-07, on Azure OpenAI (Azure AI Services `aif-specreview-demo-gwc`, Germany West Central). Reasoning effort: minimal for extraction, low for the judge. |
| Embeddings | `text-embedding-3-small` |
| Vector search | Azure AI Search `srch-specreview-demo-cac`, Free tier, Canada Central |
| OCR | Azure Document Intelligence `di-specreview-demo-gwc`, F0 (free). Not called on this run: no scanned pages. |
| All model calls | Through one client ([`spec_review/llm/client.py`](https://github.com/hemanthrayuduu/spec-review-copilot/blob/phase4-freeze/spec_review/llm/client.py)), which logs tokens, latency and cost for every call |

| Calls by prompt | Calls | Input tokens | Output tokens | Median latency | Cost |
|---|---|---|---|---|---|
| `judge_v4` | 1,425 | 2,950,836 | 400,507 | 3.1 s | $1.54 |
| `extract_v2` | 66 | 210,944 | 223,710 | 26.5 s | $0.50 |
| `permit_v1` | 1 | 821 | 516 | 5.1 s | $0.001 |
| Embeddings | 22 | 60,438 | – | 1.0 s | $0.001 |
| **Total** | **1,514** | | | | **$2.04** |

Prices used: $0.25 and $2.00 per million input and output tokens (gpt-5-mini, Global Standard), and $0.02 per million for embeddings. Search and OCR were $0, on free tiers.

## 8. Settings

This run used the frozen config (`docs/FREEZE.md`), with one change:
- **`MATCH_MAX_REQUIREMENTS` was raised from 1,000 to 2,000 on the hosted API** (owner decision, 2026-11-02).
- **Why:** the first upload, run `20261102T190242Z-319ebd`, found 1,402 requirements. That is over the 1,000 cost guard, so matching was skipped, and the run then stopped on a control-character bug that has since been fixed.

| Setting | Value |
|---|---|
| Prompts | `extract_v2`, `permit_v1`, `judge_v4` |
| Confidence gate | 0.6 |
| Quote check | 95% similarity to the page text |
| Extraction group size | 6,000 characters |
| Retrieval | keyword top 20, vector top 20, RRF k = 60, 8 items to the judge, 5 capability slots |
| Matching cost guard | 2,000 on this run (1,000 in the scored config) |

## 9. Weaknesses this run shows

1. **Section splitting.** It expects CSI numbering. This RFP became one 75-page front-matter block plus two fake sections, so the filter kept everything and extraction also pulled out procedure and background. That is why there are 1,425 items (Lakeview, at a similar size, has 319) and 40% not applicable.
2. **Thin public product data.** Public brochures give typical values and claims, never guarantees, and a claim can't settle a status. So 46% go to an engineer, and 58% of citations are synthetic rows.
3. **Judge mistakes.** See the known misses in section 3.
4. **Run-to-run variation.** The first upload extracted 1,402 requirements and this one 1,425. Fresh model replies vary a little; a cached rerun is identical.
5. **No answer key.** This shows how the tool behaves on a real document. Accuracy is measured on the labeled packages (Lakeview for dev, Cedar Falls for the held-out test): see [`docs/scorecards/`](../scorecards/README.md).

## 10. Where to find it

- **The run's files** are on the hosted share, `runs/20261102T201101Z-17f3a0/`. One JSON file per stage: `ingest`, `segment`, `addenda`, `xrefs`, `filter`, `candidates`, `extract`, `verify`, `permits`, `brief`, `match`, `coverage`. Also `llm_calls.jsonl` (one line per model call), `brief.md` and `requirements.xlsx`.
- **In the app:**
  - Checklist, with "Real sources only (100)".
  - Source viewer: each page citation opens the page with the line boxed.
  - Evidence links open the cited brochure page.
- **To reproduce it locally**, at about $2 and 17 minutes. Results vary slightly, because the model replies are fresh.

  ```
  MATCH_MAX_REQUIREMENTS=2000 uv run specreview run data/raw/demo/avila_beach_mbr_rfp
  ```

  Download the PDF from the link in section 1 first (`uv run python scripts/download_sources.py --role demo`).
