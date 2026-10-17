# Project instructions

## Start / resume every session
Read `PROGRESS.md` first, then inspect Git status and the relevant actual code. Do not
infer completion from chat history. Run the relevant tests before changing assumptions.
Keep progress notes factual; record incomplete work and the next executable step.

## Goal and architecture
Build a reliable, transparent and verifiable AI medical-report interpretation prototype.
Keep the single-process Streamlit / Claude / ChromaDB / Pydantic architecture. Avoid
unnecessary infrastructure, frameworks, services or speculative abstractions.

- `app.py`, `interpreter/ui.py`: entry point and five native Streamlit pages.
- `models.py`: strict raw, checked and generated data contracts.
- `catalog.py`, `units.py`, `validation.py`: aliases, compatible units and deterministic checks.
- `knowledge.py`: exact-ID retrieval from 26 existing project notes using Chroma.
- `llm.py`, `pipeline.py`: schema-bound Claude calls and processing orchestration.
- `storage.py`, `trends.py`: optional local SQLite, session history and numeric trends.
- `security.py`, `demo.py`: bounded uploads and synthetic preset examples.
- `tests/`: deterministic, real local Chroma, mock Claude and Streamlit AppTest coverage.

## Boundaries
Never provide definitive diagnoses, invent medical knowledge/sources, or claim clinical
validation. Unverified project notes are not clinical evidence. Readiness for educational
explanation is not normality, safety or medical risk. Preserve raw facts and uncertainty.
Never commit real patient reports, uploads, API keys, local histories or other secrets.
Do not print credentials or sensitive records in logs. Keep live history opt-in.

## Development and verification
Reuse existing normalization, range checks, conversion and RAG logic. Add programmatic
abstention rather than relying on confidence percentages or prompt instructions alone.
Preserve Synthetic Demo, History, Trends and all five pages. Use synthetic fixtures and
mock model calls; avoid paid API calls unless needed and authorized.
After changes run relevant tests; before a stable checkpoint run the full suite using
`.\.venv\Scripts\python -m pytest -q` (Windows). Record actual results in PROGRESS.md.
Update PROGRESS.md after every major stage, including failures, decisions and next steps.
Current scope: task recovery and uncertainty/abstention. Do not add full evidence
tracking, provenance infrastructure, claim auditing or a large UI redesign.

## Git
Create local commits at tested stable stages. Inspect staged files and exclusions before
committing. Never automatically push, publish or create a remote repository. Do not
delete unknown files or discard user edits. Do not invent Git author identity; use the
configured identity, or report a missing identity if it prevents committing.
