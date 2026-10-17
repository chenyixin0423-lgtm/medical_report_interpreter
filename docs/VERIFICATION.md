# Verification record

Date: **2026-10-17** (Asia/Shanghai).

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
