# app/services/stream_service.py
import asyncio
import uuid
import datetime
from pathlib import Path
import requests
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import UPLOAD_DIR
from app.db import models
from app.db.session import SessionLocal
from app.services.motion_service import MotionService
from app.services.storage_service import motion_service, storage_manager  # storage_manager singleton

# NOTE: motion_service is imported from motion_service module; ensure singleton or create new
# Here we assume motion_service is imported from motion_service module, or you can instantiate:
# motion_service = MotionService(threshold=200000.0)

class StreamHandle:
    def __init__(self, name: str, url: str, interval: float):
        self.name = name
        self.url = url
        self.interval = interval
        self._task: Optional[asyncio.Task] = None
        self._cancel = asyncio.Event()

    def start(self, loop: asyncio.AbstractEventLoop):
        if self._task is None:
            self._task = loop.create_task(self._run())

    async def stop(self):
        if self._task:
            self._cancel.set()
            await self._task

    async def _run(self):
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        while not self._cancel.is_set():
            try:
                resp = await asyncio.to_thread(requests.get, self.url, timeout=8)
                if resp.status_code == 200 and resp.content:
                    contents = resp.content
                    await asyncio.to_thread(process_frame_sync, contents)
            except Exception:
                # swallow errors to keep worker alive; in production log this
                pass

            try:
                await asyncio.wait_for(self._cancel.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                continue

def process_frame_sync(contents: bytes) -> Dict[str, Any]:
    """
    Save contents to file, insert ImageLog, run motion detection and record MotionEvent.
    Also call storage_manager to manage retention.
    This is synchronous and intended to be called inside asyncio.to_thread.
    """
    ext = ".jpg"
    fname = f"{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / fname
    dest.write_bytes(contents)

    db: Session = SessionLocal()
    me = None
    try:
        img = models.ImageLog(filename=str(dest.resolve()))
        db.add(img)
        db.commit()
        db.refresh(img)

        # Tell storage manager about this new saved image (buffer it)
        try:
            storage_manager.add_new_image(image_id=img.id, filepath=dest, timestamp=img.timestamp)
        except Exception:
            pass

        # motion detection + record
        try:
            me = motion_service.analyze_and_record(db, image_id=img.id, img_bytes=contents)
        except Exception:
            me = None

        # After motion analysis, let storage manager decide retention
        try:
            if me is not None:
                storage_manager.handle_motion_result(image_id=img.id, is_motion=bool(me.is_motion))
        except Exception:
            pass

        result = {
            "image_id": img.id,
            "filename": img.filename,
            "motion_event": {
                "id": me.id,
                "is_motion": bool(me.is_motion),
                "diff_score": me.diff_score,
            } if me else None,
        }
    finally:
        db.close()
    return result
