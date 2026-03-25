"""
Truth-preserving alignment analysis module.

Compares existing CV JSON against a client role description.
No GPT calls. Purely deterministic matching.
"""

import re
import copy
import io

ENABLE_ALIGNMENT = True

# Deterministic skill normalization

_CANONICAL = {
    "amazon web services": "aws", "aws": "aws",
    "google cloud platform": "gcp", "google cloud": "gcp", "gcp": "gcp",
    "microsoft azure": "azure", "azure": "azure",
    "kubernetes": "kubernetes", "k8s": "kubernetes",
    "javascript": "javascript", "js": "javascript",
    "typescript": "typescript", "ts": "typescript",
    "postgresql": "postgresql", "postgres": "postgresql",
    "react.js": "react", "reactjs": "react", "react": "react",
    "node.js": "node", "nodejs": "node", "node": "node",
    "vue.js": "vue", "vuejs": "vue", "vue": "vue",
    "angular.js": "angular", "angularjs": "angular", "angular": "angular",
    "mongodb": "mongodb", "mongo": "mongodb",
    "terraform": "terraform", "tf": "terraform",
    "ci/cd": "ci/cd", "cicd": "ci/cd",
    "c#": "c#", "csharp": "c#",
    "c++": "c++", "cpp": "c++",
    ".net": ".net", "dotnet": ".net",
    "scikit-learn": "scikit-learn", "sklearn": "scikit-learn",
    "llama-index": "llamaindex", "llama_index": "llamaindex",
    "langchain": "langchain", "lang chain": "langchain",
    "chromadb": "chromadb", "chroma": "chromadb",
    "fastapi": "fastapi", "fast api": "fastapi",
}

_SENIORITY_KEYWORDS = {
    "intern": 0, "trainee": 0, "werkstudent": 0,
    "junior": 1,
    "mid": 2, "mid-level": 2,
    "senior": 3,
    "lead": 4, "team lead": 4,
    "staff": 5,
    "principal": 6, "architect": 6,
    "head": 7, "director": 7,
    "vp": 8,
    "cto": 9, "ceo": 9,
}

# Concept map: high-level requirement phrases -> concrete tools

