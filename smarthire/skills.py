"""Skills taxonomy and role database (loaded from data/*.json)."""
import json
import re
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Rough hours to become interview-ready, by skill category.
CATEGORY_HOURS = {"language": 40, "ml": 25, "dl": 40, "llm": 20, "data": 12, "backend": 18,
                  "database": 12, "devops": 15, "tool": 5, "cs": 30, "frontend": 20}

CATEGORY_LABELS = {"language": "Language", "ml": "Machine Learning", "dl": "Deep Learning",
                   "llm": "LLM / GenAI", "data": "Data", "backend": "Backend", "database": "Database",
                   "devops": "DevOps / Cloud", "tool": "Tool", "cs": "CS Fundamentals", "frontend": "Frontend"}

WEIGHTS = {"core": 3, "important": 2, "nice": 1}


class Taxonomy:
    def __init__(self):
        with open(DATA_DIR / "skills.json", encoding="utf-8") as f:
            self.skills = json.load(f)
        self._patterns = {}
        for name, meta in self.skills.items():
            terms = {name.lower(), *[a.lower() for a in meta.get("aliases", [])]}
            alt = "|".join(sorted((re.escape(t) for t in terms), key=len, reverse=True))
            self._patterns[name] = re.compile(rf"(?<![a-z0-9+#.])(?:{alt})(?![a-z0-9+#])", re.I)

    def find(self, text: str) -> set:
        """Canonical skill names mentioned in text."""
        return {name for name, pat in self._patterns.items() if pat.search(text or "")}

    def count(self, text: str, name: str) -> int:
        return len(self._patterns[name].findall(text or ""))

    def category(self, name: str) -> str:
        return self.skills.get(name, {}).get("cat", "tool")

    def hours(self, name: str) -> int:
        return CATEGORY_HOURS.get(self.category(name), 15)


@lru_cache(maxsize=1)
def taxonomy() -> Taxonomy:
    return Taxonomy()


@lru_cache(maxsize=1)
def roles() -> list:
    with open(DATA_DIR / "roles.json", encoding="utf-8") as f:
        items = json.load(f)
    for r in items:
        r["weights"] = {}
        for level, w in WEIGHTS.items():
            for s in r.get(level, []):
                r["weights"][s] = w
    return items


def role_by_id(role_id: str):
    return next((r for r in roles() if r["id"] == role_id), None)
