import os
import io
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from backend.session_manager import SessionManager

app = FastAPI(title="AI Revision Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = SessionManager()

FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

class StartRequest(BaseModel):
    topic: str
    difficulty: str = "Beginner"
    doc_text: Optional[str] = None

class RespondRequest(BaseModel):
    session_id: str
    answer: str

class ResetRequest(BaseModel):
    session_id: str

class ConcludeRequest(BaseModel):
    session_id: str

class DoubtRequest(BaseModel):
    session_id: str
    question: str

@app.post("/api/session/start")
async def start_session(req: StartRequest):
    topic = req.topic
    if req.doc_text:
        topic += f"\n\nContext Notes:\n{req.doc_text[:3000]}"

    session = manager.create(topic, req.difficulty)
    try:
        result = manager.start(session.id)
    except Exception as e:
        manager.delete(session.id)
        raise HTTPException(status_code=500, detail=str(e))

    return {"topic": req.topic, "difficulty": req.difficulty, **result}


@app.post("/api/session/respond")
async def respond(req: RespondRequest):
    session = manager.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        result = manager.respond(req.session_id, req.answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result


@app.post("/api/session/reset")
async def reset_session(req: ResetRequest):
    manager.delete(req.session_id)
    return {"success": True}


@app.post("/api/session/conclude")
async def conclude_session(req: ConcludeRequest):
    session = manager.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        result = manager.conclude(req.session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/doubt")
async def ask_doubt(req: DoubtRequest):
    try:
        result = manager.ask_doubt(req.session_id, req.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    text = ""

    if file.filename and file.filename.lower().endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            text = "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading PDF: {e}")
    else:
        text = content.decode("utf-8", errors="ignore")

    return {"text": text, "chars": len(text), "filename": file.filename}


@app.get("/")
async def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
