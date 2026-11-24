"""SmartHire API.  Run:  uvicorn app:app --reload   then open http://127.0.0.1:8000"""
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from smarthire import classifier, llm
from smarthire.graph import AGENTS, stream_analysis
from smarthire.matcher import get_matcher
from smarthire.skills import roles

MAX_BYTES = 5 * 1024 * 1024


@asynccontextmanager
async def lifespan(app):
    get_matcher()  # warm up: loads the embedding model and builds the FAISS index once
    yield


app = FastAPI(title="SmartHire", version="1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    m = get_matcher()
    return {"llm": llm.info(), "embeddings": m.embedder.name, "index": m.index_name,
            "agents": [{"id": k, "label": v} for k, v in AGENTS.items()]}


@app.get("/api/model-card")
def model_card():
    return {"classifier": classifier.model_card(), "ablation": classifier.ablation()}


@app.get("/api/roles")
def list_roles():
    return [{"id": r["id"], "title": r["title"], "category": r["category"]} for r in roles()]


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), role_id: str = Form(""), jd_text: str = Form("")):
    data = await file.read()
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is larger than 5 MB.")

    def events():
        for ev in stream_analysis(data, file.filename or "resume.pdf", role_id, jd_text[:8000]):
            yield json.dumps(ev, default=str) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


from pathlib import Path

DIST = Path(__file__).parent / "frontend" / "dist"

if (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        # API and health routes are registered above, so only unknown paths reach here.
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        f = (DIST / path).resolve()
        if path and DIST.resolve() in f.parents and f.is_file():
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
else:
    # No React build present: fall back to the simple built-in UI.
    @app.get("/")
    def index():
        return FileResponse("static/index.html")

    app.mount("/static", StaticFiles(directory="static"), name="static")
