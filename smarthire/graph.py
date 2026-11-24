"""LangGraph workflow that wires the agents together.

    parser -> matcher -> target -> +-> scorer ----+
                                   +-> gap_agent -+-> rewriter -> critic --(retry)--> rewriter
                                   +-> interview -+                  |
                                   +-> classifier +
                                                                 (done) -> reporter

scorer, gap_agent, interview and the ML classifier run in PARALLEL; the rewriter waits for all three. The critic can send
rejected rewrites back to the rewriter (conditional edge) up to MAX_ATTEMPTS times.
"""
import operator
import time
import traceback
from functools import lru_cache
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph

from . import classifier, llm
from .gaps import analyse_gaps
from .interview import build_questions
from .matcher import get_matcher, resolve_target
from .parser import parse_resume
from .rewriter import MAX_ATTEMPTS, run_critic, run_rewriter
from .scoring import score_resume


class State(TypedDict, total=False):
    file_bytes: bytes
    filename: str
    role_id: str
    jd_text: str
    parsed: dict
    matches: list
    target: dict
    score: dict
    gaps: dict
    interview: dict
    ml: dict
    rewrites: dict
    rewrite_attempts: int
    report: dict
    trace: Annotated[list, operator.add]


AGENTS = {
    "parser_agent": "Parser",
    "matcher_agent": "Job Matcher",
    "target_agent": "Target Resolver",
    "scorer_agent": "ATS Scorer",
    "gap_agent": "Skill-Gap Analyst",
    "interview_agent": "Interview Coach",
    "classifier_agent": "ML Classifier",
    "rewriter_agent": "Rewriter",
    "critic_agent": "Critic",
    "reporter_agent": "Reporter",
}


def agent(node_id, critical=False):
    """Time a node, record a trace entry, and (for non-critical agents) survive failures."""
    def deco(fn):
        def wrapper(state):
            t0 = time.perf_counter()
            try:
                out, summary, tools = fn(state)
                status = "done"
            except Exception as exc:
                if critical:
                    raise
                traceback.print_exc()
                out, summary, tools, status = {}, f"Failed: {exc}", [], "failed"
            out["trace"] = [{"agent": node_id, "label": AGENTS[node_id], "status": status,
                             "ms": round((time.perf_counter() - t0) * 1000), "summary": summary, "tools": tools}]
            return out
        wrapper.__name__ = node_id
        return wrapper
    return deco


@agent("parser_agent", critical=True)
def parser_agent(state):
    parsed = parse_resume(state["file_bytes"], state["filename"])
    return ({"parsed": parsed},
            f"{len(parsed['skills'])} skills, {len(parsed['bullets'])} bullets, {len(parsed['section_names'])} sections found",
            ["pypdf", "section splitter", "skills taxonomy"])


@agent("matcher_agent", critical=True)
def matcher_agent(state):
    m = get_matcher()
    matches = m.rank(state["parsed"])
    return ({"matches": matches}, f"Best fit: {matches[0]['title']} ({matches[0]['score']}%)",
            [m.index_name, m.embedder.name])


@agent("target_agent", critical=True)
def target_agent(state):
    target = resolve_target(state.get("role_id"), state.get("jd_text"), state["matches"], state["parsed"])
    return ({"target": target}, f"Scoring against: {target['title']} ({len(target['weights'])} skills)", ["role database", "JD keyword extractor"])


@agent("scorer_agent")
def scorer_agent(state):
    score = score_resume(state["parsed"], state["target"])
    return {"score": score}, f"Overall {score['overall']}/100 ({score['grade']}), {len(score['issues'])} issues", ["6-component ATS rubric"]


@agent("gap_agent")
def gap_agent(state):
    gaps = analyse_gaps(state["parsed"], state["target"])
    return {"gaps": gaps}, f"{len(gaps['missing'])} missing skills, {len(gaps['evidence_gaps'])} unproven skills", ["skill taxonomy", "learning-tip library"]


