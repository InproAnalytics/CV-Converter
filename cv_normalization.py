import ast
import hashlib
import json


def _norm_list(x):
    """Normalize values that should be list[str]."""
    if x is None:
        return []
    if isinstance(x, list):
        return [str(v).strip() for v in x if str(v).strip()]
    if isinstance(x, str):
        parts = [p.strip() for p in x.split(",")]
        return [p for p in parts if p]
    s = str(x).strip()
    return [s] if s else []


def _responsibilities_to_text(value) -> str:
    """Normalize responsibilities value for UI display/editing (multiline string)."""
    if value is None:
        return ""
    if isinstance(value, list):
        items = [str(x).strip() for x in value if str(x).strip()]
        return "\n".join(items)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return ""
        # Handle stringified list, e.g. "['a', 'b']"
        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, list):
                    items = [str(x).strip() for x in parsed if str(x).strip()]
                    return "\n".join(items)
            except Exception:
                pass
        return s
    return str(value).strip()


def _responsibilities_to_list(value) -> list[str]:
    """Normalize responsibilities value for storage/PDF generation (list[str])."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]

    s = str(value).strip()
    if not s:
        return []

    # Handle stringified list, e.g. "['a', 'b']" or "[\"a\", \"b\"]"
    if s.startswith("[") and s.endswith("]"):
        for parser in (ast.literal_eval, json.loads):
            try:
                parsed = parser(s)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                continue

    # Split multiline / bullet-like text into items
    lines = []
    for line in s.splitlines():
        line = line.strip()
        if not line:
            continue
        line = line.lstrip("•*-·–— ").strip()
        if line:
            lines.append(line)

    # If user pasted bullets inline separated by "•"
    if len(lines) <= 1 and "•" in s:
        parts = [p.strip() for p in s.split("•") if p.strip()]
        parts = [p.lstrip("•*-·–— ").strip() for p in parts]
        lines = [p for p in parts if p]

    return lines


def _stable_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(obj) -> str:
    return hashlib.sha256(_stable_dumps(obj).encode("utf-8")).hexdigest()


def _project_has_content(p: dict) -> bool:
    if not isinstance(p, dict):
        return False
    keys = [
        "project_title",
        "company",
        "role",
        "overview",
        "duration",
        "tech_stack",
        "responsibilities",
        "domains",
    ]
    for k in keys:
        v = p.get(k)
        if isinstance(v, list):
            if any(str(x).strip() for x in v if x is not None):
                return True
        elif v is not None and str(v).strip():
            return True
    return False


def _extract_domains_from_projects(rows: list[dict]) -> list[str]:
    out = set()
    for p in rows if isinstance(rows, list) else []:
        if not isinstance(p, dict):
            continue
        for d in _norm_list(p.get("domains")):
            dd = str(d).strip()
            if dd:
                out.add(dd.title())
    return sorted(out)


def _extract_companies_from_projects(rows: list[dict]) -> list[str]:
    out = set()
    for p in rows if isinstance(rows, list) else []:
        if not isinstance(p, dict):
            continue
        c = str(p.get("company", "") or "").strip()
        if c:
            out.add(c)
    return sorted(out)


def _filter_projects_by_domains(rows: list[dict], selected_domains: list[str]) -> list[dict]:
    sel = {str(d).strip().casefold() for d in (selected_domains or []) if str(d).strip()}
    if not sel:
        return list(rows) if isinstance(rows, list) else []
    out = []
    for p in rows if isinstance(rows, list) else []:
        if not isinstance(p, dict):
            continue
        p_domains = {str(d).strip().casefold() for d in _norm_list(p.get("domains")) if str(d).strip()}
        if p_domains & sel:
            out.append(p)
    return out


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


def languages_to_pdf_format(rows):
    """Return list of {language, level}."""
    out = []
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        if "Sprache" in r or "Niveau" in r:
            out.append({"language": str(r.get("Sprache", "")).strip(), "level": str(r.get("Niveau", "")).strip()})
        else:
            out.append({"language": str(r.get("language", "")).strip(), "level": str(r.get("level", "")).strip()})
    return out
