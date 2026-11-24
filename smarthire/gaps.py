"""Skill-Gap Agent: missing skills, priorities, learning tips and a time-boxed roadmap."""
from .skills import CATEGORY_LABELS, taxonomy

TIPS = {
    "LangGraph": "Build a 3-node graph (planner, tool-caller, reviewer) with a conditional retry edge.",
    "Agentic AI": "Build an agent that picks tools by itself, keeps state, and stops after a step limit.",
    "LLMs": "Call a hosted LLM API, handle errors and rate limits, and request structured JSON output.",
    "Tool Calling": "Give an LLM 2-3 Python functions as tools and let it decide which to call.",
    "RAG": "Chunk documents, embed them, store in FAISS, and answer questions with retrieved context.",
    "Vector Databases": "Index embeddings in FAISS or ChromaDB and run similarity search.",
    "FAISS": "Index sentence embeddings with FAISS IndexFlatIP and query top-k.",
    "Embeddings": "Embed texts with sentence-transformers and compare them with cosine similarity.",
    "Prompt Engineering": "Practise system prompts, few-shot examples and JSON-only output formats.",
    "Generative AI": "Build a small app that generates text with an LLM and evaluate output quality.",
    "LLM API Integration": "Wrap a Groq or Gemini API call in a FastAPI endpoint with retries.",
    "FastAPI": "Build a CRUD API with Pydantic models, validation and auto docs at /docs.",
    "Flask": "Build a small REST API with routes, JSON responses and error handlers.",
    "Docker": "Containerise one of your FastAPI projects with a Dockerfile and run it.",
    "Deep Learning": "Train a small neural network (e.g. LSTM or CNN) and compare it with a baseline.",
    "PyTorch": "Train a simple classifier with a Dataset, DataLoader and training loop.",
    "TensorFlow": "Train a Keras model on a small dataset and plot its learning curves.",
    "SQL": "Practise joins, GROUP BY and subqueries on a sample database.",
    "Databases": "Design 3 related tables and query them from Python.",
    "Git": "Use branches, commits and pull requests on one of your repos.",
    "Unit Testing": "Add 5 pytest tests to an existing project.",
    "Data Structures": "Solve 15 easy/medium problems on arrays, hashmaps and stacks.",
    "Algorithms": "Practise sorting, binary search and recursion problems.",
    "OOP": "Refactor a script into classes using encapsulation and inheritance.",
}


def analyse_gaps(parsed: dict, target: dict) -> dict:
    tax = taxonomy()
    found = set(parsed["skills"])
    prio = {3: "High", 2: "Medium", 1: "Low"}
    missing = []
    for skill, w in target["weights"].items():
        if skill in found:
            continue
        missing.append({"skill": skill, "category": CATEGORY_LABELS.get(tax.category(skill), "Other"),
                        "weight": w, "priority": prio[w], "hours": tax.hours(skill),
                        "tip": TIPS.get(skill, f"Build a small project using {skill} and push it to GitHub.")})
    missing.sort(key=lambda m: (-m["weight"], m["hours"]))

    buckets = [("Quick wins (up to 8 hours)", lambda h: h <= 8),
               ("This week (up to 25 hours)", lambda h: 8 < h <= 25),
               ("Deep dive (25+ hours)", lambda h: h > 25)]
    roadmap = [{"label": label, "items": [m for m in missing if cond(m["hours"])]} for label, cond in buckets]
    roadmap = [b for b in roadmap if b["items"]]

    evidence_gaps = []
    if parsed["has_evidence_sections"]:
        evidence_gaps = [{"skill": s, "tip": f"Mention {s} in a project bullet: what you built with it and the result."}
                         for s, m in parsed["skills"].items() if not m["demonstrated"]]
    return {"missing": missing, "roadmap": roadmap, "evidence_gaps": evidence_gaps,
            "must_have_hours": sum(m["hours"] for m in missing if m["weight"] == 3)}
