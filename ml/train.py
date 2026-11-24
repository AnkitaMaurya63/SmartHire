"""STEP 1: train a resume -> job-category classifier on a real labelled dataset.

Usage:
    python ml/train.py --data data/resumes.csv

The CSV needs a text column (Resume / Resume_str) and a label column (Category).
Both Kaggle "Resume Dataset" variants work; columns are detected automatically.

Honest evaluation: duplicate resumes are removed BEFORE splitting (these datasets contain many
copies, and copies in both train and test inflate accuracy), and we report top-1, top-3 and
macro-F1 plus 5-fold cross-validation.
"""
import argparse
import json
import os
import re

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

TEXT_COLS = ["Resume_str", "Resume", "resume", "Text", "text"]
LABEL_COLS = ["Category", "category", "Label", "label"]
RANDOM_STATE = 42


def clean(text: str) -> str:
    text = re.sub(r"http\S+|\S+@\S+", " ", str(text).lower())
    text = re.sub(r"[^a-z0-9+#.\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load(path: str, min_per_class: int) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="latin-1")
    text_col = next((c for c in TEXT_COLS if c in df.columns), None)
    label_col = next((c for c in LABEL_COLS if c in df.columns), None)
    if not text_col or not label_col:
        raise SystemExit(f"Could not find text/label columns. Found: {list(df.columns)}")
    df = df[[text_col, label_col]].dropna()
    df.columns = ["text", "label"]
    df["label"] = df["label"].astype(str).str.strip()
    n0 = len(df)
    df["clean"] = df["text"].map(clean)
    df = df.drop_duplicates(subset="clean")
    print(f"Loaded {n0} resumes, {len(df)} after removing duplicates ({n0 - len(df)} copies dropped)")
    counts = df["label"].value_counts()
    keep = counts[counts >= min_per_class].index
    dropped = sorted(set(counts.index) - set(keep))
    if dropped:
        print(f"Dropped tiny classes (<{min_per_class} resumes): {dropped}")
    df = df[df["label"].isin(keep)].reset_index(drop=True)
    print(f"{df['label'].nunique()} classes, {len(df)} resumes\n")
    return df


def make_pipeline(model) -> Pipeline:
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.9, sublinear_tf=True,
                          stop_words="english", max_features=60000)
    return Pipeline([("tfidf", vec), ("clf", model)])


def top_k_accuracy(pipe, X, y, k=3) -> float:
    scores = pipe.decision_function(X)
    top = np.argsort(-scores, axis=1)[:, :k]
    classes = pipe.classes_
    return float(np.mean([yi in classes[row] for yi, row in zip(y, top)]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--min-per-class", type=int, default=10)
    ap.add_argument("--out", default="models")
    args = ap.parse_args()

    df = load(args.data, args.min_per_class)
    X_tr, X_te, y_tr, y_te = train_test_split(df["clean"], df["label"], test_size=0.2,
                                              stratify=df["label"], random_state=RANDOM_STATE)
    candidates = {
        "TF-IDF + Logistic Regression": LogisticRegression(max_iter=3000, C=10, class_weight="balanced"),
        "TF-IDF + Linear SVM": LinearSVC(C=1.0, class_weight="balanced"),
    }
    folds = max(2, min(5, int(df["label"].value_counts().min())))
    cv = StratifiedKFold(folds, shuffle=True, random_state=RANDOM_STATE)

    results, fitted = {}, {}
    for name, model in candidates.items():
        pipe = make_pipeline(model).fit(X_tr, y_tr)
        pred = pipe.predict(X_te)
        cv_scores = cross_val_score(make_pipeline(model), df["clean"], df["label"], cv=cv, scoring="accuracy")
        results[name] = {
            "accuracy": round(accuracy_score(y_te, pred), 4),
            "top3_accuracy": round(top_k_accuracy(pipe, X_te, y_te.values, 3), 4),
            "macro_f1": round(f1_score(y_te, pred, average="macro"), 4),
            f"cv{folds}_accuracy_mean": round(float(cv_scores.mean()), 4),
            f"cv{folds}_accuracy_std": round(float(cv_scores.std()), 4),
        }
        fitted[name] = (pipe, pred)
        print(f"=== {name} ===")
        print(json.dumps(results[name], indent=2), "\n")

    best = max(results, key=lambda n: results[n]["macro_f1"])
    pipe, pred = fitted[best]
    print(f"Best model by macro-F1: {best}\n")
    print(classification_report(y_te, pred, zero_division=0))

    os.makedirs(args.out, exist_ok=True)
    os.makedirs("results", exist_ok=True)
    joblib.dump(pipe, os.path.join(args.out, "resume_classifier.joblib"))
    labels = list(pipe.classes_)
    pd.DataFrame(confusion_matrix(y_te, pred, labels=labels), index=labels, columns=labels) \
        .to_csv("results/classifier_confusion_matrix.csv")
    with open("results/classifier_metrics.json", "w") as f:
        json.dump({"best_model": best, "train_size": len(X_tr), "test_size": len(X_te),
                   "classes": labels, "results": results}, f, indent=2)
    print("Saved models/resume_classifier.joblib, results/classifier_metrics.json, "
          "results/classifier_confusion_matrix.csv")


if __name__ == "__main__":
    main()