@agent("interview_agent")
def interview_agent(state):
    iv = build_questions(state["parsed"], state["target"])
    return {"interview": iv}, f"{len(iv['questions'])} questions ({iv['mode']})", ["question bank"] + (["LLM"] if "ai" in iv["mode"] else [])


@agent("classifier_agent")
def classifier_agent(state):
    if not classifier.is_available():
        return ({"ml": {"available": False, "predictions": []}},
                "No trained model found (run ml/train.py), skipped", [])
    preds = classifier.predict(state["parsed"]["text"], k=3)
    return ({"ml": {"available": True, "predictions": preds}},
            f"Predicted: {preds[0]['category']} ({preds[0]['confidence']}%)", ["TF-IDF + linear model"])


@agent("rewriter_agent")
def rewriter_agent(state):
    attempt = state.get("rewrite_attempts", 0) + 1
    rewrites = run_rewriter(state["parsed"], state["target"], state.get("rewrites"))
    if rewrites["mode"] == "llm":
        pending = sum(1 for i in rewrites["items"] if not i["approved"])
        summary, tools = f"Attempt {attempt}: drafting {pending} bullet(s)", [llm.info()["provider"] + " LLM"]
    elif rewrites["mode"] == "tips":
        reason = " (LLM error, using tips)" if rewrites.get("llm_error") else " (no LLM key, rule-based tips)"
        summary, tools = f"{len(rewrites['items'])} weak bullet(s) found{reason}", ["bullet quality rules"]
    else:
        summary, tools = "All bullets already strong", []
    return {"rewrites": rewrites, "rewrite_attempts": attempt}, summary, tools


@agent("critic_agent")
def critic_agent(state):
    rewrites = run_critic(state["parsed"], state["rewrites"])
    items = rewrites["items"]
    ok = sum(1 for i in items if i["approved"])
    if rewrites["mode"] != "llm":
        return {"rewrites": rewrites}, "Nothing to verify (no AI rewrites)", []
    return {"rewrites": rewrites}, f"{ok}/{len(items)} rewrites approved", ["fabrication guard", "verb/length/meaning checks"]


def route_after_critic(state):
    items = state["rewrites"]["items"]
    if any(not i["approved"] for i in items) and state["rewrite_attempts"] < MAX_ATTEMPTS:
        return "retry"
    return "done"


@agent("reporter_agent")
def reporter_agent(state):
    p, t, sc = state["parsed"], state["target"], state.get("score") or {}
    gaps, iv = state.get("gaps") or {}, state.get("interview") or {}
    ml = state.get("ml") or {"available": False, "predictions": []}
    name = p["name"]
    strengths = sc.get("matched", [])[:4]
    missing = [m["skill"] for m in gaps.get("missing", [])][:3]
    summary = (f"{name}'s resume scores {sc.get('overall', 0)}/100 for {t['title']}. "
               f"Strongest matches: {', '.join(strengths) or 'none yet'}. "
               f"Biggest gaps: {', '.join(missing) or 'none'}. "
               f"Top fix: {sc['issues'][0]['text'] if sc.get('issues') else 'nothing critical'}")
    mode = "template"
    if llm.is_enabled():
        try:
            summary = llm.chat(
                "You are a recruiter. Write a 3-sentence honest verdict on this candidate for the target role. "
                "Use only the facts given. Mention one strength, the biggest gap and one concrete next step.",
                f"Target: {t['title']}\nScore: {sc.get('overall')}/100\nMatched: {sc.get('matched')}\n"
                f"Missing: {sc.get('missing')}\nIssues: {[i['text'] for i in sc.get('issues', [])[:4]]}",
                temperature=0.4, max_tokens=300).strip()
            mode = "ai"
        except llm.LLMError:
            pass
    skills = [{"name": s, "cat": m["cat"], "demonstrated": m["demonstrated"], "sections": m["sections"]}
              for s, m in p["skills"].items()]
    report = {
        "candidate": {"name": name, "email": p["email"], "phone": p["phone"], "pages": p["pages"], "words": p["words"],
                      "links": p["links"], "education": p["education"], "project_count": p["project_count"]},
        "target": {k: v for k, v in t.items() if k != "weights"} | {"skills": t["weights"]},
        "score": sc, "matches": state["matches"], "skills": skills, "gaps": gaps,
        "rewrites": state.get("rewrites") or {"mode": "none", "items": []},
        "interview": iv, "ml": ml, "summary": summary,
        "meta": {"summary_mode": mode, "llm": llm.info(), "embeddings": get_matcher().embedder.name,
                 "index": get_matcher().index_name, "rewrite_attempts": state.get("rewrite_attempts", 0)},
    }
    return {"report": report}, "Report assembled", []


