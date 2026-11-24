"""ATS Scorer Agent: six-component resume score with actionable issues."""
import re
from statistics import mean

from .parser import ACTION_VERBS

COMPONENTS = {
    "keyword": ("Keyword match", 0.30),
    "impact": ("Bullet impact", 0.20),
    "evidence": ("Skill evidence", 0.15),
    "portfolio": ("GitHub portfolio", 0.15),
    "sections": ("Structure", 0.10),
    "format": ("Format & length", 0.10),
}


def bullet_quality(text: str) -> dict:
    words = text.split()
    first = re.sub(r"[^a-z\-]", "", words[0].lower()) if words else ""
    verb_ok = first in ACTION_VERBS
    has_metric = bool(re.search(r"\d", text))
    length_ok = 8 <= len(words) <= 32
    issues = []
    if not verb_ok:
        issues.append("does not start with a strong action verb")
    if not has_metric:
        issues.append("has no measurable result (number, %, accuracy, users)")
    if not length_ok:
        issues.append("is too short" if len(words) < 8 else "is too long")
    return {"verb_ok": verb_ok, "has_metric": has_metric, "length_ok": length_ok, "issues": issues,
            "score": 0.4 * verb_ok + 0.4 * has_metric + 0.2 * length_ok}


def grade(score: float) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Strong"
    if score >= 55:
        return "Good, needs polish"
    if score >= 40:
        return "Needs improvement"
    return "Weak"


def score_resume(parsed: dict, target: dict) -> dict:
    tw = target["weights"]
    found = set(parsed["skills"])
    matched = sorted((s for s in tw if s in found), key=lambda s: -tw[s])
    missing = sorted((s for s in tw if s not in found), key=lambda s: -tw[s])
    total = sum(tw.values()) or 1
    issues = []

    # 1. keyword match
    kw = 100 * sum(tw[s] for s in matched) / total
    must_missing = [s for s in missing if tw[s] == 3]
    if must_missing:
        issues.append({"severity": "high", "area": "Keywords",
                       "text": f"Missing {len(must_missing)} must-have skill(s) for this target: {', '.join(must_missing[:6])}."})
    elif missing:
        issues.append({"severity": "low", "area": "Keywords",
                       "text": f"Nice-to-have skills not found: {', '.join(missing[:5])}."})

    # 2. bullet impact
    bullets = parsed["bullets"]
    if bullets:
        quals = [bullet_quality(b["text"]) for b in bullets]
        impact = 100 * mean(q["score"] for q in quals)
        no_metric = sum(not q["has_metric"] for q in quals)
        no_verb = sum(not q["verb_ok"] for q in quals)
        if no_metric:
            issues.append({"severity": "high" if no_metric > len(quals) / 2 else "medium", "area": "Impact",
                           "text": f"{no_metric} of {len(quals)} bullets have no measurable result (numbers, %, accuracy, users)."})
        if no_verb:
            issues.append({"severity": "medium", "area": "Impact",
                           "text": f"{no_verb} bullet(s) do not start with a strong action verb."})
    else:
        impact = 0
        issues.append({"severity": "high", "area": "Impact",
                       "text": "No bullet points found under Projects/Experience. Add 2-3 result-oriented bullets per project."})

    # 3. skill evidence
    skills = parsed["skills"]
    if not parsed["has_evidence_sections"] or not skills:
        evidence = 50
    else:
        evidence = 100 * sum(m["demonstrated"] for m in skills.values()) / len(skills)
        listed_only = [s for s, m in skills.items() if not m["demonstrated"]]
        if listed_only:
            issues.append({"severity": "medium", "area": "Evidence",
                           "text": f"{len(listed_only)} skill(s) are listed but not shown in any project or job: "
                                   f"{', '.join(listed_only[:6])}. Interviewers will ask for proof."})

    # 4. GitHub portfolio
    links = parsed["links"]
    portfolio = 0
    if links["github_profile"]:
        portfolio += 40
    elif parsed["mentions_github"]:
        portfolio += 15
        issues.append({"severity": "high", "area": "Portfolio", "text": "GitHub is mentioned but no profile link was found. Add the full URL."})
    else:
        issues.append({"severity": "high", "area": "Portfolio", "text": "No GitHub link found. Many AI/ML roles require one."})
    portfolio += min(len(links["repos"]), 3) / 3 * 60
    if len(links["repos"]) < 2 and links["github_profile"]:
        issues.append({"severity": "medium", "area": "Portfolio",
                       "text": f"Only {len(links['repos'])} project repo link(s) found. Link each project to its own repository."})

    # 5. structure
    secs = set(parsed["section_names"])
    weights = {"contact": 20, "skills": 25, "projects": 25, "education": 15, "experience": 10, "summary": 5}
    present = {"contact": bool(parsed["email"] and parsed["phone"]), "skills": "skills" in secs,
               "projects": "projects" in secs, "education": "education" in secs,
               "experience": "experience" in secs or parsed["project_count"] >= 2, "summary": "summary" in secs}
    structure = 100 * sum(weights[k] for k, ok in present.items() if ok) / sum(weights.values())
    absent = [k for k, ok in present.items() if not ok]
    if absent:
        issues.append({"severity": "medium" if "contact" in absent or "skills" in absent else "low", "area": "Structure",
                       "text": f"Missing or unrecognised section(s): {', '.join(absent)}."})

    # 6. format
    wc, f = parsed["words"], 0
    f += 40 if 250 <= wc <= 900 else (20 if 150 <= wc <= 1100 else 0)
    f += 20 if parsed["pages"] <= 2 else 0
    f += 15 if parsed["email"] else 0
    f += 15 if parsed["phone"] else 0
    long_bullets = [b for b in bullets if len(b["text"].split()) > 35]
    f += 10 if not long_bullets else 0
    if not 250 <= wc <= 900:
        issues.append({"severity": "low", "area": "Format", "text": f"Resume has {wc} words; aim for 300-700."})
    if parsed["pages"] > 2:
        issues.append({"severity": "medium", "area": "Format", "text": f"Resume is {parsed['pages']} pages; keep it to 1-2."})
    if long_bullets:
        issues.append({"severity": "low", "area": "Format", "text": f"{len(long_bullets)} bullet(s) are over 35 words. Shorten them."})

    raw = {"keyword": kw, "impact": impact, "evidence": evidence, "portfolio": portfolio,
           "sections": structure, "format": f}
    components = {k: {"label": COMPONENTS[k][0], "weight": COMPONENTS[k][1], "score": round(v)} for k, v in raw.items()}
    overall = round(sum(raw[k] * COMPONENTS[k][1] for k in raw))
    order = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda i: order[i["severity"]])
    return {"overall": overall, "grade": grade(overall), "components": components,
            "matched": matched, "missing": missing, "issues": issues}
