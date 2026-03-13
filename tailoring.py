"""
Relevance scoring utility for the Alignment PDF.

Deterministic helpers that rank CV projects and skill areas
by their overlap with alignment evidence terms.
Used to enrich the Alignment PDF with Most Relevant Projects
and Most Relevant Skill Areas sections.

No GPT calls.  No content invention.  Read-only on inputs.
"""

import re

from alignment import _CANONICAL


def _canon(tool: str) -> str:
    """Normalize a tool name using the same canonical mapping as alignment.py."""
    s = str(tool).strip().lower()
    return _CANONICAL.get(s, s)


def _collect_evidence_terms(alignment_summary: dict) -> set:
    terms = set()
    for section_key in ("must_have", "nice_to_have"):
        section = alignment_summary.get(section_key, {})
        for item in section.get("matched", []):
            if not isinstance(item, dict):
                continue
            for ev in item.get("evidence", []):
                normalized = str(ev).strip().lower()
                if normalized:
                    terms.add(normalized)
    return terms


def _collect_requirement_keywords(alignment_summary: dict) -> list:
    """
    Collect requirement text phrases from must_have and nice_to_have
    (both matched and missing).  Returns lowercased keyword phrases
    that can be searched in responsibilities/overview text.
    """
    keywords = []
    for section_key in ("must_have", "nice_to_have"):
        section = alignment_summary.get(section_key, {})
        for bucket in ("matched", "missing"):
            for item in section.get(bucket, []):
                if isinstance(item, dict):
                    txt = str(item.get("text", "")).strip().lower()
                else:
                    txt = str(item).strip().lower()
                if txt and len(txt) >= 3:
                    keywords.append(txt)
    return keywords


_STOP_WORDS = frozenset({
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "with",
    "and", "or", "but", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "do", "does", "did", "will", "would",
    "can", "could", "should", "may", "might", "must", "shall",
    "not", "no", "than", "more", "most", "very", "also",
    "from", "by", "as", "into", "through", "within",
    "years", "year", "experience", "proven", "ability",
    "strong", "understanding", "knowledge", "skills",
})


_MIN_PREFIX = 5  


def _words_match(a: str, b: str) -> bool:
    """Check if two words match by sharing a common prefix of 5+ chars."""
    if a == b:
        return True
    prefix_len = min(len(a), len(b), _MIN_PREFIX)
    if prefix_len < _MIN_PREFIX:
        return a == b  
    return a[:_MIN_PREFIX] == b[:_MIN_PREFIX]


def _score_text_against_keywords(text: str, keywords: list) -> int:
    """
    Score text relevance against requirement keywords.
    Extracts meaningful tokens from keywords and checks if they
    appear in text using prefix-based fuzzy matching.
    Returns number of distinct keyword tokens found.
    """
    if not text or not keywords:
        return 0
    text_words = set(re.findall(r"[a-z][a-z0-9#+]*", text.lower()))

    score = 0
    seen = set()
    for kw in keywords:
        tokens = re.findall(r"[a-z][a-z0-9#+]*", kw.lower())
        meaningful = [t for t in tokens if t not in _STOP_WORDS and len(t) >= 3]
        for token in meaningful:
            prefix = token[:_MIN_PREFIX]
            if prefix in seen:
                continue
            for tw in text_words:
                if _words_match(token, tw):
                    score += 1
                    seen.add(prefix)
                    break
    return score


def _score_project(project: dict, evidence: set, keywords: list = None) -> int:
    if not isinstance(project, dict):
        return 0
    score = 0
    tech_stack = project.get("tech_stack", [])
    if isinstance(tech_stack, list):
        score += sum(1 for tool in tech_stack if _canon(tool) in evidence)
    if keywords:
        resps = project.get("responsibilities", [])
        overview = project.get("overview", "") or ""
        text_blob = overview
        if isinstance(resps, list):
            text_blob += " " + " ".join(str(r) for r in resps)
        elif isinstance(resps, str):
            text_blob += " " + resps
        score += _score_text_against_keywords(text_blob, keywords)
    return score


