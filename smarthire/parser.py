"""Parser Agent tools: read PDF/TXT, split sections, extract contact, links, skills and bullets."""
import io
import re

from pypdf import PdfReader

from .skills import taxonomy

HEADINGS = {
    "summary": r"(career\s+objective|objective|professional\s+summary|summary|profile|about\s+me)",
    "skills": r"(technical\s+skills|skills|technologies|tech\s+stack|core\s+competencies)",
    "projects": r"(academic\s+projects|personal\s+projects|projects?)",
    "experience": r"(work\s+experience|professional\s+experience|experience|internships?|employment)",
    "education": r"(education|academics?|qualifications?)",
    "certifications": r"(certifications?|courses?|licen[cs]es?)",
    "achievements": r"(achievements?|awards?|honou?rs?|extra[-\s]?curricular(\s+activities)?|positions?\s+of\s+responsibility)",
}
_HEAD_RES = {k: re.compile(rf"^{v}\s*:?$", re.I) for k, v in HEADINGS.items()}

BULLETS = "•●▪■◦∙·–—-*►➢\uf0b7\uf0a7\uf0d8"

ACTION_VERBS = set("""
built developed designed implemented created engineered deployed optimized optimised automated integrated led
analyzed analysed trained evaluated achieved improved reduced increased architected delivered launched migrated
refactored applied served constructed established managed collaborated conducted performed produced researched
resolved streamlined enhanced utilized utilised orchestrated configured wrote authored containerized containerised
benchmarked compared extracted generated validated tested debugged exposed leveraged spearheaded mentored organized
organised presented reached secured scaled simplified tuned visualized visualised processed parsed modeled modelled
monitored maintained executed formulated devised crafted shipped drove programmed prototyped identified detected
classified predicted recommended clustered indexed deployed fine-tuned
""".split())

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)|\+\d[\d\s-]{8,14}\d")
URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"')]+|(?:github|linkedin)\.com/[^\s<>\"')]+", re.I)


def read_document(data: bytes, filename: str):
    """Return (text, annotation_links, page_count)."""
    name = (filename or "").lower()
    links, pages = [], 1
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(data))
            pages = len(reader.pages)
            parts = []
            for p in reader.pages:
                parts.append(p.extract_text() or "")
                for a in (p.get("/Annots") or []):
                    try:
                        uri = a.get_object().get("/A", {}).get("/URI")
                        if uri:
                            links.append(str(uri))
                    except Exception:
                        pass
            text = "\n".join(parts)
        except Exception as exc:
            raise ValueError("This file is not a readable PDF.") from exc
    elif name.endswith((".txt", ".md")):
        text = data.decode("utf-8", "ignore")
    else:
        raise ValueError("Please upload a PDF (or .txt) resume.")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "•", text)  # some PDFs encode bullets as control chars
    if len(text.strip()) < 80:
        raise ValueError("Could not read text from this file. If it is a scanned image, export a text-based PDF.")
    return text, links, pages


def _heading(line: str):
    if len(line) > 40 or len(line.split()) > 4:
        return None
    for key, rx in _HEAD_RES.items():
        if rx.match(line.strip()):
            return key
    return None


def split_sections(text: str) -> dict:
    sections, current = {"header": []}, "header"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        key = _heading(line)
        if key:
            current = key
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {k: "\n".join(v) for k, v in sections.items() if v}


_SENT_END = re.compile(r"[.!?]\)?$")


def _first_word(line: str) -> str:
    words = line.split()
    return re.sub(r"[^a-z\-]", "", words[0].lower()) if words else ""


def extract_bullets(sections: dict) -> list:
    """Group wrapped PDF lines into bullets, remembering which project/job each belongs to."""
    out = []
    for sec in ("projects", "experience"):
        project, cur, pending = None, None, False

        def flush():
            nonlocal cur
            if cur:
                out.append(cur)
            cur = None

        for line in sections.get(sec, "").splitlines():
            if len(line) <= 2 and line and all(c in BULLETS for c in line):
                flush()
                pending = True  # a lone bullet glyph: the next line is the bullet text
                continue
            words = line.split()
            first = _first_word(line)
            marker = pending or (line[:1] in BULLETS and len(line) > 1)
            starts_verb = first in ACTION_VERBS and words[0][:1].isupper()
            if marker:
                flush()
                cur = {"section": sec, "project": project, "text": (line if pending else line[1:]).strip()}
                pending = False
            elif cur and "|" not in line and starts_verb and len(cur["text"].split()) >= 8:
                flush()
                cur = {"section": sec, "project": project, "text": line}
            elif cur and "|" not in line and not _SENT_END.search(cur["text"]):
                cur["text"] += " " + line
            elif "|" in line or (len(words) <= 10 and not _SENT_END.search(line) and first not in ACTION_VERBS):
                flush()
                project = re.split(r"\s*\|\s*", line)[0].strip()
            elif first in ACTION_VERBS or len(words) >= 6:
                flush()
                cur = {"section": sec, "project": project, "text": line}
            else:
                flush()
        flush()
    return out


def analyse_links(text: str, annotations: list) -> dict:
    urls = {u.rstrip(".,;:)") for u in URL_RE.findall(text)} | set(annotations)
    profile, repos, linkedin, other = None, set(), None, []
    for u in urls:
        m = re.search(r"github\.com/([\w.-]+)(?:/([\w.-]+))?", u, re.I)
        if m:
            user, repo = m.group(1), m.group(2)
            if repo:
                repos.add(f"github.com/{user}/{repo}")
                profile = profile or f"github.com/{user}"
            else:
                profile = f"github.com/{user}"
            continue
        if "linkedin.com" in u.lower():
            linkedin = u
        elif not u.lower().startswith("mailto:"):
            other.append(u)
    return {"github_profile": profile, "repos": sorted(repos), "linkedin": linkedin, "other": other}


def parse_resume(data: bytes, filename: str) -> dict:
    text, annots, pages = read_document(data, filename)
    sections = split_sections(text)
    tax = taxonomy()

    by_section = {sec: tax.find(body) for sec, body in sections.items()}
    all_found = set().union(*by_section.values()) if by_section else set()
    skills = {}
    for s in sorted(all_found):
        secs = [sec for sec, found in by_section.items() if s in found]
        skills[s] = {"cat": tax.category(s), "sections": secs,
                     "demonstrated": any(sec in ("projects", "experience") for sec in secs)}

    bullets = extract_bullets(sections)
    header_lines = sections.get("header", "").splitlines()
    name = next((l for l in header_lines if "@" not in l and sum(c.isdigit() for c in l) < 4), "Candidate")
    edu = sections.get("education", "")
    percents = re.findall(r"(\d{1,3}(?:\.\d+)?)\s*%", edu)
    cgpa = re.findall(r"cgpa[:\s]*([\d.]+)", edu, re.I)
    email = EMAIL_RE.search(text)
    phone = PHONE_RE.search(text)

    return {
        "name": name.strip()[:60],
        "email": email.group(0) if email else None,
        "phone": phone.group(0).strip() if phone else None,
        "links": analyse_links(text, annots),
        "mentions_github": "github" in text.lower(),
        "pages": pages,
        "words": len(text.split()),
        "sections": sections,
        "section_names": [k for k in sections if k != "header"],
        "skills": skills,
        "has_evidence_sections": any(k in sections for k in ("projects", "experience")),
        "bullets": bullets,
        "project_count": len({b["project"] for b in bullets if b["section"] == "projects" and b["project"]}),
        "education": {"percentages": percents, "cgpa": cgpa},
        "text": text[:30000],
    }
