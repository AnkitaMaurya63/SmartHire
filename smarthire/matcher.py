"""Job Matcher Agent: embeddings + FAISS vector search over a role database, plus target resolution."""
import os
import re
from functools import lru_cache

import numpy as np

from .skills import role_by_id, roles, taxonomy


class Embedder:
    """Sentence-Transformers if installed, otherwise a TF-IDF fallback (same interface)."""

    def __init__(self, corpus):
        self.dense, self.model, self.tfidf = False, None, None
        if os.getenv("EMBEDDINGS", "auto").lower() in ("auto", "sbert"):
            try:
                from sentence_transformers import SentenceTransformer
                name = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
                self.model = SentenceTransformer(name)
                self.name, self.dense = f"Sentence-Transformers ({name.split('/')[-1]})", True
            except Exception:
                self.model = None
        if self.model is None:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit(corpus)
            self.name = "TF-IDF (fallback)"

    def encode(self, texts) -> np.ndarray:
        if self.dense:
            vecs = self.model.encode(list(texts), normalize_embeddings=True)
        else:
            vecs = self.tfidf.transform(list(texts)).toarray()
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            vecs = vecs / np.where(norms == 0, 1, norms)
        return np.ascontiguousarray(vecs, dtype="float32")


class Matcher:
    def __init__(self):
        self.roles = roles()
        docs = [self._role_doc(r) for r in self.roles]
        self.embedder = Embedder(docs)
        vecs = self.embedder.encode(docs)
        try:
            import faiss
            self.index = faiss.IndexFlatIP(vecs.shape[1])
            self.index.add(vecs)
            self.index_name = "FAISS"
        except Exception:
            self.index, self.vecs, self.index_name = None, vecs, "NumPy"

    @staticmethod
    def _role_doc(r):
        return f"{r['title']}. {r['description']} Skills: {', '.join(r['core'] + r['important'] + r['nice'])}"

    @staticmethod
    def resume_doc(parsed) -> str:
        s = parsed["sections"]
        parts = [", ".join(parsed["skills"]), s.get("summary", ""), s.get("projects", ""), s.get("experience", "")]
        return " ".join(p for p in parts if p)[:3000]

    def _scale(self, cos: float) -> float:
        lo, hi = (0.10, 0.60) if self.embedder.dense else (0.0, 0.35)
        return float(min(1.0, max(0.0, (cos - lo) / (hi - lo))))

    def similarity_to_text(self, parsed, text: str) -> int:
        a, b = self.embedder.encode([self.resume_doc(parsed), text[:3000]])
        return round(100 * self._scale(float(a @ b)))

    def rank(self, parsed, limit: int = 6) -> list:
        q = self.embedder.encode([self.resume_doc(parsed)])
        k = len(self.roles)
        if self.index is not None:
            sims, idxs = self.index.search(q, k)
            pairs = list(zip(idxs[0].tolist(), sims[0].tolist()))
        else:
            sims = (self.vecs @ q[0]).tolist()
            pairs = list(enumerate(sims))
        found = set(parsed["skills"])
        out = []
        for i, cos in pairs:
            r = self.roles[i]
            w = r["weights"]
            total = sum(w.values())
            matched = sorted((s for s in w if s in found), key=lambda s: -w[s])
            missing = sorted((s for s in w if s not in found), key=lambda s: -w[s])
            coverage = sum(w[s] for s in matched) / total
            sem = self._scale(cos)
            out.append({"id": r["id"], "title": r["title"], "category": r["category"],
                        "score": round(100 * (0.55 * coverage + 0.45 * sem)),
                        "coverage": round(100 * coverage), "semantic": round(100 * sem),
                        "matched": matched, "missing": missing})
        out.sort(key=lambda m: -m["score"])
        return out[:limit]


@lru_cache(maxsize=1)
def get_matcher() -> Matcher:
    return Matcher()


def jd_weights(jd_text: str) -> dict:
    tax = taxonomy()
    must = re.compile(r"\b(must|mandatory|required|essential|primary|strong)\b", re.I)
    weights = {}
    for line in jd_text.splitlines():
        w = 3 if must.search(line) else 2
        for s in tax.find(line):
            weights[s] = max(weights.get(s, 0), w)
    for s in list(weights):
        if tax.count(jd_text, s) >= 3:
            weights[s] = 3
    return weights


def resolve_target(role_id, jd_text, matches, parsed) -> dict:
    """Decide what the resume is scored against: pasted JD > chosen role > best-matching role."""
    jd_text = (jd_text or "").strip()
    if len(jd_text) >= 40:
        w = jd_weights(jd_text)
        if len(w) >= 3:
            sim = get_matcher().similarity_to_text(parsed, jd_text)
            return {"kind": "jd", "id": "custom-jd", "title": "Your pasted job description",
                    "weights": w, "jd_similarity": sim}
    role = role_by_id(role_id) if role_id else None
    if role:
        return {"kind": "role", "id": role["id"], "title": role["title"], "weights": role["weights"]}
    best = role_by_id(matches[0]["id"])
    return {"kind": "auto", "id": best["id"], "title": best["title"], "weights": best["weights"]}
