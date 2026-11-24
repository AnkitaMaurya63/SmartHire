# SmartHire: Multi-Agent Resume Intelligence

SmartHire reads a resume (PDF or TXT) and runs it through a **LangGraph workflow of ten cooperating agents**. It parses the resume, matches it to job roles with **vector search (embeddings + FAISS)**, scores it like an ATS, finds skill gaps, rewrites weak bullets with an **LLM plus a fabrication-checking critic**, and prepares interview questions from the candidate's own projects. Results stream live into a web UI served by **FastAPI**.

![SmartHire dashboard](docs/screenshot.png)

## What makes it different
| Feature | What it does |
|---|---|
| **Agent workflow with parallelism and a retry loop** | Scorer, Gap Analyst, Interview Coach and the ML Classifier run in parallel. The Critic can send rejected rewrites back to the Rewriter (conditional edge, max 3 attempts). |
| **Fabrication guard** | A rewritten bullet is rejected if it adds numbers or technologies that are not already in the resume. The tool never invents achievements. |
| **Skill-evidence check** | Separates skills that are *proven* (used in a project or job) from skills that are only *listed*. Interviewers ask for proof, so this shows where you are exposed. |
| **Live agent trace** | The UI shows each agent starting and finishing, its time, what it did and which tools it used. |
| **Hybrid role matching** | 55% weighted skill coverage + 45% semantic similarity, over 18 roles, ranked with FAISS. See the ablation below: on a small test it matched keywords-only rather than beating it. |
| **Trained ML classifier** | A TF-IDF + Logistic Regression model predicts the job category of a resume. Metrics are shown in the app's model card. |
| **Paste any job description** | Lines marked *must / mandatory / required* become must-have skills; the resume is scored against that JD. |
| **Interview Coach** | Questions about your own projects and the skills the role needs ("what was YOUR contribution?"). |
| **Works offline of an LLM** | Without an API key, agents fall back to rule-based tips and the UI says so. |

## Architecture
```
 Upload (PDF/TXT)
      |
 parser_agent --> matcher_agent --> target_agent
                                        |
        +---------------+----------------+--------------------+
        v               v                v                    v
   scorer_agent      gap_agent      interview_agent      classifier_agent     (parallel)
        +---------------+----------------+--------------------+
                                        v
                                 rewriter_agent <-----------+
                                        v                   | retry (max 3)
                                  critic_agent --- rejected-+
                                        | approved
                                        v
                                 reporter_agent  --> streamed to the UI (NDJSON)
```

| Agent | Responsibility |
|---|---|
| Parser | Extracts text with pypdf, splits sections, finds contact info, GitHub/LinkedIn links, skills (taxonomy of 99 skills) and bullet points |
| Matcher | Embeds the resume, searches the FAISS index of roles, returns top matches |
| Target | Chooses what to score against: pasted JD, selected role, or best-fit role |
| Scorer | Six-component ATS score: keywords 30%, impact 20%, skill evidence 15%, GitHub portfolio 15%, structure 10%, format 10% |
| Gap Analyst | Missing skills with priority, estimated hours, learning tip and a time-boxed roadmap |
| Interview Coach | Question bank plus optional LLM-written questions from your resume |
| ML Classifier | Predicts the resume's job category with the trained TF-IDF model (skipped if no model is trained) |
| Rewriter | Drafts stronger bullets with the LLM (Groq or Gemini) |
| Critic | Checks verb, length, meaning drift and the fabrication guard |
| Reporter | Assembles the final report and a short recruiter-style verdict |

## Tech stack
Python, LangGraph, FastAPI, Sentence-Transformers (all-MiniLM-L6-v2), FAISS, scikit-learn, pypdf, Groq / Gemini API (optional), React, Vite, Framer Motion, pytest.

## Run it
Use **Python 3.10 to 3.12**. Newer versions (3.13+) may not have installable wheels for `faiss-cpu` and `sentence-transformers` yet.

```bash
git clone https://github.com/AnkitaMaurya63/smarthire.git
cd smarthire
python -m venv venv
venv\Scripts\activate          # Windows CMD   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env         # then paste ONE free key (Groq or Gemini) into .env
uvicorn app:app --reload
```
Open http://127.0.0.1:8000 and upload a resume.

- **No API key?** It still works; AI rewriting and AI interview questions switch to rule-based tips.
- **Slow first start?** Sentence-Transformers downloads a ~90 MB model once. To skip it, set `EMBEDDINGS=tfidf` in `.env`.
- **Gemini model error?** Set `LLM_MODEL` in `.env` to a model your key supports.

