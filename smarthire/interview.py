"""Interview Coach Agent: likely interview questions grounded in the candidate's own resume."""
from . import llm

QBANK = {
    "Python": ["What is the difference between a list, tuple, set and dict, and when do you use each?",
               "How do generators work and why are they memory efficient?"],
    "OOP": ["Explain encapsulation, inheritance and polymorphism with an example from your own code."],
    "FastAPI": ["How does FastAPI validate request data, and what role does Pydantic play?",
                "What is the difference between async and sync endpoints in FastAPI?"],
    "REST APIs": ["Which HTTP methods and status codes did you use, and why?"],
    "Flask": ["How is Flask different from FastAPI and Django?"],
    "Django": ["How does the Django ORM map models to tables, and what are migrations?"],
    "Machine Learning": ["How do you detect and handle overfitting?",
                         "Why do you split data into train and test sets, and what is data leakage?"],
    "Deep Learning": ["How does backpropagation work in simple words?"],
    "NLP": ["Walk me through your text preprocessing steps and why each one matters."],
    "TF-IDF": ["How is TF-IDF calculated, and why is it better than plain word counts?"],
    "Naive Bayes": ["Why is it called naive, and why does it still work well for text?"],
    "Logistic Regression": ["What does the sigmoid do, and how do you interpret the coefficients?"],
    "Model Evaluation": ["Why is accuracy misleading on imbalanced data? When do you use precision vs recall?"],
    "Cosine Similarity": ["Why cosine similarity instead of Euclidean distance for text or embeddings?"],
    "Embeddings": ["What is an embedding, and how are two embeddings compared?"],
    "FAISS": ["What is FAISS, and what is the difference between a flat index and an approximate one?"],
    "Semantic Search": ["How is semantic search different from keyword search?"],
    "Scikit-learn": ["What is a Pipeline in scikit-learn and why use it?"],
    "Pandas": ["How do you handle missing values and duplicates in pandas?"],
    "NumPy": ["Why is NumPy faster than Python lists?"],
    "Recommendation Systems": ["Content-based vs collaborative filtering: what are the trade-offs?",
                               "How would you evaluate a recommender when you have no user data?"],
    "Agentic AI": ["What is an AI agent and how is it different from a simple LLM call?",
                   "Explain planner, tools, memory and loop control in an agent."],
    "LangGraph": ["What are nodes, edges and state in LangGraph? How do you build a retry loop?"],
    "LLMs": ["What are hallucinations and how do you reduce them?"],
    "Prompt Engineering": ["How do you get reliable structured (JSON) output from an LLM?"],
    "Tool Calling": ["How does an LLM decide which tool to call, and what if the tool fails?"],
    "RAG": ["Explain the RAG pipeline: chunking, embedding, retrieval, generation."],
    "Git": ["What is the difference between merge and rebase?"],
    "SQL": ["Explain INNER JOIN vs LEFT JOIN with an example."],
    "Docker": ["What is the difference between an image and a container?"],
    "Data Structures": ["When would you use a hash map vs a list?"],
}

SYSTEM = ('You are a technical interviewer. Using ONLY the facts in the resume summary, write 6 specific interview '
          'questions about the candidate\'s own projects and claimed skills, including architecture, trade-offs and '
          'their individual contribution. Return JSON only: {"questions": [{"topic": "...", "q": "...", "why": "..."}]}')


def build_questions(parsed: dict, target: dict) -> dict:
    qs, seen = [], set()

    def add(topic, q, why, source="template"):
        if q not in seen:
            seen.add(q)
            qs.append({"topic": topic, "q": q, "why": why, "source": source})

    projects = []
    for b in parsed["bullets"]:
        if b["section"] == "projects" and b["project"] and b["project"] not in projects:
            projects.append(b["project"])
    for p in projects[:3]:
        add(p, f"Walk me through the architecture of {p}. What does each component do?", "Interviewers always ask you to explain your own project end to end.")
        add(p, f"What was YOUR individual contribution in {p}, and what would you improve?", "Checks ownership and honesty.")

    wanted = [s for s in target["weights"] if s in parsed["skills"]]
    wanted.sort(key=lambda s: (-target["weights"][s], not parsed["skills"][s]["demonstrated"]))
    for s in wanted:
        for q in QBANK.get(s, [])[:2]:
            why = f"{s} is {'a must-have' if target['weights'][s] == 3 else 'relevant'} for this role"
            add(s, q, why + (" and you listed it without a project to show it." if not parsed["skills"][s]["demonstrated"] else "."))
        if len(qs) >= 14:
            break

    if "Agentic AI" in target["weights"] and "Agentic AI" not in parsed["skills"]:
        add("Agentic AI", "Describe an agent workflow you would build to automate a task: which agents, which tools, and how they hand off work.",
            "Agentic AI is a must-have for this target and was not found on your resume.")

    mode = "templates"
    if llm.is_enabled():
        summary = {"projects": projects, "skills": sorted(parsed["skills"]),
                   "bullets": [b["text"] for b in parsed["bullets"]][:12], "target": target["title"]}
        try:
            data = llm.chat_json(SYSTEM, str(summary))
            for item in data.get("questions", [])[:6]:
                add(str(item.get("topic", "Resume")), str(item["q"]), str(item.get("why", "Based on your resume.")), "ai")
            mode = "ai + templates"
        except (llm.LLMError, KeyError, TypeError, AttributeError):
            pass
    return {"mode": mode, "questions": qs[:16]}
