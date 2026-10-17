"""Native Streamlit presentation. Untrusted narrative is rendered as plain text."""
import os

import pandas as pd
import streamlit as st

from interpreter.config import data_dir
from interpreter.demo import demo_reports
from interpreter.knowledge import KnowledgeBase
from interpreter.llm import ClaudeGateway, ModelError
from interpreter.pipeline import finish, prepare
from interpreter.security import UploadError, validate_upload
from interpreter.storage import HistoryStore
from interpreter.trends import trend_groups
from interpreter.abstention import STATES, summary_counts
from interpreter.models import Correction, Measurement
from interpreter.review import effective_report

DISCLAIMER = ("Educational AI demonstration — not a diagnostic or treatment service. "
              "Check all extracted values against the original report. A result inside a printed range "
              "does not establish health; an out-of-range result does not establish disease. "
              "No urgency triage or clinical validation is provided.")


@st.cache_resource(show_spinner="Preparing the local knowledge index…")
def knowledge():
    return KnowledgeBase(data_dir() / "chroma")


def table(record):
    return [{"Indicator": r.display_name, "ID": r.canonical_id or "Unmapped", "Value": r.original.raw_value or "Unreadable",
             "Unit": r.original.unit or "Not provided", "Report range": r.original.reference.text or "Not provided",
             "Range unit": r.original.reference.unit or "Not provided",
             "Range check": r.status.replace("_", " ") if r.decision and r.decision.state == "interpretable" else "Withheld — see review notes",
             "Readiness": r.decision.state if r.decision else "needs_review",
             "Why / next action": " ".join(x.message + " " + x.action for x in r.decision.reasons) if r.decision else "Revalidate this row.",
             "Knowledge": ("Source checked" if r.evidence.provenance == "source_checked_summary" else "Unverified legacy") if r.evidence else "Not covered",
             "Review notes": " ".join(r.issues)} for r in record.checked]


def metrics(record):
    counts = summary_counts(record.checked)
    cols = st.columns(4)
    cols[0].metric("Indicators", len(record.checked))
    cols[1].metric("Eligible outside range", counts["interpretable_outside_range"])
    cols[2].metric("Uncertain / conflicting", sum(r.status in ("unknown", "conflict") for r in record.checked))
    cols[3].metric("Knowledge coverage", f"{sum(r.evidence is not None for r in record.checked)} / {len(record.checked)}")
    for col, state in zip(st.columns(4), STATES):
        col.metric(state.replace("_", " ").title(), counts[state])
    st.caption("Readiness describes available information, not medical risk. Interpretable does not mean normal; unsupported does not mean dangerous.")


