# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from pathlib import Path
from app.core.config import DATA_DIR, UPLOAD_DIR
from app.db import models
from app.db.session import engine
from app.api import upload, images, motion, stream
from app.services.storage_service import storage_manager

# STATIC_DIR should be app/static (same folder as this file's parent)
STATIC_DIR = Path(__file__).resolve().parent / "static"
# create static dir if missing (won't overwrite existing files)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# create minimal default static pages if they don't exist (safe to leave as-is)
camera_file = STATIC_DIR / "camera.html"
if not camera_file.exists():
    camera_file.write_text(
        "<!doctype html>\n"
        "<html><head><meta charset='utf-8'/><title>Camera uploader</title></head>\n"
        "<body>\n<h2>Camera uploader</h2>\n<p>Default camera page placeholder.</p>\n</body></html>"
    )

viewer_file = STATIC_DIR / "viewer.html"
if not viewer_file.exists():
    viewer_file.write_text(
        "<!doctype html>\n"
        "<html><head><meta charset='utf-8'/><title>Viewer</title></head>\n"
        "<body>\n<h2>Viewer</h2>\n<p>Default viewer placeholder.</p>\n</body></html>"
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    models.Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

# include routers
app.include_router(upload.router)
app.include_router(images.router)
app.include_router(motion.router)
app.include_router(stream.router)

# mount static files from app/static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse("<h3>F0 Image Ingest Server</h3>"
                        "<p><a href='/static/camera.html'>Camera page</a> | "
                        "<a href='/static/viewer.html'>Viewer</a></p>")

@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    models.Base.metadata.create_all(bind=engine)

    # start periodic cleanup thread (daemon)
    try:
        storage_manager.start_periodic_cleanup()
    except Exception:
        pass

    yield

    # on shutdown stop cleanup thread gracefully
    try:
        storage_manager.stop_periodic_cleanup()
    except Exception:
        pass
