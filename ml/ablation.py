"""Ablation: does hybrid role matching beat keywords-only or embeddings-only?

    python ml/ablation.py --data data/resumes.csv

Uses the same labelled resumes as train.py. Each tech category is mapped to the SmartHire roles that
are reasonable answers for it (see CATEGORY_TO_ROLES, a human judgement, edit it if you disagree).
For every unique resume we rank the 18 roles three ways and check whether a correct role is in the top 1 / top 3:

    keywords : weighted skill coverage only
    semantic : embedding similarity only
    hybrid   : 0.55 * coverage + 0.45 * semantic (what SmartHire uses)

A random ranking is reported as the baseline. Copies of the same resume are removed first.
Ties (common for keywords-only) are broken by role order, which is arbitrary but identical for every method.
"""
import argparse
import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from smarthire.matcher import get_matcher  # noqa: E402
from smarthire.parser import parse_resume  # noqa: E402

CATEGORY_TO_ROLES = {
    "Data Science": {"data-scientist", "ml-engineer", "nlp-engineer", "cv-engineer"},
    "Java Developer": {"java-developer", "sde"},
    "Python Developer": {"python-backend", "django-developer", "sde"},
    "DevOps Engineer": {"devops", "cloud-engineer", "mlops"},
    "Web Designing": {"frontend-react", "fullstack"},
    "Hadoop": {"data-engineer"},
    "ETL Developer": {"data-engineer"},
}


def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#.\s]", " ", str(t).lower())).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="results/ablation.json")
    args = ap.parse_args()

    df = pd.read_csv(args.data, encoding="latin-1")
    tcol = next(c for c in ("Resume_str", "Resume", "resume", "Text") if c in df.columns)
    lcol = next(c for c in ("Category", "category", "Label") if c in df.columns)
    df = df[[tcol, lcol]].dropna()
    df.columns = ["text", "label"]
    df["label"] = df["label"].str.strip()
    df["key"] = df["text"].map(norm)
    n0 = len(df)
    df = df.drop_duplicates("key")
    df = df[df["label"].isin(CATEGORY_TO_ROLES)]
    print(f"{n0} resumes -> {len(df)} unique resumes in {df['label'].nunique()} mapped categories")
    print(df["label"].value_counts().to_string(), "\n")

    m = get_matcher()
    print(f"Embeddings: {m.embedder.name} | index: {m.index_name}\n")
    methods = {"keywords only": "coverage", "embeddings only": "semantic", "hybrid (SmartHire)": "score"}
    hits = {k: {1: 0, 3: 0} for k in methods}
    rand = {1: 0.0, 3: 0.0}
    n_roles, used = len(m.roles), 0
    for text, label in zip(df["text"], df["label"]):
        try:
            parsed = parse_resume(str(text).encode("utf-8", "ignore"), "resume.txt")
        except ValueError:
            continue
        ranked = m.rank(parsed, limit=n_roles)
        good = CATEGORY_TO_ROLES[label]
        used += 1
        for name, key in methods.items():
            order = [r["id"] for r in sorted(ranked, key=lambda r: -r[key])]
            for k in (1, 3):
                hits[name][k] += any(x in good for x in order[:k])
        for k in (1, 3):
            rand[k] += 1 - np.prod([(n_roles - len(good) - i) / (n_roles - i) for i in range(k)])

    rows = {name: {"top1": round(h[1] / used, 3), "top3": round(h[3] / used, 3)} for name, h in hits.items()}
    rows["random baseline"] = {"top1": round(rand[1] / used, 3), "top3": round(rand[3] / used, 3)}
    print(f"Evaluated on {used} resumes\n")
    print(f"{'method':<22}{'top-1':>8}{'top-3':>8}")
    for name, r in rows.items():
        print(f"{name:<22}{r['top1']:>8.1%}{r['top3']:>8.1%}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump({"resumes": used, "embeddings": m.embedder.name, "index": m.index_name,
                   "mapping": {k: sorted(v) for k, v in CATEGORY_TO_ROLES.items()}, "results": rows}, f, indent=2)
    print(f"\nSaved {args.out}")


if __name__ == "__main__":
    main()