def detail(record):
    from interpreter.audit import audit_record
    audits = audit_record(record)  # Recompute, not a persisted/model-supplied verdict.
    st.caption(f"{'SYNTHETIC · PRESET' if record.mode == 'synthetic' else 'LIVE · MODEL-ASSISTED'} | Report date: {record.extracted.report_date or 'Unknown'}")
    st.text(f"Series: {record.series}")
    metrics(record)
    st.dataframe(table(record), hide_index=True, use_container_width=True)
    if record.extracted.warnings:
        st.warning("Extraction notices — verify the original report.")
        for text in record.extracted.warnings:
            st.text(text)
    if record.analysis_issue:
        st.warning(record.analysis_issue)
    explanations = {x.row_id: x for x in record.analysis.explanations} if record.analysis else {}
    st.subheader("Facts, evidence & explanations")
    st.caption("These layers are separate. Source checking is not clinical expert review or verification of a generated conclusion.")
    st.caption("Claim audit: " + " · ".join(f"{state}: {sum(a.outcome == state for a in audits)}"
        for state in ("Supported", "Unsupported", "Contradicted", "Needs Review")))
    st.caption("Supported means a bounded report-fact match or complete selected context, not medical correctness. These are not risk levels.")
    for index, row in enumerate(record.checked, 1):
        with st.expander(f"Indicator {index} · {row.canonical_id or 'Unmapped'} · {row.decision.state}"):
            st.text("Available to display: recorded value, unit and printed reference text; unresolved fields are not verified facts.")
            for reason in row.decision.reasons:
                st.text(f"{reason.message}\nNext action: {reason.action}")
            source = record.extracted.sources[index - 1]
            st.markdown("**Report source evidence**")
            st.text(f"Observation ID: {row.observation_id}")
            st.text(f"Origin: {source.origin} | Source check: {source.verification}")
            st.json(source.raw.model_dump())
            st.text(f"PDF page: {source.page or 'Unknown'} | Position: {source.location or 'Unknown'}")
            if source.excerpt:
                st.text("Locally matched PDF text (text-layer match, not proof of extraction accuracy):")
                st.text(source.excerpt)
            elif source.verification == "synthetic":
                st.text("Synthetic fixture: no real patient document, original excerpt or PDF location exists.")
            else:
                st.text("Original excerpt: Unknown. Source unverified; extracted fields are not independently verified original evidence.")
            st.caption("Human corrections remain separate and do not verify the original extraction or its location.")
            if record.extracted.indicators[index - 1] != row.original:
                st.text("Original extraction (retained):")
                st.json(record.extracted.indicators[index - 1].model_dump())
                st.text("Current reviewed/corrected fields:")
            st.text(f"Current label: {row.original.name}")
            st.text(f"Current value: {row.original.raw_value} {row.original.unit or ''}\nCurrent reference: {row.original.reference.text or 'Not supplied'}\nCurrent flag: {row.original.report_flag}")
            for issue in row.issues:
                st.text(f"Review: {issue}")
            st.markdown("**Knowledge context · source checking is not clinical review**")
            if row.evidence:
                st.caption(row.evidence.source_id + " · SHA256 " + row.evidence.sha256[:12])
                meta = row.evidence.metadata
                if meta:
                    st.text(f"Knowledge ID: {meta.entry_id}\nVersion: {meta.version}\nReview status: {meta.review_status}")
                    st.text(f"Applicability: {meta.applicability}\nAudit note: {meta.audit_note}")
                    st.text(f"Reviewer: {meta.reviewer or 'Unknown'} | Review date: {meta.reviewed_on or 'Unknown'}")
                    if meta.source_checked_on:
                        st.text(f"Source checked: {meta.source_checked_on}\nMethod: {meta.verification_method}\nClinical expert review: not performed")
                    for item in meta.sources:
                        st.text(f"Source: {item.name}\nURL: {item.url}\nScope: {item.scope}")
                st.text("External sources: Unknown / Unverified" if not meta or not meta.sources else "Recorded sources do not prove the generated explanation.")
                if record.mode == "synthetic":
                    st.text("Use: preset-linked context only; no model used this note. Not clinical evidence.")
                else:
                    st.text("Use: linked to this explanation" if row.row_id in explanations else "Use: retrieved only; not used for a validated explanation")
                if row.evidence.selected_text:
                    st.text("Selected context for this specimen, unit and range direction:")
                    st.text(row.evidence.selected_text)
                label = ("Show structured source-checked summary" if row.evidence.provenance == "source_checked_summary"
                         else "Show retained unverified note (may contain unsupported medical advice)")
                if st.checkbox(label, key=f"note-{record.id}-{row.row_id}"):
                    st.text(row.evidence.text)
            else:
                st.info("Knowledge base coverage is insufficient for this indicator.")
            st.markdown("**Preset explanation**" if record.mode == "synthetic" else "**Model-generated explanation · not medically verified**")
            row_audits = [a for a in audits if a.row_id == row.row_id]
            if not row_audits:
                st.text("No audited explanation is available.")
            for claim in row_audits:
                st.text(f"Claim {claim.claim_id} · {claim.outcome} · {claim.basis}")
                st.text(claim.reason)
                if claim.outcome == "Contradicted":
                    st.warning("Contradicted claim withheld. Inspect the linked checked facts; this text must not be used as a medical conclusion.")
                else:
                    if claim.outcome != "Supported":
                        st.warning("Unconfirmed generated claim — not an established medical conclusion. Manual review required.")
                    st.text(claim.text)
                st.text(f"Report observation: {claim.observation_id}")
                if claim.knowledge_id:
                    st.text(f"Audited knowledge: {claim.knowledge_id} · {claim.knowledge_version}")
                if claim.evidence_text:
                    st.text("Audit comparison evidence:")
                    st.text(claim.evidence_text)
    if record.analysis:
        with st.expander("Analysis limitations", expanded=True):
            st.text("Deterministic consistency checks only. Free-form medical entailment is not verified. Source checking and claim support are not clinical validation. Check original data and seek qualified interpretation.")


