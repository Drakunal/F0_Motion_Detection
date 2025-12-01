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

    try:
        me = motion_service.analyze_and_record(db, image_id=img.id, img_bytes=contents)
    except Exception:
        me = None

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