@lru_cache(maxsize=1)
def get_graph():
    g = StateGraph(State)
    for node_id, fn in [("parser_agent", parser_agent), ("matcher_agent", matcher_agent), ("target_agent", target_agent),
                        ("scorer_agent", scorer_agent), ("gap_agent", gap_agent), ("interview_agent", interview_agent), ("classifier_agent", classifier_agent),
                        ("rewriter_agent", rewriter_agent), ("critic_agent", critic_agent), ("reporter_agent", reporter_agent)]:
        g.add_node(node_id, fn)
    g.set_entry_point("parser_agent")
    g.add_edge("parser_agent", "matcher_agent")
    g.add_edge("matcher_agent", "target_agent")
    for n in ("scorer_agent", "gap_agent", "interview_agent", "classifier_agent"):
        g.add_edge("target_agent", n)
    g.add_edge(["scorer_agent", "gap_agent", "interview_agent", "classifier_agent"], "rewriter_agent")
    g.add_edge("rewriter_agent", "critic_agent")
    g.add_conditional_edges("critic_agent", route_after_critic, {"retry": "rewriter_agent", "done": "reporter_agent"})
    g.add_edge("reporter_agent", END)
    return g.compile()


def stream_analysis(file_bytes: bytes, filename: str, role_id: str = "", jd_text: str = ""):
    """Yield events: {'type': 'agent', ...} as each agent finishes, then {'type': 'result'} or {'type': 'error'}."""
    t0 = time.perf_counter()
    init = {"file_bytes": file_bytes, "filename": filename, "role_id": role_id or "", "jd_text": jd_text or "",
            "rewrite_attempts": 0, "trace": []}
    acc = {"trace": []}
    try:
        for update in get_graph().stream(init, stream_mode="updates"):
            for node, out in update.items():
                if not out:
                    continue
                for k, v in out.items():
                    if k == "trace":
                        acc["trace"].extend(v)
                    else:
                        acc[k] = v
                yield {"type": "agent", "agent": node, "entry": (out.get("trace") or [None])[0]}
    except ValueError as exc:
        yield {"type": "error", "message": str(exc)}
        return
    except Exception as exc:  # unexpected
        traceback.print_exc()
        yield {"type": "error", "message": f"Analysis failed: {exc}"}
        return
    report = acc.get("report")
    if not report:
        yield {"type": "error", "message": "Analysis did not complete."}
        return
    report["trace"] = acc["trace"]
    report["meta"]["elapsed_ms"] = round((time.perf_counter() - t0) * 1000)
    yield {"type": "result", "report": report}


def analyze(file_bytes: bytes, filename: str, role_id: str = "", jd_text: str = "") -> dict:
    """Blocking helper (used by tests): returns the final report or raises ValueError."""
    for ev in stream_analysis(file_bytes, filename, role_id, jd_text):
        if ev["type"] == "error":
            raise ValueError(ev["message"])
        if ev["type"] == "result":
            return ev["report"]
    raise ValueError("No result")
