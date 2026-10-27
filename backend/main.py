import os
import io
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

from backend.session_manager import SessionManager

app = FastAPI(title="AI Revision Agent API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = SessionManager()


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
    topic = req.topic.strip() if req.topic else "Uploaded Study Notes"
    session = manager.create(topic=topic, difficulty=req.difficulty, doc_text=req.doc_text)
    try:
        result = manager.start(session.id)
    except Exception as e:
        manager.delete(session.id)
        raise HTTPException(status_code=500, detail=str(e))

    return {"topic": topic, "difficulty": req.difficulty, **result}


@app.post("/api/session/respond")
async def respond(req: RespondRequest):
    session = manager.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        result = manager.respond(req.session_id, req.answer)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/reset")
async def reset_session(req: ResetRequest):
    manager.delete(req.session_id)
    return {"status": "ok"}


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


@app.get("/api/session/resume/{session_id}")
async def resume_session(session_id: str):
    data = manager.resume(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session checkpoint not found")
    return data


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
            pages_text = []
            for i, page in enumerate(reader.pages):
                extracted = page.extract_text()
                if extracted and extracted.strip():
                    pages_text.append(extracted.strip())
            text = "\n\n".join(pages_text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading PDF: {e}")
    else:
        text = content.decode("utf-8", errors="ignore")

    text = text.strip()
    if not text:
        raise HTTPException(
            status_code=400,
            detail="Could not extract any readable text from this file. If it is a scanned PDF (image only), please provide a text-searchable PDF, TXT, or Markdown file."
        )

    return {"text": text, "chars": len(text), "filename": file.filename}


@app.get("/")
async def index():
    response = FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
