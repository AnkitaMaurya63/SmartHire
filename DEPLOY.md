# Deploy SmartHire on Hugging Face Spaces (free)

You get a public link like `https://<hf-username>-smarthire.hf.space` that opens the dashboard directly.

## One-time setup
1. Create a free account at https://huggingface.co.
2. Create a token: Settings -> Access Tokens -> New token -> type **Write**. Copy it (you only see it once).
3. Create the Space: https://huggingface.co/new-space
   - Space name: `smarthire`
   - SDK: **Docker** -> **Blank**
   - Hardware: **CPU basic (free)**
   - Visibility: **Public**
4. Commit the deploy files on `main` and push to GitHub as usual:
   ```powershell
   git add .
   git commit -m "Add Dockerfile and Hugging Face deploy files"
   git push
   ```
5. Connect your local repo to the Space (replace `<hf-username>`):
   ```powershell
   git remote add space https://huggingface.co/spaces/<hf-username>/smarthire
   ```
6. Publish:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\deploy_space.ps1
   ```
   When asked, username = your Hugging Face username, password = the **token** from step 2.
7. Open the Space page -> **Logs** tab. The first build takes about 5 to 10 minutes (it installs PyTorch and downloads the embedding model). When it says "Running", open the **App** tab.

## Put the link in the README
Add this near the top of README.md, then commit and push:
```
**Live demo:** https://<hf-username>-smarthire.hf.space
```

## Updating the deployed app later
```powershell
git add .
git commit -m "What you changed"
git push                                   # GitHub
powershell -ExecutionPolicy Bypass -File .\deploy_space.ps1   # Hugging Face (rebuilds automatically)
```
If you changed the React code, run `cd frontend && npm run build` first and commit `frontend/dist`.

## Optional: AI rewrites on the live demo
Space -> Settings -> Variables and secrets -> New secret: `GROQ_API_KEY` (or `GEMINI_API_KEY`).
Everyone using the demo then spends your free quota. A built-in limit of 20 analyses per visitor per hour protects it
(change with the variable `RATE_LIMIT_PER_HOUR`). Without a key the demo still works with rule-based tips.

## Good to know
- Free Spaces go to sleep after a period of no visits and wake up in about a minute on the next visit.
- Resumes are analysed in memory and not saved. Say so honestly in the app (it already does) and do not log resume text.
- The Space is public: anyone can upload a resume. Tell friends to use the sample resume if they prefer not to upload their own.
