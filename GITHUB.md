# GitHub: first push and later updates

## First push (one time)
Create an empty repo named `smarthire` on github.com (Public, no README/.gitignore/license), then in the project folder:

```powershell
git init
git add .
git status
git commit -m "SmartHire: multi-agent resume analyzer"
git branch -M main
git remote add origin https://github.com/AnkitaMaurya63/smarthire.git
git push -u origin main
```
Username: your GitHub username. Password: your Personal Access Token (not your GitHub password).
`git status` must NOT list `venv/`, `.env` or `node_modules/`.

## Every later update (3 commands)
```powershell
git add .
git commit -m "Describe what you changed"
git push
```
Check `git status` before committing. Use a short message that says what changed, for example
`Add ML classifier results` or `Fix role dropdown on mobile`.

## Useful commands
```powershell
git status              # what changed since the last commit
git diff                # see the exact changes
git log --oneline       # history of commits
git pull                # fetch changes made on GitHub (e.g. edited README in the browser)
```

## Common problems
- `rejected ... fetch first`: GitHub has changes you do not have. Run `git pull --rebase`, then `git push`.
- Pushed a secret (`.env`, API key) by mistake: revoke that key on the provider's site immediately, then remove the file and push again. Deleting it later does not hide it from history.
- Changed the React frontend: run `cd frontend && npm run build` first, then commit `frontend/dist` too, so the app runs without Node.
- Trained the model: commit `models/resume_classifier.joblib` and `results/*.json` so others (and your deployment) get the same model.