CONCEPT_MAP = {
    "machine learning": [
        "pytorch", "tensorflow", "scikit-learn", "xgboost",
        "lightgbm", "catboost", "keras",
    ],
    "machine learning frameworks": [
        "pytorch", "tensorflow", "scikit-learn", "xgboost",
        "lightgbm", "catboost", "keras",
    ],
    "ml frameworks": [
        "pytorch", "tensorflow", "scikit-learn", "xgboost",
        "lightgbm", "catboost", "keras",
    ],
    "ml": [
        "pytorch", "tensorflow", "scikit-learn", "xgboost",
        "lightgbm", "catboost", "keras",
    ],
    "deep learning": [
        "pytorch", "tensorflow", "keras",
    ],
    "nlp": [
        "transformers", "spacy", "nltk", "langchain", "llamaindex",
        "huggingface", "bert", "gpt",
    ],
    "natural language processing": [
        "transformers", "spacy", "nltk", "langchain", "llamaindex",
        "huggingface", "bert", "gpt",
    ],
    "llm": [
        "langchain", "llamaindex", "openai", "gpt", "transformers",
        "huggingface", "prompt engineering",
    ],
    "llm-based": [
        "langchain", "llamaindex", "openai", "gpt", "transformers",
    ],
    "large language model": [
        "langchain", "llamaindex", "openai", "gpt", "transformers",
    ],
    "rag": [
        "langchain", "llamaindex", "chromadb", "qdrant",
        "pinecone", "weaviate", "faiss",
    ],
    "rag pipelines": [
        "langchain", "llamaindex", "chromadb", "qdrant",
        "pinecone", "weaviate", "faiss",
    ],
    "retrieval augmented generation": [
        "langchain", "llamaindex", "chromadb", "qdrant",
        "pinecone", "weaviate", "faiss",
    ],
    "vector search": [
        "chromadb", "qdrant", "pinecone", "weaviate", "faiss", "milvus",
    ],
    "vector databases": [
        "chromadb", "qdrant", "pinecone", "weaviate", "faiss", "milvus",
    ],
    "vector stores": [
        "chromadb", "qdrant", "pinecone", "weaviate", "faiss", "milvus",
    ],
    "apis": [
        "fastapi", "django", "flask", "express", "spring boot",
    ],
    "api development": [
        "fastapi", "django", "flask", "express", "spring boot",
    ],
    "rest apis": [
        "fastapi", "django", "flask", "express", "spring boot",
    ],
    "backend": [
        "fastapi", "django", "flask", "express", "spring boot", "node",
    ],
    "backend frameworks": [
        "fastapi", "django", "flask", "express", "spring boot",
    ],
    "cloud": [
        "aws", "gcp", "azure",
    ],
    "cloud environments": [
        "aws", "gcp", "azure",
    ],
    "cloud platforms": [
        "aws", "gcp", "azure",
    ],
    "cloud computing": [
        "aws", "gcp", "azure",
    ],
    "mlops": [
        "mlflow", "kubeflow", "dvc", "airflow", "prefect",
    ],
    "data processing": [
        "spark", "pyspark", "flink", "dask", "ray", "pandas", "numpy",
    ],
    "distributed data processing": [
        "spark", "pyspark", "flink", "dask", "ray",
    ],
    "data engineering": [
        "spark", "pyspark", "airflow", "prefect", "dbt",
    ],
    "containerization": [
        "docker", "kubernetes", "podman",
    ],
    "container orchestration": [
        "kubernetes", "docker swarm", "ecs",
    ],
    "frontend": [
        "react", "vue", "angular", "svelte", "next", "nuxt",
    ],
    "frontend frameworks": [
        "react", "vue", "angular", "svelte", "next", "nuxt",
    ],
    "databases": [
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "dynamodb", "cassandra", "sqlite",
    ],
    "relational databases": [
        "postgresql", "mysql", "sqlite", "mariadb",
    ],
    "nosql": [
        "mongodb", "redis", "dynamodb", "cassandra", "couchdb",
    ],
    "ci/cd": [
        "jenkins", "github actions", "gitlab ci", "circleci",
    ],
    "ci cd": [
        "jenkins", "github actions", "gitlab ci", "circleci",
    ],
    "continuous integration": [
        "jenkins", "github actions", "gitlab ci", "circleci",
    ],
    "infrastructure as code": [
        "terraform", "pulumi", "cloudformation", "ansible",
    ],
    "monitoring": [
        "prometheus", "grafana", "datadog", "new relic",
    ],
    "observability": [
        "prometheus", "grafana", "datadog", "new relic",
    ],
    "testing": [
        "pytest", "jest", "unittest", "selenium", "cypress",
    ],
    "version control": [
        "git", "github", "gitlab", "bitbucket",
    ],
    "agile": [
        "scrum", "kanban", "jira",
    ],
    "data visualization": [
        "matplotlib", "plotly", "seaborn", "tableau", "power bi",
    ],
    "web scraping": [
        "scrapy", "beautifulsoup", "selenium", "playwright",
    ],
    "message queues": [
        "kafka", "rabbitmq", "sqs", "redis",
    ],
    "streaming": [
        "kafka", "flink", "spark streaming", "kinesis",
    ],
}

# Stop words for token-level matching — skipped when checking individual tokens
_MATCH_STOP_WORDS = frozenset({
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "with",
    "is", "are", "was", "were", "be", "been", "being",
    "and", "or", "but", "not", "no", "nor", "so", "yet",
    "experience", "knowledge", "proficiency", "expertise", "familiarity",
    "understanding", "skills", "skill", "ability", "abilities",
    "strong", "good", "deep", "solid", "proven", "demonstrated",
    "hands-on", "working", "practical", "relevant",
    "based", "systems", "system", "tools", "tool",
    "technologies", "technology", "solutions", "solution",
    "services", "service", "platforms", "platform",
    "environments", "environment", "frameworks", "framework",
    "building", "developing", "designing", "implementing", "creating",
    "using", "leveraging", "utilizing", "managing", "maintaining",
    "preferably", "ideally", "including",
})


# Normalization helpers

def _normalize(text):
    """Normalize text for matching: lowercase, strip noise, collapse whitespace."""
    s = text.strip().lower()
    s = re.sub(r"[\"'`\(\)\[\]\{\}]", "", s)
    s = s.replace("_", " ")
    s = s.strip(" .,;:")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _normalize_skill(skill):
    """Normalize a single skill/tool name via canonical mapping."""
    s = skill.strip().lower()
    return _CANONICAL.get(s, s)