def dashboard(records):
    st.header("Overview")
    st.caption("Understand the report. Inspect the evidence. Keep uncertainty visible.")
    if not records:
        st.info("No reports yet. Open Upload & Analyze, or switch to Synthetic demo to explore the application.")
        return
    latest = records[0]
    metrics(latest)
    left, right = st.columns([2, 1])
    with left:
        with st.container(border=True):
            st.subheader("Latest report at a glance")
            st.caption(f"Report date: {latest.extracted.report_date or 'Unknown'} · {len(records)} reports available")
            st.dataframe(table(latest), hide_index=True, use_container_width=True,
                         column_order=["Indicator", "Value", "Unit", "Range check"])
    with right:
        with st.container(border=True):
            st.subheader("How to read this")
            st.write("Range checks use the reference interval printed in the report. They are not clinical judgments.")
            st.write("Missing values, ambiguous ranges and conflicting flags require manual review.")
            st.write("Open Detailed Results to inspect original facts, retrieved notes and explanations separately.")


def reset_pending():
    st.session_state.pop("pending", None)
    st.session_state.pop("review_facts", None)
    st.session_state.pop("corrections", None)
    st.session_state.pop("correction_row", None)


def correction_editor(facts):
    corrections = st.session_state.get("corrections", [])
    current = effective_report(facts, corrections)
    with st.expander("Correct extracted fields", expanded=False):
        index = st.selectbox("Indicator to correct", range(len(facts.indicators)),
                            format_func=lambda i: f"Row {i + 1}", key="correction_row")
        row_id = f"row-{index + 1}"
        raw = current.indicators[index]
        with st.form(f"correct-{row_id}"):
            name = st.text_input("Indicator name", value=raw.name)
            value = st.text_input("Value as printed", value=raw.raw_value or "")
            unit = st.text_input("Measurement unit", value=raw.unit or "")
            specimen_options = ["unknown", "blood", "whole_blood", "serum", "plasma", "urine", "other"]
            specimen = st.selectbox("Specimen as reported", specimen_options, index=specimen_options.index(raw.specimen))
            fasting_options = ["unknown", "fasting", "nonfasting"]
            fasting = st.selectbox("Fasting as reported", fasting_options, index=fasting_options.index(raw.fasting))
            bounds = st.text_input("Printed reference interval", value=raw.reference.text or "")
            refunit = st.text_input("Reference unit", value=raw.reference.unit or "")
            flag = st.selectbox("Printed flag", ["unknown", "normal", "high", "low"],
                                index=["unknown", "normal", "high", "low"].index(raw.report_flag))
            uncertain = st.checkbox("Text is still unclear", value=raw.uncertain)
            required = st.checkbox("Interval requires demographic / method / laboratory selection", value=raw.reference.context_required)
            context = st.checkbox("I confirmed the applicable printed interval", value=raw.reference.context_confirmed)
            reason = st.text_input("Reason for correction (no identifying information)")
            confirmed = st.checkbox("I checked these changed fields against the original report")
            applied = st.form_submit_button("Apply correction and revalidate")
        if applied:
            try:
                after = Measurement(name=name.strip(), raw_value=value.strip() or None, unit=unit.strip() or None,
                    reference={"text": bounds.strip() or None, "unit": refunit.strip() or None,
                               "context_required": required, "context_confirmed": context},
                    report_flag=flag, uncertain=uncertain, specimen=specimen, fasting=fasting)
                change = Correction(row_id=row_id, before=facts.indicators[index], after=after,
                                    reason=reason.strip(), confirmed_from_report=confirmed)
                st.session_state.corrections = [c for c in corrections if c.row_id != row_id] + [change]
                st.session_state.pop("review_facts", None)
                st.rerun()
            except ValueError:
                st.error("Provide an indicator name and correction reason, and valid field values. Nothing was changed.")
    return st.session_state.get("corrections", [])


