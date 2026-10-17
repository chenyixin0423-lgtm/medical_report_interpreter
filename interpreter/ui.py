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
             "Range check": r.status.replace("_", " "), "Knowledge": "Project note" if r.evidence else "Not covered",
             "Review notes": " ".join(r.issues)} for r in record.checked]


def metrics(record):
    cols = st.columns(4)
    cols[0].metric("Indicators", len(record.checked))
    cols[1].metric("Outside printed range", sum(r.status in ("high", "low") for r in record.checked))
    cols[2].metric("Uncertain / conflicting", sum(r.status in ("unknown", "conflict") for r in record.checked))
    cols[3].metric("Knowledge coverage", f"{sum(r.evidence is not None for r in record.checked)} / {len(record.checked)}")


def detail(record):
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
    st.caption("These layers are intentionally separate. Project notes are not verified medical sources.")
    for index, row in enumerate(record.checked, 1):
        with st.expander(f"Indicator {index} · {row.canonical_id or 'Unmapped'} · {row.status.replace('_', ' ')}"):
            st.text(f"Original label: {row.original.name}")
            st.text(f"Original value: {row.original.raw_value} {row.original.unit or ''}\nPrinted range: {row.original.reference.text or 'Not supplied'}\nPrinted flag: {row.original.report_flag}")
            for issue in row.issues:
                st.text(f"Review: {issue}")
            st.markdown("**Knowledge base evidence · unverified project note**")
            if row.evidence:
                st.caption(row.evidence.source_id + " · SHA256 " + row.evidence.sha256[:12])
                st.text(row.evidence.text)
            else:
                st.info("Knowledge base coverage is insufficient for this indicator.")
            st.markdown("**Preset explanation**" if record.mode == "synthetic" else "**Model-generated explanation · not medically verified**")
            st.text(explanations[row.row_id].text if row.row_id in explanations else "No validated explanation is available.")
    if record.analysis:
        with st.expander("Analysis limitations", expanded=True):
            for text in record.analysis.limitations:
                st.text(text)


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
        st.session_state.pop("pending", None)
        st.session_state.pop("review_facts", None)
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
    st.caption("If any value is wrong, re-upload a clearer report. Unreadable data will not be guessed.")
    st.text(f"Extracted report date: {facts.report_date or 'Unknown — excluded from dated trends'}")
    st.dataframe([{"Original label": x.name, "Value": x.raw_value, "Unit": x.unit,
        "Reference range": x.reference.text, "Reference unit": x.reference.unit,
        "Printed flag": x.report_flag, "Uncertain": x.uncertain} for x in facts.indicators], hide_index=True)
    for text in facts.warnings:
        st.text(text)
    series = st.text_input("Series label (a pseudonym, never a patient name)", value="My reports", max_chars=60)
    question = st.text_area("Optional question (no personal information)", max_chars=2000)
    reviewed = st.checkbox("I checked these values, units, ranges and date against the original, and this series contains reports from the same person.", key="review_facts")
    if st.button("Analyze reviewed facts", disabled=not (reviewed and series.strip()), type="primary"):
        try:
            with st.status("Building evidence-based context…", expanded=True) as status:
                st.write("Normalizing indicator names and checking printed ranges")
                rows = prepare(facts, kb)
                st.write(f"Retrieved project notes for {sum(r.evidence is not None for r in rows)} of {len(rows)} rows")
                st.write("Generating explanations and validating source references")
                record = finish(facts, rows, ClaudeGateway(), series.strip(), question)
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
        st.warning("Local history is enabled for a trusted single-user machine. Saved structured data is unencrypted and may contain sensitive model output. Raw uploads and filenames are not saved.")
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
        st.caption("26 local knowledge notes · English interface · Bilingual indicator matching")
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