def _detect_seniority(text):
    """Return the highest seniority keyword found in *text*."""
    text_lower = text.lower()
    best_kw, best_level = "", -1
    for kw, level in _SENIORITY_KEYWORDS.items():
        if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
            if level > best_level:
                best_kw, best_level = kw, level
    return best_kw


# Role description parser (deterministic)

_MUST_HAVE_RE = re.compile(
    r"(?i)^[\s#*]*(must[\s\-]?have[s]?|required|requirements|key[\s\-]?requirements"
    r"|technical[\s\-]?requirements|minimum[\s\-]?requirements"
    r"|qualifications|core[\s\-]?competenc(?:ies|y)|prerequisites"
    r"|expectations|needed|experience[\s\-]?required"
    r"|(?:you|we)\s+(?:should|need|expect|require|are looking)"
    r"|(?:what|skills)\s+you\s+bring"
    r"|mandatory|essential|pflicht|anforderungen|voraussetzungen|erforderlich"
    r"|ihr\s+profil|was\s+sie\s+mitbringen|was\s+du\s+mitbringst)[\s:]*"
)
_NICE_TO_HAVE_RE = re.compile(
    r"(?i)^[\s#*]*(nice[\s\-]?to[\s\-]?have|preferred|desired|desirable|bonus"
    r"|optional|good[\s\-]?to[\s\-]?have|additional[\s\-]?skills"
    r"|plus|it\s+would\s+be\s+(?:great|nice|good)"
    r"|what\s+would\s+be\s+nice"
    r"|w[uü]nschenswert|von\s+vorteil)[\s:]*"
)
_DOMAIN_RE = re.compile(
    r"(?i)^[\s#*]*(domain|industry|sector|branche)[\s:]+(.+)"
)
_TITLE_RE = re.compile(
    r"(?i)^(role|position|title|stelle|jobtitel)[\s:]+(.+)"
)


def _is_section_header(line):
    s = line.strip()
    if not s:
        return False
    if re.match(r'^[\-\u2022*\u00b7\u25aa\u2192>]', s):
        return False
    if s.endswith(":"):
        return True
    words = s.split()
    if len(words) >= 2 and len(words) <= 5 and s.isupper():
        return True
    return False


def _parse_skill_items(text):
    """Extract individual skill names from a text fragment."""
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(
        r"\d+\+?\s*(years?|jahre?)\s*(of\s+)?(experience\s+)?(in|with|of)?\s*",
        "", text, flags=re.I,
    )
    text = re.sub(
        r"(?i)^(experience|knowledge|proficiency|expertise|familiarity"
        r"|strong|good|deep|solid|hands[\s\-]on)\s+(in|of|with)?\s*",
        "", text,
    )
    items = re.split(r"[,;]|\s+/\s+", text)
    return [s.strip() for s in items if s.strip() and len(s.strip()) > 1]


def _parse_bullet_line(line):
    line = re.sub(r"^[\s\-\u2022*\u00b7\u25aa\u2192>]+", "", line).strip()
    if not line:
        return []
    return [line]


