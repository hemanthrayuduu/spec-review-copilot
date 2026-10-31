# Knowledge base

The manufacturer's capabilities that Phase 2 checks each requirement against (design: `docs/superpowers/specs/2026-10-31-phase-2-design.md`, section 7.2).

| File | What it holds |
|---|---|
| `capabilities.csv` | One row per product line and parameter. `origin` says where each row comes from. |
| `past_exceptions.csv` | 20 past bid exceptions and clarifications. **Every row is fictional.** |

## Public and synthetic rows

- **`origin=public`:**
  - These rows are copied from the manufacturer's public literature listed in `data/sources.yaml`.
  - Each one cites its URL and PDF page, and `source_text` holds the words on that page.
  - `basis` is taken as the document words it: `guaranteed`, `typical` or `claim`.
- **`origin=synthetic`:**
  - These rows are **fictional demo data, not from Ovivo or any real manufacturer**. They fill gaps that no public source covers, such as wash water, drive torque, MBR design flux, warranties and standard terms of sale.
  - Values follow typical industry practice.
  - They cite the fictional document `synthetic_product_data`, whose every page says so.
  - A synthetic row never shares a product line and parameter with a public row, and no synthetic row covers nutrient effluent (phosphorus, nitrogen or ammonia).

Only `guaranteed` rows with `match_terms` can let a numeric rule decide a status. Claims never settle a status.

## Commands

```
uv run python scripts/download_sources.py --role knowledge   # the public sources, into data/raw/knowledge/
uv run python scripts/make_knowledge.py                       # renders the synthetic document from capabilities.csv
uv run specreview knowledge check                             # guards, plus every quote found on its cited page
```
