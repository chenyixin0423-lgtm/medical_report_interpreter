# Knowledge provenance and retrieval policy

## Current structured corpus

Sixteen JSON entries in `knowledge_base/curated/` supersede overlapping legacy notes for
live retrieval. Each includes bilingual identity/aliases, units, specimens, scope, overview,
optional high/low branches, caveats, fasting context, revision, source-check date/method and
actual MedlinePlus URLs. All have `clinical_review: not_performed`. See SOURCE_CHECKS.md.

`source_checked` means AI-assisted comparison of these short paraphrases with the opened
source page, not medical expert approval. No publication dates or clinical reviewers are
inferred from access dates. The linked public source is not claimed to have authored or
endorsed the application's summaries. No entire articles or medical thresholds were copied.

Chroma's `indicator_notes_v4` stores exact analyte documents. Selection then checks specimen,
analyte-specific units, computed direction and fasting context. Unsupported directional
branches are null, not filled by a model. Full hash-bound snapshots stay in history; only
selected passages are sent to Claude. Citation validation links each explanation to its
local summary, which itself retains the actual external URL. This is not claim-level auditing.

The content manifest pins LF-normalized file hashes. Missing/mismatched pins or invalid
schemas disable that curated entry; the legacy fallback, if present, remains unverified.
To update: read the actual source, compare every retained paraphrase and scope limitation,
update revision/check date, then update the pin. Do not update pins just to silence failures.
The manifest is not cryptographically signed; a trusted local maintainer can change it.

## Retained legacy corpus

The 26 text files in `knowledge_base/` were already present in the original prototype.
They do not include verifiable bibliographic citations, authorship dates or a clinical
review record. This refactor preserves them as **unverified project notes**. It does
not endorse their medical accuracy, reference intervals, causes or suggested actions.

The content inventory in `knowledge_base/provenance.json` covers all 26 entries. It records
unconfirmed applicability and specific concerns: unsourced reference/diagnostic thresholds,
near-certain diagnostic language, therapy advice, fixed recheck times and population claims.
GLU/HbA1c mention organizations but provide no traceable bibliography. BUN's urea terminology
also needs review. This inventory does not validate or correct the medical claims.

The app exposes the exact file ID, text and SHA-256 content hash for a retrieved note.
These identify the local artifact; a hash is not proof of medical authority. Generated
explanations cannot cite any source ID other than the note retrieved for that row.
All legacy notes are blocked from live explanation by `unverified_knowledge`. Their text
is inspectable only through an explicit UI opt-in. Synthetic preset links are not evidence
that a model used, or a professional approved, these notes. The model is instructed not to invent external citations, diagnose, prescribe or
assign a visit deadline. Schema and citation validation do not medically validate prose.

## Retrieval decisions

- The bilingual alias catalog maps known names to stable IDs. No fuzzy substring match.
- Chroma stores each complete short note keyed by its filename stem. Startup upserts
  current content and removes stale entries in the dedicated `indicator_notes_v4` collection.
  Previous collections remain untouched. JSON provenance metadata is stored alongside each
  Chroma document and returned with it, including `kb:<stem>` and `sha256:<full hash>` version.
  Missing inventory never upgrades trust; reviewer, review date and sources remain unknown.
  The loader never upgrades the legacy inventory to checked/reviewed; structured checked
  entries are separate. Legacy-only retrieval remains available for compatibility tests.
- Retrieval uses `collection.get(ids=[...])`, not nearest-neighbor ranking. The constant
  one-dimensional vector is a storage placeholder required by Chroma, not a semantic
  embedding. No embedding-model download or vector-quality claims are made.
- This is retrieval-augmented generation with exact entity retrieval. For 26 structured
  notes, determinism and explicit missing coverage are preferable to a broad semantic search.
- `IBIL` and `DBIL` are distinct analytes but share the existing `DBIL.txt` note.
  Urea is **not** treated as an alias of blood urea nitrogen.
- Differential counts and percentages can retrieve the same explanatory note. Different
  unit dimensions remain separate; repeated IDs within a report are excluded from trends.
- Unknown names get no note; the UI and model input explicitly state insufficient coverage.
- Knowledge reference intervals never override the interval printed in a report.

## Unit policy

The allowlist in `interpreter/units.py` covers SI scaling (g/dL ↔ g/L,
µmol/L ↔ mmol/L), count-volume identities (K/µL ↔ 10^9/L), fractions
(L/L ↔ %) and same-unit observations for U/L, fL, pg and normalized eGFR units.
These are dimensional identities, not clinical thresholds. Mass-to-molar, urea-to-BUN,
HbA1c method conversions, unsupported spellings and incompatible dimensions are refused.
Compatible units alone do not establish comparable specimen, assay or fasting conditions;
the user must check those conditions before interpreting the plot.

## Next steps for a clinical knowledge project

Expand only after inspecting attributable sources and preserving scoped paraphrases.
Add independent clinician review and evaluation cases. No critical-value
rules are shipped because this project has no verified rule set or clinical validation.