def parse_role_description(text):
    """Deterministically parse a role description into structured components."""
    result = {
        "role_title": "",
        "seniority": "",
        "must_have": [],
        "nice_to_have": [],
        "domain_hints": [],
    }
    if not text or not text.strip():
        return result

    lines = [l.strip() for l in text.strip().split("\n")]

    # Role title 
    for line in lines:
        if not line:
            continue
        m = _TITLE_RE.match(line)
        if m:
            result["role_title"] = m.group(2).strip()
            break
    if not result["role_title"]:
        for line in lines:
            if not line:
                continue
            if _MUST_HAVE_RE.match(line) or _NICE_TO_HAVE_RE.match(line):
                continue
            if _DOMAIN_RE.match(line):
                continue
            if len(line) < 80:
                result["role_title"] = line
                break

    if result["role_title"]:
        result["seniority"] = _detect_seniority(result["role_title"])

    current_section = None
    for line in lines:
        if not line:
            continue

        if _MUST_HAVE_RE.match(line):
            current_section = "must_have"
            after_colon = line.split(":", 1)[1].strip() if ":" in line else ""
            if after_colon:
                result["must_have"].extend(_parse_skill_items(after_colon))
            continue

        if _NICE_TO_HAVE_RE.match(line):
            current_section = "nice_to_have"
            after_colon = line.split(":", 1)[1].strip() if ":" in line else ""
            if after_colon:
                result["nice_to_have"].extend(_parse_skill_items(after_colon))
            continue

        dm = _DOMAIN_RE.match(line)
        if dm:
            result["domain_hints"].extend(
                [d.strip() for d in dm.group(2).split(",") if d.strip()]
            )
            current_section = "domain"
            continue

        if _is_section_header(line):
            current_section = None
            continue

        if current_section == "must_have":
            result["must_have"].extend(_parse_bullet_line(line))
        elif current_section == "nice_to_have":
            result["nice_to_have"].extend(_parse_bullet_line(line))
        elif current_section == "domain":
            result["domain_hints"].extend(
                [d.strip() for d in line.split(",") if d.strip()]
            )

    result["must_have"] = list(dict.fromkeys(result["must_have"]))
    result["nice_to_have"] = list(dict.fromkeys(result["nice_to_have"]))
    result["domain_hints"] = list(dict.fromkeys(result["domain_hints"]))

    if not result["must_have"] and not result["nice_to_have"]:
        for line in lines:
            if not line:
                continue
            if line == result["role_title"]:
                continue
            if _is_section_header(line):
                continue
            if _DOMAIN_RE.match(line) or _TITLE_RE.match(line):
                continue
            cleaned = re.sub(r"^[\s\-\u2022*\u00b7\u25aa\u2192>]+", "", line).strip()
            if cleaned and len(cleaned) > 1:
                result["must_have"].append(cleaned)
        result["must_have"] = list(dict.fromkeys(result["must_have"]))

    if not result["must_have"] and not result["nice_to_have"] and result["role_title"]:
        result["must_have"].append(result["role_title"])

    return result


# Candidate evidence collection (from JSON only)

def collect_candidate_terms(cv_json):
    """
    Collect ALL candidate evidence terms from CV JSON into a single
    normalized set. Sources: hard_skills, skills_overview, tech_stack,
    project roles, project domains, top-level domains, title.
    """
    terms = set()

    hs = cv_json.get("hard_skills", {})
    if isinstance(hs, dict):
        for cat_name, tools_list in hs.items():
            if isinstance(cat_name, str) and cat_name.strip():
                terms.add(_normalize(cat_name))
            if isinstance(tools_list, list):
                for t in tools_list:
                    if isinstance(t, str) and t.strip():
                        terms.add(_normalize_skill(t))

    for s in cv_json.get("skills_overview", []):
        if not isinstance(s, dict):
            continue
        cat = s.get("category", "")
        if isinstance(cat, str) and cat.strip():
            terms.add(_normalize(cat))
        for t in s.get("tools", []):
            if isinstance(t, str) and t.strip():
                terms.add(_normalize_skill(t))

    for p in cv_json.get("projects_experience", []):
        if not isinstance(p, dict):
            continue
        for t in p.get("tech_stack", []):
            if isinstance(t, str) and t.strip():
                terms.add(_normalize_skill(t))
        role = p.get("role", "")
        if isinstance(role, str) and role.strip():
            terms.add(_normalize(role))
        for d in p.get("domains", []):
            if isinstance(d, str) and d.strip():
                terms.add(_normalize(d))

    for d in cv_json.get("domains", []):
        if isinstance(d, str) and d.strip():
            terms.add(_normalize(d))

    title = cv_json.get("title", "")
    if isinstance(title, str) and title.strip():
        terms.add(_normalize(title))

    terms.discard("")
    return terms


# Requirement matching (deterministic, with evidence)

