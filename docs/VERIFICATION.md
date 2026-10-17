# Verification record

Date: **2026-10-17** (Asia/Shanghai).

## Current iteration: Claim Audit

- Baseline: **113 passed in 32.64s**; final: **136 passed in 37.35s**, exit 0.
- 23 added synthetic cases cover values, units, status, invented indicators, diagnosis,
  advice, overreach, exact-context support versus citation-only claims, correction/history
  links, forged saved labels, legacy prose, partial refusal, mock tool output and Demo.
- AppTest verifies mixed audit outcomes and that contradicted text is not displayed;
  existing five pages, history, trends and evidence viewer regressions pass.
- `pip check` and `git diff --check` passed. `compileall` remains incomplete due to repeated
  bytecode-cache OSError [Errno 22], including unsandboxed retry; alternate-cache run also
  encountered I/O errors. Cause unresolved. Pytest imported and executed the test module.
- Hidden loopback service on `127.0.0.1:8506` returned **HTTP 200 / ok** (PID 22340).
- No paid Claude call, semantic-audit model, corpus expansion, clinical evaluation or
  browser screenshot. Supported means deterministic consistency, not medical truth.

## Previous iteration: structured source-checked knowledge

- Baseline: **100 passed in 14.28s**. Final full suite: **113 passed in 32.87s**, exit 0.
- New corpus tests include all 16 entries across high/low/within-range directions, real local
  Chroma retrieval, supported units/specimens, fasting caveats, null branches, source snapshots,
  partial correction, selected-only model payloads, manifest mismatch and urine trend exclusion.
- Actual MedlinePlus pages were inspected for the 16 summaries (14 distinct pages). URLs and
  checking scope are in SOURCE_CHECKS.md. AI-assisted source checking is not clinician review.
- AppTest verifies source-checked live workflow with a Mock: unknown specimen blocks, a
  confirmed correction revalidates and permits an explanation, real source links appear, and
  the original snapshot is retained. Existing five pages, Demo, History and Trends still pass.
- First integration run: 98 passed / 2 failed because previous tests assumed every production
  note was unverified. Preserved legacy-only tests and updated production-view expectations.
- `compileall`, `pip check` and `git diff --check` passed.
- Hidden loopback Streamlit service started on `127.0.0.1:8505`; health **HTTP 200 / ok**.
- No paid Claude calls, clean installation, screenshot review, medical accuracy benchmark or
  clinical evaluation. Historical Windows pyreadline3 warnings occurred in some earlier runs;
  the final pytest process exited 0. No Push or deployment.

## Previous iteration: evidence tracking and knowledge provenance

- Baseline: **79 passed in 8.17s**. Final: **100 passed in 14.74s**, exit code 0.
- `compileall`, `pip check` and `git diff --check` passed. Git emits normal LF/CRLF notices.
- Fixed an initial legacy migration guard regression; updated a history assertion to compare
  independent records by ID rather than identical values. Details retained in PROGRESS.md.
- Real local Chroma tests verify all 26 IDs, content versions, unverified sources, refresh,
  alias linkage and historical snapshots. No legacy note content was modified.
- Synthetic PDF bytes plus mock extraction exercise actual pypdf matching, source persistence,
  duplicate/inexact/multiline rejection, unknown image locations and model-field rejection.
- Tests cover original/corrected association, conversion links, metadata corruption, v2/v3
  migration, malformed legacy records and inventory, and no live bypass from Demo presets.
- AppTest verifies the evidence viewer, source metadata, opt-in retained notes, real unverified
  corpus abstention, all five existing pages, mixed-state corrections, History and Trends.
- Hidden local Streamlit service started on `127.0.0.1:8504`. Approved health request:
  **HTTP 200 / ok**. Sandboxed startup/health attempts were unsuccessful.
- A post-summary ignored pyreadline3 Windows console-handle warning occurred; pytest exited 0.
- No paid API calls, external medical-source validation, browser screenshot review, clinical
  validation or clean-environment installation. All shipped medical notes remain Unverified.
- Local commit only; no push, remote creation or deployment.

## Previous iteration: uncertainty and task recovery

