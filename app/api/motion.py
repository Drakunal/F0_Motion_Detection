from fastapi import APIRouter, Depends
from app.db.session import SessionLocal
from sqlalchemy.orm import Session
from app.db import models

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/motion_events")
def list_motion(db: Session = Depends(get_db)):
    rows = db.query(models.MotionEvent).order_by(models.MotionEvent.id.desc()).limit(200).all()
    return [
        {
            "id": r.id,
            "image_id": r.image_id,
            "timestamp": r.timestamp.isoformat(),
            "diff_score": r.diff_score,
            "is_motion": bool(r.is_motion),
        }
        for r in rows
    ]