def _match_requirement(req_text, candidate_terms):
    """
    Match a single requirement against candidate terms.
    Handles 'or'/'and'/'und'/'oder' splits and concept mapping.
    Returns (matched: bool, evidence: list[str]).
    """
    normalized_req = _normalize(req_text)
    if not normalized_req:
        return (False, [])

    # Split on "or" / "and" / "und" / "oder" to get alternatives
    alternatives = re.split(r'\b(?:or|and|und|oder)\b', normalized_req)
    alternatives = [a.strip() for a in alternatives if a.strip()]
    if not alternatives:
        alternatives = [normalized_req]

    evidence = set()

    for alt in alternatives:
        # --- 1. Direct exact match of full alternative ---
        canonical_alt = _CANONICAL.get(alt, alt)
        if canonical_alt in candidate_terms:
            evidence.add(canonical_alt)

        # --- 2. Substring match for short alternatives (1-2 words) ---
        if len(alt.split()) <= 2 and len(canonical_alt) >= 3:
            for c in candidate_terms:
                if len(c) >= 3 and (canonical_alt in c or c in canonical_alt):
                    evidence.add(c)

        # --- 3. Token-level exact match (skip stop words) ---
        tokens = alt.split()
        for token in tokens:
            if len(token) < 2 or token in _MATCH_STOP_WORDS:
                continue
            ct = _CANONICAL.get(token, token)
            if ct in candidate_terms:
                evidence.add(ct)

        # --- 4. Concept map match (word-boundary) ---
        for concept_key, concept_tools in CONCEPT_MAP.items():
            pattern = r'\b' + re.escape(concept_key) + r'\b'
            if re.search(pattern, alt) or alt == concept_key:
                for tool in concept_tools:
                    tc = _CANONICAL.get(tool, tool)
                    if tc in candidate_terms:
                        evidence.add(tc)

    return (len(evidence) > 0, sorted(evidence))


def _estimate_candidate_seniority(cv_json):
    """Estimate seniority from the candidate's roles and title."""
    best_kw, best_level = "", -1
    title = cv_json.get("title", "")
    if title:
        s = _detect_seniority(title)
        level = _SENIORITY_KEYWORDS.get(s, -1)
        if level > best_level:
            best_kw, best_level = s, level
    for p in cv_json.get("projects_experience", []):
        if not isinstance(p, dict):
            continue
        role = p.get("role", "")
        if role:
            s = _detect_seniority(role)
            level = _SENIORITY_KEYWORDS.get(s, -1)
            if level > best_level:
                best_kw, best_level = s, level
    return best_kw


# Main alignment computation

def compute_alignment(cv_json, role_description):
    """
    Compute alignment summary between CV JSON and role description.
    No GPT calls. Purely deterministic.
    Returns structured result with per-requirement evidence.
    """
    parsed = parse_role_description(role_description)
    candidate_terms = collect_candidate_terms(cv_json)

    # Must-have matching with evidence
    must_matched = []
    must_missing = []
    for req in parsed["must_have"]:
        matched, ev = _match_requirement(req, candidate_terms)
        entry = {"text": req, "evidence": ev}
        if matched:
            must_matched.append(entry)
        else:
            must_missing.append(entry)

    # Nice-to-have matching with evidence
    nice_matched = []
    nice_missing = []
    for req in parsed["nice_to_have"]:
        matched, ev = _match_requirement(req, candidate_terms)
        entry = {"text": req, "evidence": ev}
        if matched:
            nice_matched.append(entry)
        else:
            nice_missing.append(entry)

    # Seniority
    candidate_seniority = _estimate_candidate_seniority(cv_json)
    seniority_match = ""
    if parsed["seniority"] and candidate_seniority:
        req_level = _SENIORITY_KEYWORDS.get(parsed["seniority"], -1)
        cand_level = _SENIORITY_KEYWORDS.get(candidate_seniority, -1)
        if req_level >= 0 and cand_level >= 0:
            seniority_match = cand_level >= req_level

    # Domain matching
    candidate_domains = [
        d.lower() for d in (cv_json.get("domains", []) or []) if isinstance(d, str)
    ]
    required_domains = [d.lower() for d in parsed["domain_hints"]]
    domain_match = ""
    if required_domains and candidate_domains:
        domain_match = any(
            rd in cd or cd in rd
            for rd in required_domains
            for cd in candidate_domains
        )

    # Role title match
    candidate_role = cv_json.get("title", "")
    role_title_match = False
    if parsed["role_title"] and candidate_role:
        stop_words = {
            "the", "a", "an", "and", "or", "for", "in", "at", "of",
            "m/f/d", "(m/f/d)", "m/w/d", "(m/w/d)", "-",
        }
        rt_words = set(parsed["role_title"].lower().split()) - stop_words
        cr_words = set(candidate_role.lower().split()) - stop_words
        if rt_words and cr_words:
            overlap = rt_words & cr_words
            role_title_match = len(overlap) >= min(len(rt_words), len(cr_words)) * 0.5

    # Overall alignment — deterministic thresholds
    total_must = len(parsed["must_have"])
    matched_must = len(must_matched)
    if total_must == 0:
        overall = "unclear"
    elif matched_must / total_must >= 0.75:
        overall = "strong_match"
    elif matched_must / total_must >= 0.40:
        overall = "partial_match"
    else:
        overall = "weak_match"

    # Notes
    notes = []
    if not parsed["must_have"]:
        notes.append("No must-have skills could be parsed from role description.")
    if not candidate_seniority:
        notes.append("Candidate seniority could not be determined from CV data.")
    if not parsed["seniority"]:
        notes.append("Required seniority not specified in role description.")

    return {
        "candidate_name": cv_json.get("full_name", ""),
        "target_role_title": parsed["role_title"],
        "candidate_role_title": candidate_role,
        "role_title_match": role_title_match,
        "seniority_required": parsed["seniority"],
        "seniority_estimated": candidate_seniority,
        "seniority_match": seniority_match,
        "must_have": {
            "matched": must_matched,
            "missing": must_missing,
        },
        "nice_to_have": {
            "matched": nice_matched,
            "missing": nice_missing,
        },
        "domain_required": parsed["domain_hints"],
        "domain_candidate": cv_json.get("domains", []),
        "domain_match": domain_match,
        "notes": notes,
        "overall_alignment": overall,
    }