def upload_page(demo, kb):
    st.header("Upload & Analyze")
    if demo:
        st.info("Synthetic demo uses fabricated data and preset explanations. No file, API key or network model call is needed.")
        st.write("Explore the six sample indicators in Detailed Results and the three-report series in Trends.")
        st.markdown("**Live workflow**")
        st.write("Validate file → Extract facts → Review facts → Normalize names → Retrieve notes → Generate and validate explanations")
        return
    st.caption("PDF, JPEG, PNG or WEBP · up to 10 MB · PDFs up to 20 pages")
    st.warning("Live extraction sends the entire uploaded document to Anthropic. Remove personal identifiers before uploading. Metadata stripping does not remove visible identifiers.")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.info("Set ANTHROPIC_API_KEY in your environment or .env file to enable live extraction.")
        return
    uploaded = st.file_uploader("De-identified report", type=["pdf", "jpg", "jpeg", "png", "webp"],
                                key="report_upload", on_change=reset_pending)
    consent = st.checkbox("I have removed identifying information and agree to send this document to Anthropic.")
    if st.button("Extract report facts", type="primary", disabled=not (uploaded and consent)):
        reset_pending()
        try:
            with st.status("Extracting structured facts…", expanded=True) as status:
                st.write("Checking file content and size")
                safe = validate_upload(uploaded.getvalue(), uploaded.name)
                st.write("Reading report with Claude")
                extracted = ClaudeGateway().extract(safe)
                st.session_state.pending = extracted
                status.update(label="Extraction complete — review required", state="complete")
        except (UploadError, ModelError) as exc:
            st.error(str(exc))
    if "pending" not in st.session_state:
        return
    facts = st.session_state.pending
    st.subheader("Review extracted facts")
    st.caption("Correct individual fields below or upload a clearer report. Changes are rechecked and never automatically resolve all missing information.")
    st.text(f"Extracted report date: {facts.report_date or 'Unknown — excluded from dated trends'}")
    st.dataframe([{"Original label": x.name, "Value": x.raw_value, "Unit": x.unit,
        "Specimen": x.specimen, "Fasting": x.fasting,
        "Reference range": x.reference.text, "Reference unit": x.reference.unit,
        "Printed flag": x.report_flag, "Uncertain": x.uncertain} for x in facts.indicators], hide_index=True)
    for text in facts.warnings:
        st.text(text)
    corrections = correction_editor(facts)
    preview = prepare(facts, kb, corrections)
    st.dataframe([{"Row": r.row_id, "Current value": r.original.raw_value, "Readiness": r.decision.state,
        "Reasons": " ".join(x.message for x in r.decision.reasons),
        "Next actions": " ".join(x.action for x in r.decision.reasons)} for r in preview], hide_index=True)
    series = st.text_input("Series label (a pseudonym, never a patient name)", value="My reports", max_chars=60)
    st.caption("This workflow explains eligible rows only. Free-form diagnostic or treatment questions are unsupported and are not sent to the model.")
    reviewed = st.checkbox("I checked these values, units, ranges and date against the original, and this series contains reports from the same person.", key="review_facts")
    if st.button("Analyze reviewed facts", disabled=not (reviewed and series.strip()), type="primary"):
        try:
            with st.status("Building evidence-based context…", expanded=True) as status:
                st.write("Normalizing indicator names and checking printed ranges")
                rows = prepare(facts, kb, corrections)
                st.write(f"Retrieved project notes for {sum(r.evidence is not None for r in rows)} of {len(rows)} rows")
                st.write("Generating explanations and validating source references")
                record = finish(facts, rows, ClaudeGateway(), series.strip(), corrections=corrections)
                st.session_state.setdefault("live_records", []).insert(0, record)
                st.session_state.pop("pending", None)
                status.update(label="Analysis complete" if record.analysis else "Facts ready; explanations unavailable",
                              state="complete" if record.analysis else "error")
            st.success("Report added to this session. Open Detailed Results or History to inspect it.")
            detail(record)
        except ModelError as exc:
            st.error(str(exc))
        except Exception:
            st.error("Report processing failed. No result was added. Check local storage access and retry.")


def history_page(records, demo, store):
    st.header("History")
    if not records:
        st.info("No saved reports in this mode.")
        if demo and st.button("Restore synthetic examples"):
            st.session_state.demo_records = demo_reports(knowledge())
            st.rerun()
        return
    if demo:
        st.caption("These three synthetic reports are built in. Hide one for this session or restore the demo.")
    elif store:
        st.warning("Local history is enabled for a trusted single-user machine. Structured facts and matched report excerpts are unencrypted and may be sensitive. Raw uploads and filenames are not saved.")
    else:
        st.caption("Session-only storage. Data is lost when this session ends. Local persistence is disabled by default.")
    for record in records:
        with st.container(border=True):
            a, b, c = st.columns([4, 1, 1])
            a.text(f"{record.extracted.report_date or 'Unknown date'} · {record.series} · {record.id[:8]}")
            if store and not demo and b.button("Save locally", key=f"save-{record.id}"):
                try:
                    store.save(record)
                    st.toast("Structured report saved locally")
                except Exception:
                    st.error("Could not save local history. Check directory access and disk space.")
            if c.button("Hide" if demo else "Delete", key=f"delete-{record.id}"):
                if store and not demo:
                    try:
                        store.delete(record.id)
                    except Exception:
                        st.error("Could not delete the local record.")
                        return
                key = "demo_records" if demo else "live_records"
                st.session_state[key] = [r for r in records if r.id != record.id]
                st.rerun()
    if demo and st.button("Restore synthetic examples"):
        st.session_state.demo_records = demo_reports(knowledge())
        st.rerun()


