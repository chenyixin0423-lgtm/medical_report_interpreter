# Project Progress

## Overall Goal
A reliable, transparent, verifiable educational AI laboratory-report interpreter.
Not a clinically validated medical device or diagnostic service.

## Current Architecture
Single-process Streamlit UI (five pages), strict Pydantic models, two Claude calls
(extraction/explanation), exact canonical-ID retrieval from Chroma, session-first history,
optional SQLite and allowlisted unit conversion. See AGENTS.md for module responsibilities.
`abstention.py` assigns per-row decisions before model calls; `review.py` retains immutable
extraction plus explicit corrections. V4 records add original source snapshots and stable
occurrence IDs. `tracking.py` performs conservative local PDF text matches; Chroma v4
retains knowledge ID/version/review/source metadata with each note snapshot. `curated.py`
selects checked context by analyte, specimen, unit, range direction and fasting status.

## Completed Features
Verified in code at the start of this iteration: bilingual aliases; raw/checked/generated
data separation; numeric range checks and printed-flag conflicts; exact Chroma retrieval;
image/PDF validation; synthetic preset demo; history save/delete; numeric trends and
exclusions; five-page native UI; mocked API and AppTest tests; English documentation.
Task recovery instructions now exist in AGENTS.md and this file.
The previous iteration added four readiness states with actionable reasons, per-row input/output
gating, safe counts, correction forms/revalidation and non-destructive v2 history compatibility.
Existing Synthetic Demo, five pages, History and Trends pass tests.
The evidence/provenance iteration adds source-linked corrections and trends, model-facing
facts-only extraction schemas, PDF text-layer matching, per-entry inventory for all 26 notes,
provenance-aware abstention, compact evidence viewing and v2/v3 historical compatibility.
The structured-knowledge iteration adds 16 source-checked summaries, four lipid aliases,
explicit specimen/fasting extraction and correction fields, directional abstention,
manifest-pinned content, real source links and branch-only Claude context. Clinical expert
review remains not performed. Known urine/other results are excluded from blood trends.

## Current Task
2026-10-17: Structured medical knowledge refactor implemented and verified.
Started from clean commit 6684671. Read actual MedlinePlus pages for the 16 summaries
(14 distinct pages), recorded sources and limitations in docs/SOURCE_CHECKS.md. No clinical
review claimed, no thresholds copied, no paid API calls. This file is included in the local
implementation checkpoint; use `git log -1` to identify it. No Push or publication.

Previous evidence/provenance iteration:
2026-10-17: Evidence Tracking / Knowledge Provenance implementation and verification complete.
This file is included in the local implementation checkpoint (use `git log -1`). Started
from clean Git baseline 9b373ad. Source snapshots,
legacy migration, versioned provenance, live gating, evidence UI and synthetic tests are
implemented. No claim auditing, medical thresholds or large UI redesign added.

Previous iteration:
Implement per-indicator uncertainty and abstention in the actual processing flow, plus
human corrections, partial analysis, readiness counts and compatible history loading.
Stage 1 complete: fresh baseline 49 passed; local checkpoint `15473e6` created.
Stage 2 implementation and verification complete: structured readiness, gated model input, per-row output
rejection, correction-aware revalidation and v2 history compatibility are implemented.
Existing five-page UI now has readiness counts, reasons and a correction form.
Mixed-state UI correction flow passed AppTest, including an unconfirmed edit remaining
blocked, explicit confirmation allowing revalidation, and two other refused rows excluded.
Final docs are updated. The implementation commit containing this file is the stable
checkpoint; identify it with `git log -1` rather than inferring a hash from chat.

## Pending Tasks
No remaining implementation tasks within this iteration's scope.
Future work only when requested: clean-environment install check, visual review and an
explicitly authorized synthetic live-API smoke test. Independent clinician review, wider
analyte coverage and evaluated population/assay-specific knowledge remain future work.
Claim audit is deferred.

## Important Decisions
Evidence tracking and knowledge provenance are now explicitly authorized and implemented;
Claim Audit and multi-model review remain outside scope.
Keep the existing architecture. Readiness states are not medical risk categories.
An unusual value alone is not proof of OCR error. Model agreement is not verification.
All 26 legacy notes lack verifiable bibliographies/review. Original texts are preserved;
their unsupported clinical assertions are inventoried, not validated. They remain Unverified
and cannot support live explanations. Preset Demo has a separate path that cannot unlock
the live pipeline or Claude gateway. No source links, publication dates or reviewers invented.
Knowledge versions are content hashes, not publication dates. Hashes are not medical trust.
New structured summaries are source_checked, distinct from reviewed/clinical approval.
Only bounded public-page paraphrases are admitted. Source checks are AI-assisted and may
contain errors; metadata names the method and actual check date, not a publication date.
Legacy notes remain unchanged/unverified. Manifest mismatch disables curated admission;
this guards accidental edits, not malicious local tampering. Null directions stay blocked.
Unknown specimens block live explanations. Unknown fasting chooses general educational
context, never fasting criteria. BUN mg/dL only; HbA1c % only. No new conversions or targets.
Report text matches require unique complete lines; page means PDF page and location means
extracted-text line, not a visual bounding box. Unknown stays unknown. Human corrections
never overwrite original source snapshots or claim independent source verification.
Summary counts exclude refused rows. Arbitrary questions and model report summaries are
withheld to avoid bypassing the row gate. Structural checks cannot establish truth of prose.
Trends may display numeric facts even when missing intervals/notes block interpretation.

