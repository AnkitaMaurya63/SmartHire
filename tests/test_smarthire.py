import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smarthire import graph, llm  # noqa: E402
from smarthire.parser import parse_resume  # noqa: E402
from smarthire.rewriter import critique  # noqa: E402
from smarthire.scoring import bullet_quality, score_resume  # noqa: E402
from smarthire.skills import roles, taxonomy  # noqa: E402

SAMPLE = """Rahul Verma
+91-9876543210 | rahul.verma@example.com | github.com/rahulverma
CAREER OBJECTIVE
B.Tech CSE student interested in machine learning and backend development.
TECHNICAL SKILLS
Languages: Python, C++
AI / ML: Machine Learning, scikit-learn, NumPy, Pandas, Deep Learning
Backend: FastAPI, REST APIs, Git
PROJECTS
House Price Predictor | github.com/rahulverma/house-price | Python, scikit-learn
• Built a regression model on 20,000 housing records reaching 0.87 R2 score.
• Created a FastAPI service that returns predictions for new inputs.
Chat Helper | Python
• Worked on a chatbot for the college.
EDUCATION
B.Tech Computer Science | ABC University | 2023 - 2027 | CGPA 8.4
"""


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    monkeypatch.setattr(llm, "is_enabled", lambda: False)
    monkeypatch.setattr(llm, "info", lambda: None)


def test_skill_matching_edge_cases():
    found = taxonomy().find("Used FastAPI, scikit-learn, C++ and Node.js; also sklearn. Not 'pythonic'.")
    assert {"FastAPI", "Scikit-learn", "C++", "Node.js"} <= found
    assert "Python" not in found  # 'pythonic' must not match


def test_all_role_skills_exist_in_taxonomy():
    tax = taxonomy()
    for r in roles():
        for s in r["weights"]:
            assert s in tax.skills, (r["id"], s)


def test_parser_extracts_structure():
    p = parse_resume(SAMPLE.encode(), "resume.txt")
    assert p["name"] == "Rahul Verma"
    assert p["email"] == "rahul.verma@example.com"
    assert {"skills", "projects", "education"} <= set(p["section_names"])
    assert len(p["bullets"]) == 3
    assert p["links"]["github_profile"] == "github.com/rahulverma"
    assert "github.com/rahulverma/house-price" in p["links"]["repos"]
    assert p["skills"]["Python"]["demonstrated"] is True
    assert p["skills"]["Deep Learning"]["demonstrated"] is False  # listed but never used


def test_bullet_quality():
    assert bullet_quality("Built a regression model on 20,000 records reaching 0.87 R2 score.")["score"] == 1.0
    weak = bullet_quality("Worked on a chatbot.")
    assert not weak["verb_ok"] and not weak["has_metric"]


def test_score_is_bounded_and_flags_gaps():
    p = parse_resume(SAMPLE.encode(), "resume.txt")
    target = {"weights": {"Python": 3, "Agentic AI": 3, "FastAPI": 2}}
    s = score_resume(p, target)
    assert 0 <= s["overall"] <= 100
    assert "Agentic AI" in s["missing"]
    assert any("must-have" in i["text"] for i in s["issues"])


def test_critic_fabrication_guard():
    p = parse_resume(SAMPLE.encode(), "resume.txt")
    original = "Created a FastAPI service that returns predictions for new inputs."
    bad = "Created a Kubernetes service that improved latency by 73% for 5000 users."
    notes = " ".join(critique(bad, original, p))
    assert "not in the resume" in notes
    good = "Created a FastAPI service that returns predictions for new inputs reliably."
    assert critique(good, original, p) == []


def test_full_pipeline_without_llm():
    report = graph.analyze(SAMPLE.encode(), "resume.txt", role_id="python-backend")
    assert report["target"]["id"] == "python-backend"
    assert 0 <= report["score"]["overall"] <= 100
    assert report["rewrites"]["mode"] == "tips"
    assert report["interview"]["questions"]
    agents = [t["agent"] for t in report["trace"]]
    assert agents[0] == "parser_agent" and agents[-1] == "reporter_agent"


def test_retry_loop_with_llm(monkeypatch):
    attempts = {"n": 0}

    def fake_json(system, user, **kw):
        if "interviewer" in system:
            return {"questions": []}
        attempts["n"] += 1
        text = ("Built a chatbot for the college with 9999 users" if attempts["n"] == 1
                else "Worked on a chatbot for the college")
        import re
        ids = [int(i) for i in re.findall(r'"id": (\d+)', user)]
        if attempts["n"] >= 2:
            text = "Built a chatbot for the college using Python"
        return {"rewrites": [{"id": i, "text": text} for i in ids]}

    monkeypatch.setattr(llm, "is_enabled", lambda: True)
    monkeypatch.setattr(llm, "info", lambda: {"provider": "mock", "model": "mock"})
    monkeypatch.setattr(llm, "chat_json", fake_json)
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "Verdict.")
    report = graph.analyze(SAMPLE.encode(), "resume.txt")
    assert report["meta"]["rewrite_attempts"] >= 2  # first draft was rejected, so the loop ran again
    assert any(i["approved"] for i in report["rewrites"]["items"])


def test_bad_file_gives_friendly_error():
    with pytest.raises(ValueError):
        graph.analyze(b"x" * 10, "resume.docx")


def test_classifier_agent_skips_without_model(monkeypatch, tmp_path):
    from smarthire import classifier
    monkeypatch.setattr(classifier, "MODEL_PATH", tmp_path / "missing.joblib")
    monkeypatch.setattr(classifier, "METRICS_PATH", tmp_path / "missing.json")
    classifier._model.cache_clear()
    report = graph.analyze(SAMPLE.encode(), "resume.txt", role_id="python-backend")
    assert report["ml"] == {"available": False, "predictions": []}
    assert classifier.model_card() == {"available": False}
    classifier._model.cache_clear()