def trends_page(records):
    st.header("Trends")
    st.caption("Numerical change is not evidence of improvement or deterioration. Compare the same person, specimen and test conditions.")
    if not records:
        st.info("Add reports to explore numeric observations over time.")
        return
    series = st.selectbox("Report series", sorted({r.series for r in records}))
    codes = sorted({x.canonical_id for r in records if r.series == series for x in r.checked if x.canonical_id})
    if not codes:
        st.info("No recognized indicators available for trends.")
        return
    code = st.selectbox("Indicator", codes, index=codes.index("HGB") if "HGB" in codes else 0)
    groups, excluded = trend_groups(records, code, series, records[0].mode)
    if not groups:
        st.info("No comparable numeric observations. See exclusions below.")
    for unit, points in groups.items():
        st.subheader(f"{code} · {unit}")
        frame = pd.DataFrame(points)
        st.dataframe(frame, hide_index=True, use_container_width=True)
        if len({p["Date"] for p in points}) >= 2:
            if frame["Date"].duplicated().any():
                st.info("Multiple reports share a date. Showing points without an inferred within-day order.")
                st.scatter_chart(frame, x="Date", y="Value", color="#2E86AB")
            else:
                st.line_chart(frame, x="Date", y="Value", color="#2E86AB")
                delta = points[-1]["Value"] - points[0]["Value"]
                st.caption(f"First to last numeric change: {delta:+.3g} {unit}. No clinical direction is inferred.")
        else:
            st.info("At least two distinct report dates are needed for a trend line.")
    if len(groups) > 1:
        st.info("Incompatible units are shown in separate groups; no conversion is assumed.")
    if excluded:
        with st.expander(f"Excluded observations ({len(excluded)})", expanded=True):
            st.dataframe(excluded, hide_index=True)


def main():
    st.set_page_config(page_title="Medical Report Interpreter", page_icon="🔬", layout="wide")
    with st.sidebar:
        st.title("MRI")
        st.caption("MEDICAL REPORT INTERPRETER")
        mode = st.radio("Workspace", ["Synthetic demo", "Live analysis"])
        page = st.radio("Navigate", ["Dashboard", "Upload & Analyze", "Detailed Results", "History", "Trends"])
        st.divider()
        st.caption("Source-checked summaries + unverified legacy notes · Bilingual indicator matching")
        st.caption("No diagnostic or clinical validation claims")
    st.title("Medical Report Interpreter")
    st.caption("A transparent workspace for laboratory reports")
    demo = mode == "Synthetic demo"
    if demo:
        st.info("SYNTHETIC DEMO · Fabricated data and preset example explanations. No live model analysis.")
    st.warning(DISCLAIMER)
    try:
        kb = knowledge()
    except Exception:
        st.error("Could not initialize the local knowledge index. Check MRI_DATA_DIR permissions and installed dependencies.")
        return
    store = None
    if not demo and os.environ.get("MRI_ENABLE_LOCAL_HISTORY", "false").lower() == "true":
        try:
            store = HistoryStore(data_dir() / "history.sqlite3")
        except Exception:
            st.error("Local history is unavailable. Session-only storage remains active.")
    if demo:
        if "demo_records" not in st.session_state:
            st.session_state.demo_records = demo_reports(kb)
        records = st.session_state.demo_records
    else:
        if "live_records" not in st.session_state:
            saved, rejected = ([], 0)
            if store:
                try:
                    saved, rejected = store.load()
                except Exception:
                    st.error("Local history could not be read. Existing data has not been changed.")
            st.session_state.live_records = saved
            st.session_state.rejected_history = rejected
        if st.session_state.get("rejected_history", 0):
            st.warning("Some local records failed validation and were skipped. Existing files were not changed.")
        records = st.session_state.live_records
    if page == "Dashboard":
        dashboard(records)
    elif page == "Upload & Analyze":
        upload_page(demo, kb)
    elif page == "Detailed Results":
        st.header("Detailed Results")
        if records:
            selected = st.selectbox("Report", range(len(records)), format_func=lambda i: f"{records[i].extracted.report_date or 'Unknown date'} · Report {i + 1}")
            detail(records[selected])
        else:
            st.info("Analyze a report to see its facts, evidence and explanations.")
    elif page == "History":
        history_page(records, demo, store)
    else:
        trends_page(records)
