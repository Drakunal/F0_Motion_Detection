from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db import models
from fastapi.responses import FileResponse

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/images")
def list_images(db: Session = Depends(get_db)):
    rows = db.query(models.ImageLog).order_by(models.ImageLog.id.desc()).limit(200).all()
    return [{"id": r.id, "filename": r.filename, "timestamp": r.timestamp.isoformat()} for r in rows]

@router.get("/images/{image_id}")
def get_image_meta(image_id: int, db: Session = Depends(get_db)):
    r = db.query(models.ImageLog).filter(models.ImageLog.id == image_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="image not found")
    return {"id": r.id, "filename": r.filename, "timestamp": r.timestamp.isoformat()}

@router.get("/images/{image_id}/raw")
def get_image_file(image_id: int, db: Session = Depends(get_db)):
    r = db.query(models.ImageLog).filter(models.ImageLog.id == image_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="image not found")
    return FileResponse(r.filename)
