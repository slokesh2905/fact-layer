import streamlit as st
import requests
import time
from html import escape
from typing import Optional

API_BASE = "http://localhost:8000/api"

st.set_page_config(
    page_title="Fact Knowledge Layer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Relationship type badges */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.78em;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .badge-corroborates { background: #d4edda; color: #155724; }
    .badge-contradicts  { background: #f8d7da; color: #721c24; }
    .badge-reconciles   { background: #cce5ff; color: #004085; }
    .badge-unrelated    { background: #e2e3e5; color: #383d41; }

    /* Evidence block */
    .evidence-box {
        background: #f8f9fa;
        color: #212529;
        border-left: 3px solid #6c757d;
        padding: 8px 12px;
        border-radius: 0 4px 4px 0;
        font-family: monospace;
        font-size: 0.85em;
        white-space: pre-wrap;
        word-break: break-word;
        max-height: 180px;
        overflow-y: auto;
    }
    .evidence-box-a { border-left-color: #0d6efd; }
    .evidence-box-b { border-left-color: #198754; }

    /* Case card */
    .case-card {
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .case-corroborates { border-top: 4px solid #198754; }
    .case-contradicts  { border-top: 4px solid #dc3545; }
    .case-reconciles   { border-top: 4px solid #0d6efd; }
    .case-failure      { border-top: 4px solid #fd7e14; }

    /* Confidence pill */
    .conf-high { color: #198754; font-weight: 600; }
    .conf-med  { color: #fd7e14; font-weight: 600; }
    .conf-low  { color: #dc3545; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ── API helpers ──────────────────────────────────────────────────────────────

def _get(endpoint: str, params: dict = None):
    with st.spinner("Fetching data..."):
        try:
            r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to API. Make sure the backend is running on port 8000.")
            return None
        except Exception as e:
            st.error(f"API error: {e}")
            return None


def _post(endpoint: str, json=None, files=None, data=None):
    with st.spinner("Processing..."):
        try:
            if files:
                r = requests.post(f"{API_BASE}{endpoint}", files=files, data=data, timeout=120)
            else:
                r = requests.post(f"{API_BASE}{endpoint}", json=json, timeout=300)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to API. Make sure the backend is running on port 8000.")
            return None
        except Exception as e:
            st.error(f"API error: {e}")
            return None


def _delete(endpoint: str):
    with st.spinner("Deleting..."):
        try:
            r = requests.delete(f"{API_BASE}{endpoint}", timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to API. Make sure the backend is running on port 8000.")
            return None
        except Exception as e:
            st.error(f"API error: {e}")
            return None


def conf_html(c: float) -> str:
    cls = "conf-high" if c >= 0.8 else "conf-med" if c >= 0.6 else "conf-low"
    return f'<span class="{cls}">{c:.0%}</span>'


def badge_html(rel_type: str) -> str:
    return f'<span class="badge badge-{rel_type}">{rel_type}</span>'


def latest_documents(docs: list[dict]) -> list[dict]:
    status_rank = {
        "completed": 5,
        "analyzing": 4,
        "extracting": 3,
        "parsing": 2,
        "pending": 1,
        "failed": 0,
    }
    latest_by_name = {}
    for doc in docs:
        key = (doc.get("filename"), doc.get("source_dataset") or "")
        current = latest_by_name.get(key)
        doc_score = (status_rank.get(str(doc.get("status", "")).lower(), 0), doc.get("uploaded_at", ""))
        current_score = (
            status_rank.get(str(current.get("status", "")).lower(), 0),
            current.get("uploaded_at", ""),
        ) if current else None
        if not current or doc_score > current_score:
            latest_by_name[key] = doc
    return sorted(latest_by_name.values(), key=lambda d: d.get("uploaded_at", ""), reverse=True)


# ── Sidebar navigation ────────────────────────────────────────────────────────

PAGES = ["📤 Upload", "🧩 Fact Explorer", "🔗 Relationships", "🔍 Search", "🎯 Demo Cases"]
page = st.sidebar.radio("Navigation", PAGES, index=0)

stats = _get("/stats") or {}
st.sidebar.divider()
st.sidebar.metric("Documents", stats.get("total_documents", "–"))
st.sidebar.metric("Facts", stats.get("total_facts", "–"))
st.sidebar.metric("Relationships", stats.get("total_relationships", "–"))


# ─────────────────────────────────────────────────────────────────────────────
# 🎯 DEMO CASES  (shown last — the submission showcase tab)
# ─────────────────────────────────────────────────────────────────────────────

def render_cases():
    st.title("🎯 Demo Cases")
    st.caption("Four required cases demonstrating corroboration, contradiction, reconciliation, and extraction failure — each grounded in source evidence.")


    cases = _get("/cases")

    if not cases:
        st.info("No relationships found yet. Upload and process PDFs first, then relationships are detected automatically.")
        return

    # ── Case 1: Corroboration ─────────────────────────────────────────────
    st.subheader("Case 1 — Corroboration")
    st.caption("The same fact confirmed across documents, even if expressed differently.")
    c = cases.get("corroboration")
    if c:
        _render_case_card(c, "corroborates")
    else:
        st.info("No corroboration found. Process more documents.")

    st.divider()

    # ── Case 2: Contradiction ─────────────────────────────────────────────
    st.subheader("Case 2 — Contradiction")
    st.caption("A genuine conflict: two documents report materially different values for the same fact.")
    c = cases.get("contradiction")
    if c:
        _render_case_card(c, "contradicts")
    else:
        st.info("No contradiction found yet.")

    st.divider()

    # ── Case 3: Reconciliation ────────────────────────────────────────────
    st.subheader("Case 3 — Apparent Contradiction, Explained by Context")
    st.caption("Values differ, but the difference is explained by scope, time period, or unit.")
    c = cases.get("reconciliation")
    if c:
        _render_case_card(c, "reconciles")
    else:
        st.info("No reconciliation found yet.")

    st.divider()

    # ── Case 4: Extraction Failure ────────────────────────────────────────
    st.subheader("Case 4 — Extraction / Reasoning Failure")
    st.caption("A known failure mode and how it was handled.")

    st.markdown("""
    <div class="case-card case-failure">
    <strong>Failure: Over-generic attribute labels</strong><br><br>
    The LLM sometimes extracted a fact with attribute <code>Profit</code> without distinguishing
    <em>Profit Before Tax</em> from <em>Profit After Tax</em>. This caused false contradictions
    when compared across documents that correctly labelled the two separately.<br><br>
    <strong>How it was handled:</strong> The extraction prompt was updated to require granular
    attribute names (e.g., prefer "Profit Before Tax" over "Profit") and to use the
    <code>qualifier</code> field to capture the surrounding table header context.<br><br>
    <strong>Future improvement:</strong> A post-extraction validation pass that flags any
    fact whose attribute appears in a known ambiguity list and asks the LLM to re-classify it
    with more context.
    </div>
    """, unsafe_allow_html=True)


def _render_case_card(case: dict, rel_type: str):
    rel_id = case.get("relationship_id", "")
    entity = case.get("entity", "")
    attribute = case.get("attribute", "")
    period = case.get("time_period", "")
    explanation = case.get("explanation", "")
    confidence = case.get("confidence", 0.0)
    fa = case.get("fact_a", {})
    fb = case.get("fact_b", {})

    header = f"{entity} · {attribute}"
    if period:
        header += f" · {period}"

    st.markdown(
        f"{badge_html(rel_type)} &nbsp; <strong>{header}</strong> &nbsp; confidence: {conf_html(confidence)}",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        doc_label = fa.get("document", "Document A")
        st.caption(f"**{doc_label}** — page {fa.get('page_num', '?')}")
        st.markdown(f"**{fa.get('value', '')} {fa.get('unit', '')}** {_scope_tag(fa.get('scope'))}")
        st.markdown(
            f'<div class="evidence-box evidence-box-a">{escape(str(fa.get("evidence", "")))}</div>',
            unsafe_allow_html=True,
        )
    with col_b:
        doc_label = fb.get("document", "Document B")
        st.caption(f"**{doc_label}** — page {fb.get('page_num', '?')}")
        st.markdown(f"**{fb.get('value', '')} {fb.get('unit', '')}** {_scope_tag(fb.get('scope'))}")
        st.markdown(
            f'<div class="evidence-box evidence-box-b">{escape(str(fb.get("evidence", "")))}</div>',
            unsafe_allow_html=True,
        )

    if explanation:
        st.markdown(f"> {explanation}")

    if rel_id:
        with st.expander("Full evidence details"):
            detail = _get(f"/relationships/{rel_id}/evidence")
            if detail:
                st.json(detail)


def _scope_tag(scope: Optional[str]) -> str:
    if not scope:
        return ""
    return f"({scope})"


# ─────────────────────────────────────────────────────────────────────────────
# 📤 UPLOAD  (tab 1 — entry point for new PDFs)
# ─────────────────────────────────────────────────────────────────────────────

def render_upload():
    st.title("📤 Upload PDFs")
    st.caption("Upload any PDF — facts are extracted automatically and cross-document relationships are detected.")


    dataset = st.text_input(
        "Dataset / collection name (optional)",
        placeholder="e.g. delhivery, india-macroeconomy, my-project",
        help="Groups documents together. Leave blank if not needed.",
    )

    uploaded = st.file_uploader("Drop PDF files here", type="pdf", accept_multiple_files=True)

    if uploaded and st.button("Upload & Process", type="primary"):
        for f in uploaded:
            with st.status(f"Processing **{f.name}**...", expanded=True) as status:
                files = {"file": (f.name, f.getvalue(), "application/pdf")}
                data = {"source_dataset": dataset} if dataset else {}
                result = _post("/documents/upload", files=files, data=data)

                if not result:
                    status.update(label=f"Failed to upload {f.name}", state="error")
                    continue

                doc_id = result["document_id"]
                st.write("Uploaded. Extracting facts and detecting relationships...")

                for _ in range(120):
                    time.sleep(3)
                    s = _get(f"/documents/{doc_id}/status")
                    if not s:
                        break
                    job = _get(f"/documents/{doc_id}/jobs")
                    if job:
                        latest = job[-1]
                        prog = latest.get("progress", 0)
                        msg = latest.get("message", "")
                        st.write(f"[{prog:.0%}] {msg}")
                    if s.get("status") == "completed":
                        status.update(label=f"{f.name} — done", state="complete")
                        break
                    if s.get("status") == "failed":
                        status.update(label=f"{f.name} — failed: {s.get('error_message')}", state="error")
                        break
                else:
                    status.update(label=f"{f.name} — still processing (check Documents tab)", state="running")

    st.divider()
    st.subheader("All Documents")

    docs = _get("/documents", {"limit": 100}) or []
    if not docs:
        st.info("No documents yet.")
        return

    show_history = st.checkbox("Show historical failed/pending runs", value=False)
    visible_docs = docs if show_history else latest_documents(docs)

    if not show_history and len(visible_docs) < len(docs):
        hidden = len(docs) - len(visible_docs)
        st.caption(f"Hiding {hidden} older run(s). Enable history to debug previous failures.")

    for doc in visible_docs:
        status_icon = {"completed": "✅", "failed": "❌", "pending": "⏳", "extracting": "⚙️", "analyzing": "🔍", "parsing": "📖"}.get(doc["status"], "•")
        with st.expander(f"{status_icon} {doc['filename']}  —  {doc['status']}"):
            cols = st.columns(4)
            cols[0].metric("Pages", doc.get("page_count") or "–")
            cols[1].write(f"**Dataset:** {doc.get('source_dataset') or '–'}")
            cols[2].write(f"**Uploaded:** {doc['uploaded_at'][:10]}")
            cols[3].write(f"**Processed:** {(doc.get('processed_at') or '')[:10] or '–'}")
            if doc.get("error_message"):
                st.error(doc["error_message"])

            st.divider()
            confirm_key = f"confirm_delete_{doc['document_id']}"
            delete_key = f"delete_{doc['document_id']}"
            confirm = st.checkbox("Confirm delete this document and its extracted data", key=confirm_key)
            if st.button("Delete document", key=delete_key, type="secondary", disabled=not confirm):
                result = _delete(f"/documents/{doc['document_id']}")
                if result:
                    st.success(f"Deleted {doc['filename']}")
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 🧩 FACT EXPLORER  (tab 2 — browse extracted facts per document)
# ─────────────────────────────────────────────────────────────────────────────

def render_documents():
    st.title("🧩 Fact Explorer")
    st.caption("Pick a processed document to browse its extracted facts with character-level source evidence.")


    docs = _get("/documents", {"status": "completed", "limit": 100}) or []
    if not docs:
        st.info("No processed documents yet.")
        return

    options = {f"{d['filename']}  ({d.get('source_dataset') or 'no dataset'})": d["document_id"] for d in docs}
    selected = st.selectbox("Document", list(options.keys()))
    doc_id = options[selected]

    col1, col2, col3 = st.columns(3)
    fact_type = col1.selectbox("Type", ["All", "numeric", "percentage", "categorical", "temporal", "ratio"])
    min_conf = col2.slider("Min confidence", 0.0, 1.0, 0.5, 0.05)
    show_rels = col3.checkbox("Show relationship badges", value=True)

    facts = _get(
        f"/documents/{doc_id}/facts",
        {
            "fact_type": None if fact_type == "All" else fact_type,
            "min_confidence": min_conf,
            "with_relationships": show_rels,
            "limit": 200,
        },
    ) or []

    st.write(f"**{len(facts)} facts**")

    if not facts:
        st.info("No facts match the current filters.")
        return

    for fact in facts:
        rels = (fact.get("context") or {}).get("relationships", [])
        rel_badges = " ".join(badge_html(r["relationship_type"]) for r in rels) if rels else ""

        conf_cls = "conf-high" if fact["confidence"] >= 0.8 else "conf-med" if fact["confidence"] >= 0.6 else "conf-low"

        header_html = (
            f"<strong>{fact['entity']}</strong> › <strong>{fact['attribute']}</strong>"
            f" &nbsp;=&nbsp; {fact['value']} {fact.get('unit') or ''}"
            f"&nbsp;&nbsp;{rel_badges}"
        )
        st.markdown(header_html, unsafe_allow_html=True)

        meta_cols = st.columns([2, 2, 2, 1])
        meta_cols[0].write(f"Period: {fact.get('time_period') or '–'}")
        meta_cols[1].write(f"Scope: {fact.get('scope') or '–'}")
        meta_cols[2].write(f"Page: {fact['page_num']}")
        meta_cols[3].markdown(f'<span class="{conf_cls}">{fact["confidence"]:.0%}</span>', unsafe_allow_html=True)

        with st.expander("Source evidence"):
            evid = (fact.get("evidence") or {}).get("text", "")
            st.markdown(f'<div class="evidence-box">{escape(str(evid))}</div>', unsafe_allow_html=True)
            extra = (fact.get("context") or {}).get("extra_properties", {})
            if extra:
                st.write("**Additional properties:**", extra)

        st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# 🔗 RELATIONSHIPS  (tab 3 — cross-document corroborations / contradictions / reconciliations)
# ─────────────────────────────────────────────────────────────────────────────

def render_relationships():
    st.title("🔗 Cross-Document Relationships")
    st.caption("All detected relationships between facts across documents — click a row to see full evidence side by side.")


    col1, col2 = st.columns([2, 1])
    with col1:
        rel_filter = st.radio(
            "Filter by type",
            ["All", "corroborates", "contradicts", "reconciles"],
            horizontal=True,
        )
    with col2:
        if st.button("Re-run full analysis", help="Reanalyse all documents from scratch"):
            with st.spinner("Running..."):
                result = _post("/analyze/relationships")
                if result:
                    st.success(result.get("message", "Done"))
                    st.rerun()

    params = {"limit": 200}
    if rel_filter != "All":
        params["relationship_type"] = rel_filter

    rels = _get("/relationships", params) or []

    if not rels:
        st.info("No relationships found. Upload and process at least two documents.")
        return

    counts = {}
    for r in _get("/relationships", {"limit": 1000}) or []:
        t = r["relationship_type"]
        counts[t] = counts.get(t, 0) + 1

    metric_cols = st.columns(4)
    metric_cols[0].metric("Total", sum(counts.values()))
    metric_cols[1].metric("Corroborates", counts.get("corroborates", 0))
    metric_cols[2].metric("Contradicts", counts.get("contradicts", 0))
    metric_cols[3].metric("Reconciles", counts.get("reconciles", 0))

    st.divider()
    st.write(f"Showing **{len(rels)}** relationships")

    for rel in rels:
        rel_id = rel["id"]
        rel_type = rel["relationship_type"]
        explanation = rel.get("explanation", "")
        confidence = rel.get("confidence", 0.0)

        # Header row
        header = f"{badge_html(rel_type)} &nbsp; conf: {conf_html(confidence)}"
        if explanation:
            snippet = escape(explanation[:120] + ("..." if len(explanation) > 120 else ""))
            header += f" &nbsp;·&nbsp; <span style='color:#6c757d;font-size:0.9em;'>{snippet}</span>"

        with st.expander(f"[{rel_type.upper()}] {explanation[:80]}"):
            detail = _get(f"/relationships/{rel_id}/evidence")
            if not detail:
                st.warning("Could not load evidence.")
                continue

            fa = detail["fact_a"]
            fb = detail["fact_b"]

            st.markdown(
                f"{badge_html(rel_type)} &nbsp; confidence: {conf_html(confidence)}",
                unsafe_allow_html=True,
            )
            st.write(f"> {detail['explanation']}")

            c1, c2 = st.columns(2)
            with c1:
                st.caption(f"**{fa['document']}** — page {fa['page_num']}")
                st.markdown(f"**{fa['entity']} · {fa['attribute']}**")
                st.markdown(f"Value: `{fa['value']} {fa.get('unit') or ''}`  scope: {fa.get('scope') or '–'}")
                st.markdown(
                    f'<div class="evidence-box evidence-box-a">{escape(str(fa["evidence"]))}</div>',
                    unsafe_allow_html=True,
                )
            with c2:
                st.caption(f"**{fb['document']}** — page {fb['page_num']}")
                st.markdown(f"**{fb['entity']} · {fb['attribute']}**")
                st.markdown(f"Value: `{fb['value']} {fb.get('unit') or ''}`  scope: {fb.get('scope') or '–'}")
                st.markdown(
                    f'<div class="evidence-box evidence-box-b">{escape(str(fb["evidence"]))}</div>',
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────────────────────────────────────
# 🔍 SEMANTIC SEARCH  (tab 4 — search facts by meaning)
# ─────────────────────────────────────────────────────────────────────────────

def render_search():
    st.title("🔍 Semantic Search")
    st.caption(
        "Search facts by meaning, not just keywords. "
        "Try queries like *'India economic growth'* to find facts about GDP, "
        "or *'logistics company profitability'* to find revenue / EBITDA facts."
    )

    # ── Controls ──────────────────────────────────────────────────────────────
    with st.form("search_form"):
        col_q, col_mode = st.columns([4, 1])
        query = col_q.text_input(
            "Search query",
            placeholder="e.g. India GDP growth rate, Delhivery revenue FY24 ...",
            label_visibility="collapsed",
        )
        mode = col_mode.radio("Mode", ["Semantic", "Keyword"], horizontal=False)

        with st.expander("Optional filters", expanded=False):
            f1, f2, f3 = st.columns(3)
            filt_entity = f1.text_input("Entity", placeholder="e.g. india")
            filt_attr   = f2.text_input("Attribute", placeholder="e.g. gdp_growth")
            top_k       = f3.slider("Max results", 3, 50, 10)
            
        submitted = st.form_submit_button("Search", type="primary", use_container_width=True)

    # We want to run the search if they submitted the form and there's a query
    if not submitted:
        # Don't show the "Enter a query" message if they haven't submitted anything yet,
        # but if there IS a query (e.g. leftover from state), we could still search,
        # but standard form behaviour is to wait for submit.
        st.info("Enter a query above and click Search.")
        return
        
    if submitted and not query.strip():
        st.warning("Please enter a search query.")
        return

    # ── Call API ──────────────────────────────────────────────────────────────
    endpoint = "/search/semantic" if mode == "Semantic" else "/search"
    payload = {"query": query, "top_k": top_k}
    if filt_entity:
        payload["entity"] = filt_entity
    if filt_attr:
        payload["attribute"] = filt_attr

    results = _post(endpoint, json=payload) or []

    if not results:
        st.warning(
            "No results found. "
            + ("Make sure facts are indexed (upload and process PDFs first)." if mode == "Semantic"
               else "Try different keywords.")
        )
        return

    # ── Render results ────────────────────────────────────────────────────────
    mode_badge = (
        f'<span style="background:#6f42c1;color:#fff;padding:2px 8px;border-radius:10px;'
        f'font-size:0.75em;font-weight:600;">VECTOR</span>'
        if mode == "Semantic"
        else f'<span style="background:#495057;color:#fff;padding:2px 8px;border-radius:10px;'
             f'font-size:0.75em;font-weight:600;">KEYWORD</span>'
    )
    st.markdown(
        f"{mode_badge} &nbsp; <strong>{len(results)}</strong> result(s) for &nbsp;"
        f"<em>\"{escape(query)}\"</em>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    for item in results:
        fact  = item.get("fact", {})
        score = item.get("score", 0.0)

        entity    = fact.get("entity", "")
        attribute = fact.get("attribute", "")
        value     = fact.get("value", "")
        unit      = fact.get("unit", "") or ""
        period    = fact.get("time_period", "") or ""
        doc_id    = fact.get("document_id", "")
        page      = fact.get("page_num", "?")
        evidence  = (fact.get("evidence") or {}).get("text", "")
        conf      = fact.get("confidence", 0.0)

        # Similarity bar (purple for semantic, grey for keyword)
        bar_color = "#6f42c1" if mode == "Semantic" else "#6c757d"
        bar_pct   = int(score * 100)
        score_html = (
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<div style="flex:1;background:#e9ecef;border-radius:4px;height:6px;">'
            f'<div style="width:{bar_pct}%;background:{bar_color};border-radius:4px;height:6px;"></div>'
            f'</div>'
            f'<span style="font-size:0.8em;color:{bar_color};font-weight:600;white-space:nowrap;">{score:.0%}</span>'
            f'</div>'
        )

        st.markdown(
            f"<strong>{escape(entity)}</strong> › <strong>{escape(attribute)}</strong>"
            f" &nbsp;=&nbsp; {escape(value)} {escape(unit)}"
            + (f" &nbsp;<em>({escape(period)})</em>" if period else ""),
            unsafe_allow_html=True,
        )
        st.markdown(score_html, unsafe_allow_html=True)

        meta_cols = st.columns([3, 1, 1])
        meta_cols[0].caption(f"Document: {doc_id[:20]}...  · page {page}")
        meta_cols[1].caption(f"Confidence: {conf:.0%}")

        with st.expander("Source evidence"):
            st.markdown(
                f'<div class="evidence-box">{escape(str(evidence))}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")



if page == "📤 Upload":
    render_upload()
elif page == "🧩 Fact Explorer":
    render_documents()
elif page == "🔗 Relationships":
    render_relationships()
elif page == "🔍 Search":
    render_search()
elif page == "🎯 Demo Cases":
    render_cases()
