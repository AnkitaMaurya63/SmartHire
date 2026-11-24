"""Trained resume -> job-category classifier (made by `python ml/train.py`).

The model file is optional: if it has not been trained yet, SmartHire still works and the
ML agent reports that no model is available. The model card (metrics) comes from the JSON
that train.py writes, so the UI only ever shows numbers from a real training run.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "resume_classifier.joblib"
METRICS_PATH = ROOT / "results" / "classifier_metrics.json"


def clean(text: str) -> str:
    """Must stay identical to clean() in ml/train.py, otherwise predictions drift from training."""
    text = re.sub(r"http\S+|\S+@\S+", " ", str(text).lower())
    text = re.sub(r"[^a-z0-9+#.\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=1)
def _model():
    if not MODEL_PATH.exists():
        return None
    import joblib
    return joblib.load(MODEL_PATH)


def is_available() -> bool:
    return _model() is not None


def predict(text: str, k: int = 3) -> list:
    """Top-k categories with a softmax-style confidence (0-100). Empty list if no model."""
    pipe = _model()
    if pipe is None:
        return []
    scores = pipe.decision_function([clean(text)])[0]
    exp = np.exp(scores - scores.max())
    probs = exp / exp.sum()
    top = np.argsort(-scores)[:k]
    return [{"category": str(pipe.classes_[i]), "confidence": round(float(probs[i]) * 100, 1)} for i in top]


def model_card() -> dict:
    """Metrics from the real training run, or {'available': False}."""
    if not METRICS_PATH.exists():
        return {"available": False}
    try:
        m = json.loads(METRICS_PATH.read_text())
    except (OSError, ValueError):
        return {"available": False}
    best = m.get("results", {}).get(m.get("best_model"), {})
    return {"available": True, "best_model": m.get("best_model"), "train_size": m.get("train_size"),
            "test_size": m.get("test_size"), "classes": m.get("classes", []), "metrics": best,
            "all_models": m.get("results", {}),
            "notes": ["Duplicate resumes are removed before the train/test split.",
                      "Small public dataset: treat the numbers as indicative, not as production accuracy.",
                      "Categories come from the dataset and differ from the 18 target roles."]}


def ablation():
    """Results of ml/ablation.py (matcher comparison), or None if it has not been run."""
    path = ROOT / "results" / "ablation.json"
    try:
        return json.loads(path.read_text()) if path.exists() else None
    except (OSError, ValueError):
        return None