# Deterministic self-test

def _self_test():
    """
    Deterministic self-test with synthetic data.
    Validates concept mapping, evidence tracking, and scoring.
    Returns (passed: bool, details: str).
    """
    test_cv = {
        "title": "Senior ML Engineer",
        "domains": ["AI"],
        "hard_skills": {
            "Programming Languages": ["Python"],
            "ML & AI": ["PyTorch", "Transformers"],
            "LLM & RAG": ["LangChain", "LlamaIndex"],
            "APIs": ["FastAPI"],
            "Cloud": ["AWS", "Azure"],
            "Vector DBs": ["ChromaDB", "Qdrant"],
        },
        "skills_overview": [
            {"category": "ML Frameworks", "tools": ["PyTorch", "Transformers"],
             "years_of_experience": ""},
            {"category": "Cloud", "tools": ["AWS", "Azure"],
             "years_of_experience": ""},
        ],
        "projects_experience": [
            {
                "project_title": "RAG System",
                "company": "TestCo",
                "role": "Senior ML Engineer",
                "duration": "2023-2024",
                "responsibilities": [],
                "tech_stack": ["Python", "LangChain", "ChromaDB", "FastAPI"],
                "domains": ["AI"],
            },
        ],
    }

    test_role = """Senior ML Engineer (m/f/d)

Must-have:
- Experience with machine learning frameworks
- NLP or LLM-based systems
- Building APIs for ML services
- Cloud environments
- RAG pipelines
- Vector search systems

Nice-to-have:
- Kubernetes
- MLOps experience"""

    result = compute_alignment(test_cv, test_role)

    must = result["must_have"]
    nice = result["nice_to_have"]

    lines = []
    lines.append(f"Overall: {result['overall_alignment']}")
    lines.append(f"Must-have matched ({len(must['matched'])}/{len(must['matched']) + len(must['missing'])}):")
    for m in must["matched"]:
        lines.append(f"  [+] {m['text']}  ->  evidence: {m['evidence']}")
    lines.append(f"Must-have missing ({len(must['missing'])}):")
    for m in must["missing"]:
        lines.append(f"  [-] {m['text']}")
    lines.append(f"Nice-to-have matched ({len(nice['matched'])}/{len(nice['matched']) + len(nice['missing'])}):")
    for m in nice["matched"]:
        lines.append(f"  [+] {m['text']}  ->  evidence: {m['evidence']}")
    lines.append(f"Nice-to-have missing ({len(nice['missing'])}):")
    for m in nice["missing"]:
        lines.append(f"  [-] {m['text']}")

    # Validation: at least 5 of 6 must-haves should match, overall = strong_match
    passed = len(must["matched"]) >= 5 and result["overall_alignment"] == "strong_match"

    details = "\n".join(lines)
    return (passed, details)


if __name__ == "__main__":
    passed, details = _self_test()
    print("SELF-TEST", "PASSED" if passed else "FAILED")
    print(details)
