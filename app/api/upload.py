# app/api/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from pathlib import Path
import aiofiles
import uuid
import datetime
from sqlalchemy.orm import Session
from app.core.config import UPLOAD_DIR
from app.db.session import SessionLocal
from app.db import models
from app.services.motion_service import MotionService
from app.services.storage_service import storage_manager  # <-- new

router = APIRouter()
motion_service = MotionService(threshold=200000.0)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload")
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Only JPEG and PNG supported")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix or ".jpg"
    fname = f"{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / fname

    contents = await file.read()
    async with aiofiles.open(dest, "wb") as out_file:
        await out_file.write(contents)

    img = models.ImageLog(filename=str(dest.resolve()))
    db.add(img)
    db.commit()
    db.refresh(img)

    # Add to in-memory buffer for retention logic
    try:
        storage_manager.add_new_image(image_id=img.id, filepath=dest, timestamp=img.timestamp)
    except Exception:
        # don't break upload on storage-manager error
        pass

    try:
        me = motion_service.analyze_and_record(db, image_id=img.id, img_bytes=contents)
    except Exception:
        me = None

    # Let storage manager decide whether to keep or delete older frames
    try:
        if me is not None:
            storage_manager.handle_motion_result(image_id=img.id, is_motion=bool(me.is_motion))
    except Exception:
        pass

    return JSONResponse({
        "id": img.id,
        "filename": img.filename,
        "timestamp": img.timestamp.isoformat(),
        "motion_event": {
            "id": me.id,
            "is_motion": bool(me.is_motion),
            "diff_score": me.diff_score,
        } if me else None,
    })