def _matched_tools(items: list, evidence: set) -> list:
    out = []
    for tool in (items if isinstance(items, list) else []):
        if _canon(tool) in evidence:
            out.append(str(tool).strip())
    return out


def _score_skills_row(row: dict, evidence: set) -> int:
    if not isinstance(row, dict):
        return 0
    tools = row.get("tools") or row.get("Werkzeuge", [])
    if not isinstance(tools, list):
        return 0
    return sum(1 for tool in tools if _canon(tool) in evidence)


def reorder_cv_by_relevance(cv_json: dict, alignment_summary: dict) -> dict:
    """
    Reorder projects and skills_overview in cv_json by relevance to
    alignment evidence.  Most relevant items appear first.

    The caller must pass a deep copy — this function mutates in place
    and returns the same dict for convenience.

    No data is added or removed — only order changes.
    """
    evidence = _collect_evidence_terms(alignment_summary)
    keywords = _collect_requirement_keywords(alignment_summary)

    # Reorder projects_experience
    projects = cv_json.get("projects_experience", [])
    if isinstance(projects, list) and projects:
        scored = [(i, _score_project(p, evidence, keywords), p) for i, p in enumerate(projects)]
        scored.sort(key=lambda x: (-x[1], x[0]))
        cv_json["projects_experience"] = [p for _, _, p in scored]

    # Reorder skills_overview
    skills = cv_json.get("skills_overview", [])
    if isinstance(skills, list) and skills:
        scored = [(i, _score_skills_row(r, evidence), r) for i, r in enumerate(skills)]
        scored.sort(key=lambda x: (-x[1], x[0]))
        cv_json["skills_overview"] = [r for _, _, r in scored]

    return cv_json


def compute_relevance_ranking(cv_json: dict, alignment_summary: dict) -> dict:
    """
    Rank CV projects and skill areas by relevance to alignment evidence.

    Returns a dict with:
      relevant_projects:    list of {name, score, matched_tools}
      relevant_skill_areas: list of {category, score, matched_tools}

    Only items with score > 0 are included.
    Sorted descending by score, stable on original order for ties.
    """
    evidence = _collect_evidence_terms(alignment_summary)
    keywords = _collect_requirement_keywords(alignment_summary)

    # Relevant projects
    projects = cv_json.get("projects_experience", [])
    if not isinstance(projects, list):
        projects = []

    proj_ranked = []
    for i, proj in enumerate(projects):
        if not isinstance(proj, dict):
            continue
        score = _score_project(proj, evidence, keywords)
        if score > 0:
            name = (str(proj.get("project_title", "") or "").strip()
                    or str(proj.get("project_name", "") or "").strip()
                    or "Unnamed Project")
            tools = _matched_tools(proj.get("tech_stack", []), evidence)
            proj_ranked.append((i, score, name, tools))

    proj_ranked.sort(key=lambda x: (-x[1], x[0]))
    relevant_projects = [
        {"name": name, "score": score, "matched_tools": tools}
        for _, score, name, tools in proj_ranked
    ]

    # Relevant skill areas
    skills = cv_json.get("skills_overview", [])
    if not isinstance(skills, list):
        skills = []

    skill_ranked = []
    for i, row in enumerate(skills):
        if not isinstance(row, dict):
            continue
        score = _score_skills_row(row, evidence)
        if score > 0:
            cat = (str(row.get("category", "") or "").strip()
                   or str(row.get("Kategorie", "") or "").strip()
                   or "Unknown")
            tools = _matched_tools(row.get("tools") or row.get("Werkzeuge", []), evidence)
            skill_ranked.append((i, score, cat, tools))

    skill_ranked.sort(key=lambda x: (-x[1], x[0]))
    relevant_skill_areas = [
        {"category": cat, "score": score, "matched_tools": tools}
        for _, score, cat, tools in skill_ranked
    ]

    MAX_ITEMS = 5
    return {
        "relevant_projects": relevant_projects[:MAX_ITEMS],
        "relevant_skill_areas": relevant_skill_areas[:MAX_ITEMS],
    }


