"""
Candidate Ranking batch-process multiple CVs against one role description,
rank them by a weighted alignment score (0–100).
"""

import streamlit as st
import json
import os
import re
import tempfile
import time

from pdf_processor import prepare_cv_text, clean_cv_text
from chatgpt_client import ask_chatgpt_v2
from postprocess import postprocess_filled_cv
from alignment import compute_alignment
import copy
from tailoring import reorder_cv_by_relevance
from cv_pdf_generator import create_pretty_first_section
from skill_mapper import remap_hard_skills

MAX_BATCH_SIZE = 10
MODEL = "gpt-4.1-mini"

st.set_page_config(page_title="Candidate Ranking", layout="wide")

st.markdown("""
<style>
div.stButton > button {
    border: 1.5px solid #b0c4de;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

st.title("Candidate Ranking")
st.markdown("Upload multiple CVs and a role description to rank candidates by fit.")


# Scoring

def compute_score(alignment_summary: dict) -> float:
    """
    Weighted score 0–100:
        - must-have coverage:  60%
        - nice-to-have coverage: 20%
        - seniority fit:       10%
        - domain fit:          10%
    """
    must = alignment_summary.get("must_have", {})
    total_must = len(must.get("matched", [])) + len(must.get("missing", []))
    matched_must = len(must.get("matched", []))
    must_score = (matched_must / total_must * 100) if total_must > 0 else 50

    nice = alignment_summary.get("nice_to_have", {})
    total_nice = len(nice.get("matched", [])) + len(nice.get("missing", []))
    matched_nice = len(nice.get("matched", []))
    nice_score = (matched_nice / total_nice * 100) if total_nice > 0 else 50

    seniority_match = alignment_summary.get("seniority_match", "")
    if seniority_match is True:
        seniority_score = 100
    elif seniority_match is False:
        seniority_score = 0
    else:
        seniority_score = 50  

    domain_match = alignment_summary.get("domain_match", "")
    if domain_match is True:
        domain_score = 100
    elif domain_match is False:
        domain_score = 0
    else:
        domain_score = 50  

    total = (
        must_score * 0.60
        + nice_score * 0.20
        + seniority_score * 0.10
        + domain_score * 0.10
    )
    return round(total, 1)


# Single CV pipeline

def process_single_cv(pdf_bytes: bytes, filename: str, role_desc: str) -> dict:
    """
    Convert one CV PDF → JSON → alignment → score.
    Returns a result dict (always), with 'error' key on failure.
    """
    result = {"filename": filename, "name": "—", "role": "—", "score": 0,
                "overall": "—", "alignment": None, "cv_json": None, "error": None}
    try:
        # Write to temp file (prepare_cv_text needs a path)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            prepared_text, raw_text = prepare_cv_text(tmp_path)
            prepared_text = clean_cv_text(prepared_text)

            gpt_result = ask_chatgpt_v2(prepared_text, model=MODEL, detailed_responsibilities=True)
            raw_resp = (gpt_result or {}).get("raw_response", "")
            if not raw_resp:
                result["error"] = "GPT returned empty response"
                return result

            cleaned_resp = raw_resp.strip()
            if cleaned_resp.startswith("```"):
                cleaned_resp = re.sub(r"^```(?:json)?\s*", "", cleaned_resp)
                cleaned_resp = re.sub(r"\s*```\s*$", "", cleaned_resp)
            brace_start = cleaned_resp.find("{")
            if brace_start >= 0:
                depth, i = 0, brace_start
                in_str = False
                while i < len(cleaned_resp):
                    ch = cleaned_resp[i]
                    if ch == '"' and (i == 0 or cleaned_resp[i - 1] != '\\'):
                        in_str = not in_str
                    elif not in_str:
                        if ch == '{':
                            depth += 1
                        elif ch == '}':
                            depth -= 1
                            if depth == 0:
                                cleaned_resp = cleaned_resp[brace_start:i + 1]
                                break
                    i += 1

            cv_json = json.loads(cleaned_resp)
            cv_json = postprocess_filled_cv(cv_json, raw_text)

            alignment = compute_alignment(cv_json, role_desc)
            score = compute_score(alignment)

            result["cv_json"] = cv_json
            result["name"] = alignment.get("candidate_name") or cv_json.get("full_name", "—")
            result["role"] = alignment.get("candidate_role_title") or cv_json.get("title", "—")
            result["score"] = score
            result["overall"] = alignment.get("overall_alignment", "—")
            result["alignment"] = alignment
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        result["error"] = str(e)

    return result


# ---------------------------------------------------------------------------
# Tailored CV helpers
# ---------------------------------------------------------------------------
TOP_N = 3


def _normalize_skills_for_pdf(json_data):
    """Normalize skills_overview from German editor keys to English PDF keys."""
    skills = json_data.get("skills_overview", [])
    if not isinstance(skills, list):
        return json_data
    normalized = []
    for row in skills:
        if not isinstance(row, dict):
            continue
        cat = (row.get("category") or row.get("Kategorie") or "").strip()
        tools = row.get("tools")
        if tools is None:
            tools = row.get("Werkzeuge", [])
        yoe = row.get("years_of_experience")
        if yoe is None:
            yoe = row.get("Jahre Erfahrung")
        if yoe is None or yoe == "":
            yoe = "0"
        if not cat:
            continue
        normalized.append({"category": cat, "tools": tools, "years_of_experience": str(yoe)})
    json_data["skills_overview"] = normalized
    return json_data


def _remove_empty_fields(x):
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            vv = _remove_empty_fields(v)
            if vv in (None, "", [], {}):
                continue
            out[k] = vv
        return out
    if isinstance(x, list):
        out = []
        for it in x:
            vv = _remove_empty_fields(it)
            if vv in (None, "", [], {}):
                continue
            out.append(vv)
        return out
    return x


def generate_tailored_cv(result: dict) -> dict:
    """
    Generate a tailored CV PDF for one candidate.
    Returns dict with keys: name, score, pdf_bytes, error.
    """
    out = {"name": result["name"], "score": result["score"],
           "pdf_bytes": None, "error": None}
    try:
        cv_json = copy.deepcopy(result["cv_json"])
        alignment = result["alignment"]

        # Reorder projects/skills by relevance
        cv_json = reorder_cv_by_relevance(cv_json, alignment)

        # Inject position matched skills
        pos_skills = set()
        for sec in ("must_have", "nice_to_have"):
            for item in alignment.get(sec, {}).get("matched", []):
                if isinstance(item, dict):
                    for ev in item.get("evidence", []):
                        if str(ev).strip():
                            pos_skills.add(str(ev).strip())
        cv_json["_position_skills"] = sorted(pos_skills)
        cv_json["_target_role_title"] = alignment.get("target_role_title", "")

        _PLACEHOLDER_RE = re.compile(r"(?i)^(unknown|n/?a|not\s+available|tbd|none)$")
        for project in cv_json.get("projects_experience", []):
            if isinstance(project, dict):
                dur = (project.get("duration") or "").strip()
                if _PLACEHOLDER_RE.match(dur):
                    project["duration"] = ""

        cv_json["hard_skills"] = remap_hard_skills(cv_json.get("hard_skills", {}))

        cv_json = _normalize_skills_for_pdf(cv_json)
        cv_json = _remove_empty_fields(cv_json)

        # Generate PDF
        name = cv_json.get("full_name", "Candidate")
        prefix = f"CV Inpro Tailored {name}"
        pdf_path = create_pretty_first_section(
            cv_json, output_dir="data_output", prefix=prefix
        )
        with open(pdf_path, "rb") as fh:
            out["pdf_bytes"] = fh.read()
    except Exception as e:
        out["error"] = str(e)
    return out


# File upload
uploaded_files = st.file_uploader(
    f"Upload CV PDFs (max {MAX_BATCH_SIZE})",
    type=["pdf"],
    accept_multiple_files=True,
    key="ranking_pdfs",
)

if uploaded_files and len(uploaded_files) > MAX_BATCH_SIZE:
    st.warning(f"Maximum {MAX_BATCH_SIZE} CVs per batch. Only the first {MAX_BATCH_SIZE} will be processed.")
    uploaded_files = uploaded_files[:MAX_BATCH_SIZE]

# Role description
role_desc = st.text_area(
    "Paste the client role description",
    height=200,
    key="ranking_role_desc",
)

# Rank button
if st.button("Rank Candidates", key="btn_rank", disabled=not uploaded_files or not role_desc):
    if not role_desc.strip():
        st.warning("Please paste a role description.")
    else:
        results = []
        progress = st.progress(0)
        status = st.empty()
        total = len(uploaded_files)

        for i, f in enumerate(uploaded_files):
            status.text(f"Processing CV {i + 1} of {total}: {f.name}")
            progress.progress((i) / total)

            pdf_bytes = f.read()
            res = process_single_cv(pdf_bytes, f.name, role_desc.strip())
            results.append(res)

        progress.progress(1.0)
        status.text(f"Done — {total} CVs processed.")

        results.sort(key=lambda r: r["score"], reverse=True)
        st.session_state["ranking_results"] = results

# Display results

if "ranking_results" in st.session_state:
    results = st.session_state["ranking_results"]

    st.markdown("---")
    st.subheader("Ranking Results")

    table_data = []
    for rank, r in enumerate(results, 1):
        must = r.get("alignment", {}).get("must_have", {}) if r["alignment"] else {}
        nice = r.get("alignment", {}).get("nice_to_have", {}) if r["alignment"] else {}
        total_must = len(must.get("matched", [])) + len(must.get("missing", []))
        matched_must = len(must.get("matched", []))
        total_nice = len(nice.get("matched", [])) + len(nice.get("missing", []))
        matched_nice = len(nice.get("matched", []))

        if r["error"]:
            status = "❌ Error"
        elif r["score"] >= 75:
            status = "Strong Match"
        elif r["score"] >= 50:
            status = "Partial Match"
        else:
            status = "Weak Match"

        table_data.append({
            "Rank": rank,
            "Name": r["name"],
            "Role": r["role"],
            "Score": r["score"],
            "Must-Have": f"{matched_must}/{total_must}" if not r["error"] else "—",
            "Nice-To-Have": f"{matched_nice}/{total_nice}" if not r["error"] else "—",
            "Overall": status,
        })

    st.dataframe(
        table_data,
        width="stretch",
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
        },
    )

    for rank, r in enumerate(results, 1):
        label = f"#{rank} — {r['name']} ({r['score']} pts)"
        if r["error"]:
            label += f" ⚠️ {r['error'][:50]}"

        with st.expander(label, expanded=False):
            if r["error"]:
                st.error(f"Error processing {r['filename']}: {r['error']}")
                continue

            a = r["alignment"]
            if not a:
                st.info("No alignment data.")
                continue

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Score", f"{r['score']}/100")
            with col2:
                must = a.get("must_have", {})
                total_m = len(must.get("matched", [])) + len(must.get("missing", []))
                st.metric("Must-Have", f"{len(must.get('matched', []))}/{total_m}")
            with col3:
                nice = a.get("nice_to_have", {})
                total_n = len(nice.get("matched", [])) + len(nice.get("missing", []))
                st.metric("Nice-To-Have", f"{len(nice.get('matched', []))}/{total_n}")

            # Seniority & Domain
            st.markdown(f"**Seniority:** required={a.get('seniority_required', 'N/A')}, "
                        f"estimated={a.get('seniority_estimated', 'N/A')}, "
                        f"match={'✅' if a.get('seniority_match') is True else '❌' if a.get('seniority_match') is False else '—'}")
            st.markdown(f"**Domain:** required={', '.join(a.get('domain_required', [])) or 'N/A'}, "
                        f"match={'✅' if a.get('domain_match') is True else '❌' if a.get('domain_match') is False else '—'}")

            # Must-have details
            must = a.get("must_have", {})
            if must.get("matched"):
                st.markdown("**Must-have matched:**")
                for m in must["matched"]:
                    txt = m["text"] if isinstance(m, dict) else str(m)
                    ev = m.get("evidence", []) if isinstance(m, dict) else []
                    ev_str = f" *({', '.join(ev[:5])})*" if ev else ""
                    st.markdown(f"- :green[+] **{txt}**{ev_str}")
            if must.get("missing"):
                st.markdown("**Must-have missing:**")
                for m in must["missing"]:
                    txt = m["text"] if isinstance(m, dict) else str(m)
                    st.markdown(f"- :red[-] {txt}")

            # Nice-to-have details
            nice = a.get("nice_to_have", {})
            if nice.get("matched"):
                st.markdown("**Nice-to-have matched:**")
                for m in nice["matched"]:
                    txt = m["text"] if isinstance(m, dict) else str(m)
                    ev = m.get("evidence", []) if isinstance(m, dict) else []
                    ev_str = f" *({', '.join(ev[:5])})*" if ev else ""
                    st.markdown(f"- :green[+] **{txt}**{ev_str}")
            if nice.get("missing"):
                st.markdown("**Nice-to-have missing:**")
                for m in nice["missing"]:
                    txt = m["text"] if isinstance(m, dict) else str(m)
                    st.markdown(f"- :red[-] {txt}")

            # Notes
            notes = a.get("notes", [])
            if notes:
                st.markdown("**Notes:**")
                for n in notes:
                    st.markdown(f"- {n}")

            # Per-candidate tailored CV generation
            if r["cv_json"] is not None:
                st.markdown("---")
                tkey = f"tailored_individual_{r['filename']}"
                if st.button("Generate Tailored CV", key=f"btn_{tkey}"):
                    with st.spinner(f"Generating tailored CV for {r['name']}..."):
                        t_result = generate_tailored_cv(r)
                    if "tailored_individual" not in st.session_state:
                        st.session_state["tailored_individual"] = {}
                    st.session_state["tailored_individual"][r["filename"]] = t_result
                    if t_result["error"]:
                        st.error(f"Failed: {t_result['error']}")
                    else:
                        st.success("Tailored CV ready.")

                # Show download if previously generated
                stored = st.session_state.get("tailored_individual", {}).get(r["filename"])
                if stored and stored.get("pdf_bytes"):
                    st.download_button(
                        label="Download Tailored CV",
                        data=stored["pdf_bytes"],
                        file_name=f"CV_Tailored_{r['name'].replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key=f"dl_individual_{r['filename']}",
                    )



# UI only when ranking results exist

if "ranking_results" in st.session_state:
    results = st.session_state["ranking_results"]

    valid = [r for r in results if not r["error"] and r["cv_json"] is not None]
    top = valid[:TOP_N]

    if top:
        st.markdown("---")
        if st.button(f"Generate Tailored CV for Top {min(len(top), TOP_N)} Candidates",
                        key="btn_tailored"):
            tailored_results = []
            progress = st.progress(0)
            status_text = st.empty()

            for i, candidate in enumerate(top):
                status_text.text(f"Generating tailored CV {i + 1} of {len(top)}: {candidate['name']}")
                progress.progress(i / len(top))
                t_result = generate_tailored_cv(candidate)
                tailored_results.append(t_result)

            progress.progress(1.0)
            status_text.text(f"Done — {len(top)} tailored CVs generated.")
            st.session_state["tailored_results"] = tailored_results

    # Display tailored CV results
    if "tailored_results" in st.session_state:
        st.subheader("Tailored CVs")
        for t in st.session_state["tailored_results"]:
            col1, col2 = st.columns([3, 1])
            with col1:
                if t["error"]:
                    st.error(f"{t['name']} (Score: {t['score']}) — Error: {t['error']}")
                else:
                    st.success(f"{t['name']} (Score: {t['score']}) — Ready")
            with col2:
                if t["pdf_bytes"]:
                    st.download_button(
                        label=f"Download",
                        data=t["pdf_bytes"],
                        file_name=f"CV_Tailored_{t['name'].replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key=f"dl_tailored_{t['name']}",
                    )
