import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8050))
    reload = os.getenv("RELOAD", "true").lower() in ("true", "1", "yes")

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
    )
