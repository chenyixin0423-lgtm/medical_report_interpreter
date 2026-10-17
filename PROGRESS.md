# Project Progress

## Overall Goal
A reliable, transparent, verifiable educational AI laboratory-report interpreter.
Not a clinically validated medical device or diagnostic service.

## Current Architecture
Single-process Streamlit UI (five pages), strict Pydantic models, two Claude calls
(extraction/explanation), exact canonical-ID retrieval from Chroma, session-first history,
optional SQLite and allowlisted unit conversion. See AGENTS.md for module responsibilities.

## Completed Features
Verified in code at the start of this iteration: bilingual aliases; raw/checked/generated
data separation; numeric range checks and printed-flag conflicts; exact Chroma retrieval;
image/PDF validation; synthetic preset demo; history save/delete; numeric trends and
exclusions; five-page native UI; mocked API and AppTest tests; English documentation.
Task recovery instructions now exist in AGENTS.md and this file.

## Current Task
Implement per-indicator uncertainty and abstention in the actual processing flow, plus
human corrections, partial analysis, readiness counts and compatible history loading.
Stage 1 complete: inventory and recovery documents created; fresh baseline is 49 passed.
Local Git initialized with the existing configured author; preparing audited baseline commit.

## Pending Tasks
- Structured interpretable / needs_review / insufficient_evidence / unsupported decisions.
- Reuse range/alias/unit checks and add deterministic interpretation gating.
- Exclude rejected rows from model inputs and definite summary counts.
- Editable review with immutable extraction and explicit correction/revalidation.
- Preserve synthetic demo, existing pages, trends and older v2 history records.
- Integration tests, docs, final verification and local Git commit.

## Important Decisions
No full Evidence Tracking, Knowledge Provenance or Claim Audit system in this iteration.
Keep the existing architecture. Readiness states are not medical risk categories.
An unusual value alone is not proof of OCR error. Model agreement is not verification.
Existing knowledge notes lack clinical review; eligible explanations remain educational.

## Known Issues
Current code sends all checked rows to Claude, including missing-knowledge/unknown rows;
existing warnings do not actually abstain. Review UI offers confirmation but no corrections.
Existing historical records have schema version 2 and no readiness state.
Directory was not a Git repository when inspected; now initialized locally, no remote.
Previous verification documents lack a live API call, clean-install validation and browser
visual review. These are historical limitations, not checks completed in this iteration.

## Test Results
Fresh baseline: `.venv/Scripts/python -m pytest -q` — 49 passed in 6.99s.

## Next Steps
1. Check baseline pytest result and initialize local Git with audited non-sensitive files.
2. Implement decisions and correction-aware pipeline, then run targeted integration tests.
3. Update this file at each stable stage; finish with full tests and local commits, no push.
