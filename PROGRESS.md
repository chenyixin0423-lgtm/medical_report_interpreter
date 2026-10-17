# Project Progress

## Overall Goal
A reliable, transparent, verifiable educational AI laboratory-report interpreter.
Not a clinically validated medical device or diagnostic service.

## Current Architecture
Single-process Streamlit UI (five pages), strict Pydantic models, two Claude calls
(extraction/explanation), exact canonical-ID retrieval from Chroma, session-first history,
optional SQLite and allowlisted unit conversion. See AGENTS.md for module responsibilities.
`abstention.py` assigns per-row decisions before model calls; `review.py` retains immutable
extraction plus explicit corrections. V3 records persist decisions and correction metadata.

## Completed Features
Verified in code at the start of this iteration: bilingual aliases; raw/checked/generated
data separation; numeric range checks and printed-flag conflicts; exact Chroma retrieval;
image/PDF validation; synthetic preset demo; history save/delete; numeric trends and
exclusions; five-page native UI; mocked API and AppTest tests; English documentation.
Task recovery instructions now exist in AGENTS.md and this file.
This iteration adds four readiness states with actionable reasons, per-row input/output
gating, safe counts, correction forms/revalidation and non-destructive v2 history compatibility.
Existing Synthetic Demo, five pages, History and Trends pass tests.

## Current Task
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
explicitly authorized synthetic live-API smoke test. Full provenance/claim audit is deferred.

## Important Decisions
No full Evidence Tracking, Knowledge Provenance or Claim Audit system in this iteration.
Keep the existing architecture. Readiness states are not medical risk categories.
An unusual value alone is not proof of OCR error. Model agreement is not verification.
Existing knowledge notes lack clinical review; eligible explanations remain educational.
Summary counts exclude refused rows. Arbitrary questions and model report summaries are
withheld to avoid bypassing the row gate. Structural checks cannot establish truth of prose.
Trends may display numeric facts even when missing intervals/notes block interpretation.

## Known Issues
Original code sent rejected rows to Claude; new pipeline now filters them. Original review
confirmation lacked editing; corrections now retain original extraction and require rechecking.
Old v2 history is upgraded in memory; its un-gated explanations are withheld, files untouched.
Directory was not a Git repository when inspected; now initialized locally, no remote.
Previous verification documents lack a live API call, clean-install validation and browser
visual review. These are historical limitations, not checks completed in this iteration.
Plausible OCR errors without explicit ambiguity signals cannot be reliably detected.
Knowledge checks are basic identity/header/content checks, not clinical evidence review.
Repeated analytes remain under review rather than guessing specimen/method matching.
Mismatched reference units require explicit review. Re-upload/review old reports to
regenerate gated explanations; v2 files are not automatically rewritten.

## Test Results
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
