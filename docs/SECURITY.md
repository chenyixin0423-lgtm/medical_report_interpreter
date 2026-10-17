# Security and data handling

This is a local educational application, not a hardened multi-user medical service.
Default binding is `127.0.0.1`; CORS and XSRF protections remain enabled.

## Data flow

1. Streamlit receives uploaded bytes in memory. File size, extension and decoded content
   are checked. PNG/JPEG/WEBP images are decoded, oriented and re-encoded without metadata.
2. PDFs must have a valid header, parse strictly, contain 1–20 pages and be unencrypted.
   Interactive actions, forms, URLs and embedded files found in their object graph are
   rejected. Image input is limited to 20 megapixels and one frame.
3. With the user's consent, the **entire document** is sent to Anthropic for extraction.
   Image metadata stripping does not redact visible names. PDF bytes are not anonymized.
   Users must de-identify documents themselves. Do not use real patient data in a public demo.
4. Extracted facts, retrieved project notes and the optional question are sent in a second
   request after the review checkbox. The prompt excludes patient identifiers; it is not
   an automated guarantee of de-identification.
5. Structured results stay in the current Streamlit session by default. No raw upload or
   original filename is written by application code. Streamlit holds uploader bytes for
   the life of its widget/session; this app does not promise forensic memory erasure.
6. `MRI_ENABLE_LOCAL_HISTORY=true` allows explicit per-record saves to local SQLite.
   This is unencrypted, single-user storage. All sessions on that server could read the
   same history if enabled. Keep it disabled on shared/public hosts. Series labels are
   organization aids, not access controls. Do not put real names into labels or questions.

API credentials come from environment variables or ignored `.env` files, never UI fields.
Raw SDK errors, response bodies and extraction validation errors are not shown or logged
by application code. Error messages are deliberately generic. Third-party library logging,
external service retention and OS-level access remain outside this application's guarantees.

All untrusted explanatory text is displayed with plain-text components, not HTML. Generated
citations are validated against retrieved IDs. Prompt-injection defenses and schema checks
reduce risk but do not guarantee truthful or medically appropriate natural-language output.

## Files, persistence and deletion

- `.gitignore` excludes `.env`, secrets, local histories, old vector stores, uploads,
  common report image/PDF formats, caches, logs and the virtual environment.
- Only reviewed synthetic screenshots under `docs/screenshots/` may be tracked.
- Existing legacy `history/` and `chroma_db/` directories are not migrated or deleted.
  Legacy outputs lack provenance and the stricter schema; review them separately.
- Delete in History removes the selected structured record from session state and the
  active SQLite store. `secure_delete` is enabled for the SQL deletion, but filesystem
  backups, SSD behavior and external copies prevent a guarantee of secure erasure.
- Synthetic reports are never persisted into the live store.

PDF parsing is not a malware sandbox or antivirus. Limits and object-graph checks do not
eliminate parser vulnerabilities or every resource-exhaustion possibility. For untrusted
public uploads, add process isolation, stronger resource controls and authentication before
deployment. No public deployment or compliance certification is included here.