## Known Issues
Original code sent rejected rows to Claude; new pipeline now filters them. Original review
confirmation lacked editing; corrections now retain original extraction and require rechecking.
Old v2/v3 history is upgraded in memory; old explanations are withheld, files untouched.
Directory was not a Git repository when inspected; now initialized locally, no remote.
Previous verification documents lack a live API call, clean-install validation and browser
visual review. These are historical limitations, not checks completed in this iteration.
Plausible OCR errors without explicit ambiguity signals cannot be reliably detected.
There is no clinically reviewed corpus shipped. Source-checked summaries now permit limited
live explanation when context is sufficient. Blood count indices/differentials, eGFR and
other uncurated legacy indicators remain blocked. AST/HbA1c/TC/TG low and HDL high branches
are deliberately absent. No pediatric/pregnancy/disease-management targets are supported.
Image/scanned and multiline PDF locations remain unknown. Text-layer matching is not semantic
or OCR verification. No cryptographic audit log or malicious-local-history protection claimed.
Repeated analytes remain under review rather than guessing specimen/method matching.
Mismatched reference units require explicit review. Re-upload/review old reports to
regenerate gated explanations when adequate knowledge exists; v2/v3 files are not automatically rewritten.

## Test Results
Structured knowledge iteration baseline: **100 passed in 14.28s**.
First integration run: 98 passed / 2 failed (legacy-only inventory count and old UI source
label assertions). Retained legacy coverage through explicit legacy-only retrieval and
updated viewer expectations to show source_checked, never clinician approval.
New corpus routing suite: **11 passed in 16.22s**, including all 16 x 3 directional
combinations, unknown/wrong specimens, unit/context guards, partial correction, snapshots,
gateway branch filtering and unchecked-edit rejection.
Full regression including real-source Mock UI correction: **112 passed in 32.96s**.
Added known-urine trend separation regression; final full run: **113 passed in 32.87s**.
`compileall`, `pip check` and `git diff --check` passed. AppTest confirms existing pages,
synthetic demo, history/trends, source viewing and specimen correction unlocking a bounded
Mock Claude explanation. Loopback service on 8505 returned **HTTP 200 / ok** (PID 2928
at verification). No real Claude call, browser visual inspection or clinical evaluation.
No paid Claude calls; source-check network activity was limited to reading public pages.

Previous evidence/provenance iteration:
Evidence/provenance iteration baseline: **79 passed in 8.17s**.
First regression: 40 failures / 39 passed exposed a legacy migration guard treating new
constructors as legacy. Fixed the guard; existing 79 tests passed in 7.03s.
New source/provenance suite: 17 passed in 7.08s. Expanded regression: 96 passed / 1 failed
because an old history test compared the newest record to a different record with identical
values. Fixed it to select by record ID, preserving independent occurrence identity.
Full regression after that fix: **97 passed in 14.29s**. Additional defensive migration and
malformed-inventory cases added; final full regression: **100 passed in 14.74s**.
Exit code 0; the inherited pyreadline3 console destructor emitted an ignored Windows
handle warning after the summary (also present historically), not an application test failure.
Syntax compilation and dependency checks passed. AppTest exercises evidence display,
synthetic note opt-in, live source insufficiency and matched PDF source details. No paid API.
Sandboxed startup on port 8503 did not expose a healthy endpoint; retried a hidden,
loopback-only process on 8504 through the approved execution path. Approved local health
request returned **HTTP 200 / ok**; sandboxed local requests were blocked. Service PID at
verification was 58552. No browser screenshot/visual review or real Claude call was performed.

Previous uncertainty iteration:
Fresh baseline: `.venv/Scripts/python -m pytest -q` — 49 passed in 6.99s.
First post-change regression: 45 passed / 4 failed because old assertions assumed all rows
were analyzed, unsupported HGB units were trended, and only four metrics existed. These
tests have been updated to the new contract, retaining their original safety coverage.
First new pipeline suite: 22 passed / 1 failed; missing units also triggered an overly broad
reference-ambiguity reason. Rule narrowed to known, matching units; rerun passed.
Intermediate full regression: 72 passed in 8.34s.
Targeted pipeline + mixed UI correction tests: 24 passed in 5.48s.
Final full suite: **79 passed in 8.50s** (30 more cases than baseline).
Syntax compilation passed; dependency check reported no broken requirements.
Updated Streamlit service started on localhost:8502; health returned HTTP 200 / ok.
No paid model calls. UI behavior verified through AppTest, not browser screenshots.

## Next Steps
1. On resumption read this file, inspect `git status` / `git log -2`, then relevant code.
2. Run `.venv/Scripts/python -m pytest -q` before extending the readiness policy.
3. Pick a requested follow-up from Pending Tasks; do not automatically build deferred systems.
