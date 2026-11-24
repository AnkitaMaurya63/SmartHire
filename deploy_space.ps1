# Publishes the current commit of main to your Hugging Face Space.
# One-time setup:  git remote add space https://huggingface.co/spaces/<your-hf-username>/smarthire
# Every update:    commit on main as usual, then run  .\deploy_space.ps1
$ErrorActionPreference = "Stop"
if (git status --porcelain) { Write-Host "Commit your changes on main first (git add . ; git commit)."; exit 1 }
git checkout main
git checkout -B hf
$utf8 = New-Object System.Text.UTF8Encoding($false)   # no BOM, the Space config must start with ---
$header = [System.IO.File]::ReadAllText("space_header.txt", $utf8)
$readme = [System.IO.File]::ReadAllText("README.md", $utf8)
[System.IO.File]::WriteAllText("README.md", $header + $readme, $utf8)
git add README.md
git commit -m "Space config"
git push space hf:main --force
git checkout main
Write-Host "Done. Watch the build in the Logs tab of your Space."
