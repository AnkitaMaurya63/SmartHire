"""Use the trained classifier (this is what Step 4 will plug into the SmartHire backend).

    python ml/predict.py path/to/resume.txt
"""
import os
import sys
from functools import lru_cache

import joblib
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from train import clean  # noqa: E402

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "resume_classifier.joblib")


@lru_cache(maxsize=1)
def _model():
    return joblib.load(MODEL_PATH)


def predict_categories(text: str, k: int = 3) -> list:
    """Top-k predicted job categories with a softmax-style confidence (0-100)."""
    pipe = _model()
    scores = pipe.decision_function([clean(text)])[0]
    exp = np.exp(scores - scores.max())
    probs = exp / exp.sum()
    top = np.argsort(-scores)[:k]
    return [{"category": str(pipe.classes_[i]), "confidence": round(float(probs[i]) * 100, 1)} for i in top]


if __name__ == "__main__":
    print(predict_categories(open(sys.argv[1], encoding="utf-8", errors="ignore").read()))
