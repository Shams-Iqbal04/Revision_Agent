"""
Entry point — run the FastAPI server serving both API and frontend.

Usage:
    python run.py
    or
    .venv/Scripts/python.exe run.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8050,
        reload=True,
    )