def _self_test():
    fake_cv = {
        "projects_experience": [
            {"project_title": "Alpha", "tech_stack": ["Java", "Spring"],
             "responsibilities": ["Built solution architecture for treasury system"]},
            {"project_title": "Beta", "tech_stack": ["Python", "FastAPI", "Docker"],
             "responsibilities": ["Developed REST API endpoints"]},
            {"project_title": "Gamma", "tech_stack": ["C++"],
             "responsibilities": ["Low-level systems programming"]},
        ],
        "skills_overview": [
            {"category": "programming_languages", "tools": ["Java", "C++"]},
            {"category": "cloud_platforms", "tools": ["AWS", "Docker"]},
            {"category": "databases", "tools": ["PostgreSQL"]},
        ],
    }
    fake_alignment = {
        "must_have": {
            "matched": [
                {"text": "Python experience", "evidence": ["Python", "FastAPI"]},
                {"text": "Cloud skills", "evidence": ["Docker", "AWS"]},
            ],
        },
        "nice_to_have": {
            "matched": [
                {"text": "API development", "evidence": ["FastAPI"]},
            ],
        },
    }

    result = compute_relevance_ranking(fake_cv, fake_alignment)
    errors = []

    rp = result["relevant_projects"]
    rp_names = [p["name"] for p in rp]
    if "Beta" not in rp_names:
        errors.append(f"FAIL #1: Beta should be in relevant projects, got {rp_names}")
    if len(rp) < 1:
        errors.append(f"FAIL #2: expected at least 1 relevant project, got {len(rp)}")
    if rp and rp[0]["name"] != "Beta":
        errors.append(f"FAIL #3: Beta should be first, got {rp[0]['name']}")

    rsa = result["relevant_skill_areas"]
    if len(rsa) != 1:
        errors.append(f"FAIL #5: expected 1 relevant skill area, got {len(rsa)}")
    elif rsa[0]["category"] != "cloud_platforms":
        errors.append(f"FAIL #6: expected cloud_platforms, got {rsa[0]['category']}")
    elif rsa[0]["score"] != 2:
        errors.append(f"FAIL #7: score expected 2, got {rsa[0]['score']}")

    # Empty evidence -> empty results
    empty = compute_relevance_ranking(fake_cv, {"must_have": {"matched": []}, "nice_to_have": {"matched": []}})
    if empty["relevant_projects"] or empty["relevant_skill_areas"]:
        errors.append("FAIL #8: empty evidence should return empty lists")

    if len(fake_cv["projects_experience"]) != 3:
        errors.append("FAIL #9: original CV was mutated")

    # Reorder test
    import copy as _copy
    reorder_input = _copy.deepcopy(fake_cv)
    reordered = reorder_cv_by_relevance(reorder_input, fake_alignment)
    proj_names = [p["project_title"] for p in reordered["projects_experience"]]
    if proj_names[0] != "Beta":
        errors.append(f"FAIL #10: reorder projects expected Beta first, got {proj_names}")
    skill_cats = [s["category"] for s in reordered["skills_overview"]]
    if skill_cats[0] != "cloud_platforms":
        errors.append(f"FAIL #11: reorder skills expected cloud_platforms first, got {skill_cats[0]}")
    if len(reordered["projects_experience"]) != 3:
        errors.append(f"FAIL #12: reorder lost projects, got {len(reordered['projects_experience'])}")
    if len(reordered["skills_overview"]) != 3:
        errors.append(f"FAIL #13: reorder lost skills, got {len(reordered['skills_overview'])}")
    if reorder_input["projects_experience"][0]["project_title"] != "Beta":
        errors.append("FAIL #14: reorder did not mutate the passed copy")

    if errors:
        for e in errors:
            print(e)
        raise SystemExit(1)

    print("tailoring._self_test: ALL invariants passed.")
    print(f"  relevant projects: {[p['name'] for p in rp]}")
    print(f"  relevant skills:   {[s['category'] for s in rsa]}")


if __name__ == "__main__":
    _self_test()
