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
2026-10-17: Claim Audit restored from retained Codex log patches after the earlier
52ea36e / 74a87ba commit objects were no longer present. Existing baseline 9ab28e1
passed git fsck and had no uncommitted changes; no old history was rewritten.
Recovery source: Codex rollout 019fcaac-21b1-7223-b0ce-56ef56bb9b64, ten apply_patch
records on lines 1019-1158. Patches were replayed in an independent local clone at
`.local_data/claim-audit-recovery-20261017`, not directly over the official checkout.
All 11 restored files matched the historical Git blob hashes, including the final
74a87ba PROGRESS.md contents. The recovery clone retains that exact historical state.
Its 37 Python files passed in-memory syntax compilation; pip check passed using the
existing project's Python 3.10 virtual environment (not a fresh dependency install).
Recovery-directory regression: **136 passed in 37.27s**, no paid API calls.
Only after passing those checks was the clean, unchanged official checkout updated.
All 11 hashes matched again after transfer. This recovery entry intentionally changes
PROGRESS.md from its historical hash; the other ten files remain byte-content equivalent
under Git's line-ending normalization. No feature redesign or knowledge changes made.
Recovery copies and existing backups are retained; no Push or remote change authorized.
Official-directory regression: **136 passed in 38.56s**, exit 0. The inherited pyreadline3
console destructor emitted an ignored Windows handle warning after the passing summary;
no test failed. Official in-memory syntax compilation (37 files), pip check and
git diff --check also passed. Pre-commit git fsck --full returned exit 0, without
the previous device/index/object errors. A new ordinary local commit will record this
recovery; no original commit ID recreation or fsync-disabling workaround is required.
Use git log -1 for the recovery checkpoint and rerun git fsck after committing.

Previous Claim Audit implementation (historical records, not current recovery checks):
2026-10-17: Claim Audit implementation and verification complete; included in the local
checkpoint containing this file (identify with `git log -1`). No Push.
Started from clean commit 9ab28e1; read instructions, actual models, pipeline, gateway,
UI and tests. Baseline: 113 passed in 32.64s. No corpus changes or UI redesign.
`audit.py` parses sentence claims and verifies closed-form report facts or complete
applicable selected knowledge context. Unsupported/Contradicted/Needs Review outcomes
retain reasons and occurrence links; supported knowledge context retains ID/version/text.
New model output uses atomic claims; legacy text is also audited, never silently omitted.
Audit is recomputed on record creation, history load and display; no saved verdict is trusted.
Contradicted prose is withheld and unconfirmed prose labeled. Demo supplies preset fact
claims. No semantic model or additional API call is used. Source matching is not clinical truth.

Previous structured knowledge iteration:
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
Broader semantic entailment evaluation is deferred; deterministic Claim Audit is implemented.

## Important Decisions
Evidence tracking, knowledge provenance and deterministic Claim Audit are implemented.
Multi-model review remains outside scope. This iteration does not expand medical knowledge.
Only closed-form facts and complete applicable educational context can receive Supported.
Free-form paraphrases need review; English safety heuristics can overflag or miss wording,
but unfamiliar prose is never automatically Supported. These outcomes are not risk labels.
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
Claim Audit is conservative, not general semantic entailment or medical truth verification.
Unparsed factual errors may receive Needs Review instead of Contradicted; safety keyword
checks may overflag negations. No claim-unit conversions are inferred. Context matching
preserves the entire selected block and caveats, not arbitrary sentence-level paraphrases.
Original extraction can still be wrong even when a claim matches its reviewed fields.
Rejected extra-row explanations are discarded with a report notice, not attached to a
fabricated observation. Audit/raw generated text remains in opt-in local history, not logs.
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
Claim Audit iteration: baseline 113 passed in 32.64s; initial implementation retained all
113 existing tests (33.31s). Initial new synthetic audit suite: 22 passed in 7.92s.
Final full regression: **136 passed in 37.35s** (23 new audit cases). Includes real local
Chroma context checks, mocked Claude tool output, correction/history recomputation,
legacy v4 compatibility, ignored forged saved verdicts, partial abstention, synthetic
presets and AppTest contradiction withholding. No paid model calls.
`pip check` and `git diff --check` passed. `compileall` did not fully pass: repeated
OSError [Errno 22] writing test_audit's bytecode cache, including an unsandboxed retry;
a separate cache-prefix attempt also had I/O errors. Cause not established. Pytest
successfully imported/executed all modules and tests. No source syntax failure reported.
Hidden loopback Streamlit service on port 8506 started (PID 22340 at verification),
health endpoint **HTTP 200 / ok**. UI verified via AppTest, not browser screenshots.
Git staging twice failed with `fsync / Bad file descriptor`. A command-local
`-c core.fsync=none -c core.fsyncObjectFiles=false` workaround allowed staging; no
persistent Git configuration changed. Use the same scoped flags for this checkpoint,
then inspect commit/object integrity. This does not resolve the underlying filesystem issue.
Implementation committed locally as `52ea36e`; `git show HEAD` succeeded and the working
tree was clean. `git fsck --no-reflogs` and an approved `git fsck --full` both returned
exit 1 without diagnostics, so full repository integrity verification is **not confirmed**.
Do not interpret the successful commit as resolution of that environment limitation.

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
4. Before broadening claim acceptance, add an independently labeled synthetic/adversarial
   evaluation set for paraphrases, negation, compound claims and multilingual wording.
   Do not promote heuristic matches to medical entailment. Investigate the local bytecode
   cache I/O issue separately; do not change clinical logic to address environment errors.