- Fresh baseline before changes: **49 passed in 6.99s**.
- Final full regression: **79 passed in 8.50s**; no failed tests.
- `compileall` succeeded; `pip check`: no broken requirements found.
- Updated service started at `127.0.0.1:8502`; health returned **HTTP 200 / ok**.
- Streamlit AppTest exercised all existing pages and mixed-state correction: unconfirmed
  edits stay blocked, confirmed edits are revalidated, refused rows stay out of model inputs,
  and summary counts exclude refused abnormalities.
- Added synthetic tests cover missing/ambiguous values, unsupported/incompatible units,
  missing/reversed/contextual intervals, ambiguous/unknown names, irrelevant/missing notes,
  duplicate measurements, stale/conflicting corrections, inconsistent derived data,
  generated row/source conflicts, partial acceptance and read-only v2 history migration.
- No paid Claude calls, browser visual review, clinical evaluation or clean installation
  were performed this iteration. Earlier browser limitations below are historical.
- Recovery docs: AGENTS.md and PROGRESS.md. Local baseline commit: `15473e6`;
  implementation checkpoint is recorded in local Git history. No push or remote creation.

The following sections record the preceding refactor's verification baseline.

## Executed checks

| Check | Result |
| --- | --- |
| pytest core + integration + UI suite | 49 passed, no failed tests |
| `python -m compileall -q app.py analyzer.py history.py rag.py interpreter tests` | Passed |
| `python -m pip check` | No broken requirements found |
| Streamlit service startup | Started on `127.0.0.1:8501` |
| HTTP `/_stcore/health` | HTTP 200, body `ok` |
| Five-page synthetic navigation | Passed with Streamlit AppTest |
| Five-page live empty states | Passed with Streamlit AppTest |
| Mandatory fact review and mocked live explanation flow | Passed with Streamlit AppTest |
| Opt-in SQLite save/delete from UI | Passed with Streamlit AppTest |
| Browser screenshot / visual inspection | Not completed; see below |
| Real Anthropic request | Not executed; no API charges incurred by tests |

The suite covers bilingual aliases, strict schemas, range boundaries, qualitative
and qualified values, conflicting flags, missing reference units, real Chroma exact
retrieval/update/removal, evidence integrity, generated citation/row validation,
image content mismatch and re-encoding, oversized images, PDF page limits, encryption,
JavaScript and attachments, SQL parameterization, history corruption, unit conversion,
series separation, missing indicators, duplicate rows, uncertain dates and trend exclusions.
It also verifies that untrusted model text is rendered as plain text, not Markdown/HTML.

## Environment

Windows, Python 3.10.11. A project `.venv` was created with `--system-site-packages`
to reuse already installed libraries; pytest and pypdf were installed into it. This
was **not** a clean installation on a second operating system. The README's standard
isolated virtual-environment workflow still needs cross-platform verification.

| Direct dependency | Version used |
| --- | --- |
| streamlit | 1.57.0 |
| anthropic | 0.100.0 |
| chromadb | 1.5.9 |
| pydantic | 2.13.4 |
| Pillow | 12.0.0 |
| pypdf | 6.21.0 |
| python-dotenv | 1.2.2 |
| pandas | 2.3.3 |
| pytest | 9.1.1 |

`requirements.txt` bounds direct dependency versions; it is not a full transitive lockfile.
Some command exits emitted an ignored `pyreadline3` Windows console destructor error
from the inherited environment after the test summary. The test process returned zero;
this is recorded rather than represented as an application failure or silently hidden.

## Constraints encountered

- Initial package installation was blocked by sandbox networking. It succeeded through
  the approved network-enabled execution path.
- The sandboxed server attempt did not expose the port. Starting the local service through
  the approved execution path succeeded and the HTTP health check passed.
- Computer Use browser capture stopped because the tool could not reliably determine
  the current browser URL for its policy checks. Browser interaction was stopped; no
  runtime screenshots were captured and no visual layout review is claimed. AppTest
  interaction coverage and a healthy service are not substitutes for a screenshot review.
- No live model behavior, extraction accuracy, medical correctness, production deployment,
  clean-machine installation or concurrent multi-user suitability was validated.

No remote repository was created and no Git push or public deployment was performed.
