"""
Entry point — run the FastAPI server serving both API and frontend.

Usage:
    python run.py
    or
    .venv/Scripts/python.exe run.py
"""

import os
import uvicorn

if __name__ == "__main__":
    # Support dynamic PORT from cloud hosting environments (Render, Railway, Heroku, etc.)
    port = int(os.getenv("PORT", 8050))
    reload = os.getenv("RELOAD", "true").lower() in ("true", "1", "yes")

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
    )