## Results
Dataset: Kaggle *Updated Resume Dataset* (962 rows, 25 categories). It contains 796 duplicate resumes, which are removed **before** splitting so the numbers are not inflated. 163 unique resumes in 24 categories remain (`PMO` has too few and is dropped).

**Resume category classifier** (`python ml/train.py --data data/resumes.csv --min-per-class 4`, 130 train / 33 test)

| Model | Top-1 | Top-3 | Macro-F1 | 4-fold CV |
|---|---|---|---|---|
| TF-IDF + Logistic Regression (selected) | 90.9% | 93.9% | 0.869 | 91.4% ± 3.6% |
| TF-IDF + Linear SVM | 90.9% | 97.0% | 0.869 | 90.2% ± 4.5% |

The test set is only 33 resumes, so treat each number as roughly plus or minus several points.

**Role-matching ablation** (`python ml/ablation.py --data data/resumes.csv`, 52 unique resumes from 7 tech categories, embeddings: all-MiniLM-L6-v2)

| Method | Top-1 | Top-3 |
|---|---|---|
| Keywords only (weighted skill coverage) | 40.4% | 76.9% |
| Embeddings only | 30.8% | 67.3% |
| Hybrid 55/45 (used in SmartHire) | 40.4% | 71.2% |
| Random baseline | 13.4% | 35.8% |

Finding: every method is far above random, but on this small set the hybrid did **not** beat keywords-only, and embeddings alone were the weakest. Keyword coverage is therefore the main signal and embeddings are a supporting one. More labelled resumes would be needed to say more.

## Tests
```bash
pytest -q
```
Covers skill matching edge cases, parser, scoring, the fabrication guard, the full graph, the retry loop (with a mocked LLM) and the classifier agent's no-model fallback (10 tests).

## API
- `POST /api/analyze` (multipart: `file`, `role_id`, `jd_text`) streams newline-delimited JSON events, one per finished agent, then the final report
- `GET /api/roles`, `GET /api/status`, `GET /api/model-card`, `GET /health`

## Limitations (honest)
- Skill extraction uses a curated taxonomy, so skills outside it are not detected.
- Scanned (image-only) PDFs are not supported; there is no OCR.
- The score is a heuristic rubric, not the scoring of any real company's ATS.
- Role database has 18 hand-written roles; add more in `data/roles.json`.
- The classifier is trained on a small public dataset (163 unique resumes after removing copies), so its metrics are indicative, not production accuracy. Its categories (Java Developer, Testing, HR...) differ from the 18 target roles.
- The matcher ablation uses 52 resumes and a hand-made category-to-role mapping (see `ml/ablation.py`), so small differences between methods are within noise.

## Project structure
```
smarthire/
  app.py                  FastAPI app
  smarthire/              agents and workflow (parser, scoring, matcher, gaps, rewriter, interview, classifier, graph, llm)
  ml/                     train.py (classifier), ablation.py (matcher comparison), predict.py
  models/                 resume_classifier.joblib (trained model)
  results/                classifier_metrics.json, classifier_confusion_matrix.csv, ablation.json
  data/                   skills.json, roles.json
  frontend/               React + Framer Motion UI (frontend/dist is the build served by FastAPI)
  static/index.html       simple fallback UI used if the React build is missing
  tests/                  pytest suite
```


## Frontend (React + Framer Motion)

```bash
cd frontend
npm install
npm run build        # outputs frontend/dist, served automatically by FastAPI
uvicorn app:app --reload   # from the project root, open http://127.0.0.1:8000
```

For live frontend development run `npm run dev` (port 5173, proxies /api to port 8000).
Fonts: Inter (body/UI) and Plus Jakarta Sans (headings). Animations respect `prefers-reduced-motion`.


## Train the ML model (optional, adds the "ML Classifier" agent)

1. Download the Kaggle "Updated Resume Dataset" (`UpdatedResumeDataSet.csv`) and save it as `data/resumes.csv`.
2. Train the resume-to-category classifier (duplicates are removed before the split, so the numbers are honest):
   ```bash
   python ml/train.py --data data/resumes.csv --min-per-class 4
   ```
   This writes `models/resume_classifier.joblib` and `results/classifier_metrics.json`.
3. Compare keyword, embedding and hybrid role matching on the same resumes:
   ```bash
   python ml/ablation.py --data data/resumes.csv
   ```
4. Restart the server. The dashboard now has an **ML model** tab with predictions, the model card and the ablation table.

Without a trained model the app still works and that agent is skipped.
