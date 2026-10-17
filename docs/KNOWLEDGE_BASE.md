# Knowledge provenance and retrieval policy

The 26 text files in `knowledge_base/` were already present in the original prototype.
They do not include verifiable bibliographic citations, authorship dates or a clinical
review record. This refactor preserves them as **unverified project notes**. It does
not endorse their medical accuracy, reference intervals, causes or suggested actions.

The app exposes the exact file ID, text and SHA-256 content hash for a retrieved note.
These identify the local artifact; a hash is not proof of medical authority. Generated
explanations cannot cite any source ID other than the note retrieved for that row.
The model is instructed not to invent external citations, diagnose, prescribe or
assign a visit deadline. Schema and citation validation do not medically validate prose.

## Retrieval decisions

- The bilingual alias catalog maps known names to stable IDs. No fuzzy substring match.
- Chroma stores each complete short note keyed by its filename stem. Startup upserts
  current content and removes stale entries in the dedicated `indicator_notes_v2` collection.
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

Replace or review notes with attributable, licensed primary sources, versioned dates,
applicable populations and units. Add clinician-reviewed evaluation cases. No critical-value
rules are shipped because this project has no verified rule set or clinical validation.
