# Deploy SmartHire on Render (free web service)

Result: a public link like `https://smarthire-xxxx.onrender.com` that opens the dashboard.

## What is different from running on your laptop
The free host is small, so the demo uses `requirements-deploy.txt` (no PyTorch) and `EMBEDDINGS=tfidf`.
The dashboard shows "Embeddings: TF-IDF (fallback)" honestly. Locally, with `requirements.txt`, SmartHire uses
Sentence-Transformers (all-MiniLM-L6-v2). In tests, the lightweight mode used about 275 MB of RAM.
Say this in the README and in interviews; do not claim the live demo runs transformer embeddings.

## Step 0: pin your scikit-learn version (important)
The classifier file in `models/` was saved with your scikit-learn version. Render must install the same one.
In your venv run:
```powershell
pip show scikit-learn
```
Note the `Version:` line (for example `1.7.2`). Open `requirements-deploy.txt` and change the line
`scikit-learn` to `scikit-learn==1.7.2` (use your number).

## Step 1: commit and push
```powershell
git add .
git commit -m "Add Render deploy files"
git push
```

## Step 2: create the service on Render
1. Sign up at https://render.com with your GitHub account.
2. New + -> **Web Service** -> choose the `SmartHire` repository.
3. If it reads `render.yaml`, accept it. Otherwise fill in by hand:
   - Runtime: **Python 3**, Instance type: **Free**
   - Build command: `pip install -r requirements-deploy.txt`
   - Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - Environment variables: `PYTHON_VERSION` = `3.12.8`, `EMBEDDINGS` = `tfidf`
4. Create. The first build takes a few minutes. Open the `.onrender.com` link when it says Live.

## Step 3: add the link to the README
```
**Live demo:** https://<your-service>.onrender.com  (free tier: the first load after idle can take about a minute)
```
Then `git add .`, `git commit`, `git push`. Render redeploys automatically on every push to GitHub.

## Good to know (from Render's free-tier docs)
- A free service spins down after 15 minutes without traffic; waking it takes about one minute.
- 750 free instance hours per month per workspace.
- Local files are lost on restart. SmartHire stores nothing, so this does not matter.
- Open the link yourself a minute before sharing it with an interviewer.
