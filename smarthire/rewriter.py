"""Rewriter Agent + Critic Agent.

The Rewriter drafts stronger resume bullets with an LLM. The Critic then checks every draft with
deterministic rules, including a FABRICATION GUARD: a rewrite may not introduce numbers or
technologies that are not already in the candidate's resume. Rejected drafts go back to the
Rewriter with the Critic's feedback (a retry loop, max MAX_ATTEMPTS).
Without an LLM key the Rewriter falls back to rule-based tips.
"""
from __future__ import annotations

import json
import re

from . import llm
from .parser import ACTION_VERBS, _first_word
from .scoring import bullet_quality
from .skills import taxonomy

MAX_ATTEMPTS = 3
NUM_RE = re.compile(r"\d+(?:\.\d+)?")

SYSTEM = (
    "You improve resume bullet points for a student applying for software/AI roles. Rules: "
    "1) Keep every fact from the original. 2) NEVER invent numbers, metrics, tools, datasets or results. "
    "3) Start with a strong past-tense action verb. 4) One sentence, 12-28 words. "
    "5) You may only mention technologies from the ALLOWED list. "
    "6) If the original has no measurable result, do not make one up; describe the concrete outcome instead. "
    'Return JSON only: {"rewrites": [{"id": <int>, "text": "<bullet>"}]}'
)


def _tips(issues, quality):
    tips = []
    if not quality["verb_ok"]:
        tips.append("Start with an action verb such as Built, Designed, Implemented or Deployed.")
    if not quality["has_metric"]:
        tips.append("Add a measurable result you can prove: accuracy, dataset size, latency, number of users or records.")
    if not quality["length_ok"]:
        tips.append("Keep it to one line of 12-28 words.")
    return tips


def pick_weak_bullets(parsed: dict, limit: int = 3) -> list:
    items = []
    for b in parsed["bullets"]:
        q = bullet_quality(b["text"])
        if q["score"] < 0.8:
            items.append({"original": b["text"], "project": b["project"], "issues": q["issues"],
                          "tips": _tips(q["issues"], q), "suggestion": None, "approved": False,
                          "notes": [], "attempts": 0, "_score": q["score"]})
    items.sort(key=lambda i: i["_score"])
    for it in items:
        it.pop("_score")
    return items[:limit]


def run_rewriter(parsed: dict, target: dict, prev: dict | None) -> dict:
    items = prev["items"] if prev else pick_weak_bullets(parsed)
    if not items:
        return {"mode": "none", "items": []}
    if not llm.is_enabled():
        for it in items:
            it["approved"] = True  # nothing to critique in tips mode
        return {"mode": "tips", "items": items}

    pending = [(i, it) for i, it in enumerate(items) if not it["approved"]]
    allowed = sorted(parsed["skills"])
    payload = [{"id": i, "original": it["original"], "problems": it["issues"],
                "previous_attempt": it["suggestion"], "critic_feedback": it["notes"]} for i, it in pending]
    user = f"ALLOWED technologies: {', '.join(allowed)}\nTarget role: {target['title']}\nBullets:\n{json.dumps(payload, indent=1)}"
    try:
        data = llm.chat_json(SYSTEM, user)
        rewrites = {int(r["id"]): str(r["text"]).strip() for r in data.get("rewrites", [])}
    except (llm.LLMError, KeyError, ValueError, TypeError, AttributeError) as exc:
        for it in items:
            it["approved"] = True
        return {"mode": "tips", "items": items, "llm_error": str(exc)}
    for i, it in pending:
        if i in rewrites:
            it["suggestion"] = rewrites[i]
            it["attempts"] += 1
    return {"mode": "llm", "items": items}


def critique(suggestion: str, original: str, parsed: dict) -> list:
    """Return a list of problems; empty list means the rewrite is approved."""
    notes = []
    words = suggestion.split()
    if _first_word(suggestion) not in ACTION_VERBS:
        notes.append("Must start with a strong past-tense action verb.")
    if not 8 <= len(words) <= 32:
        notes.append(f"Length is {len(words)} words; keep it between 8 and 32.")
    new_numbers = set(NUM_RE.findall(suggestion)) - set(NUM_RE.findall(parsed["text"]))
    if new_numbers:
        notes.append(f"Contains numbers that are not in the resume ({', '.join(sorted(new_numbers))}). Do not invent metrics.")
    new_skills = taxonomy().find(suggestion) - set(parsed["skills"])
    if new_skills:
        notes.append(f"Mentions technologies not in the resume ({', '.join(sorted(new_skills))}). Remove them.")
    sig = {w for w in re.findall(r"[a-z]{4,}", original.lower())}
    kept = {w for w in re.findall(r"[a-z]{4,}", suggestion.lower())}
    if sig and len(sig & kept) / len(sig) < 0.35:
        notes.append("Drifts too far from the original meaning; keep its key facts.")
    return notes


def run_critic(parsed: dict, rewrites: dict) -> dict:
    if rewrites.get("mode") != "llm":
        return rewrites
    for it in rewrites["items"]:
        if it["approved"]:
            continue
        if not it["suggestion"]:
            it["notes"] = ["No rewrite returned."]
            continue
        it["notes"] = critique(it["suggestion"], it["original"], parsed)
        it["approved"] = not it["notes"]
    return rewrites
