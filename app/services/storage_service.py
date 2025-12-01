# app/services/storage_service.py
import threading
import time
import os
from collections import deque
from datetime import datetime, timedelta
from typing import Optional, Deque, Tuple
from pathlib import Path

from app.core.config import UPLOAD_DIR, PRE_MOTION_BUFFER, RETENTION_HOURS, KEEP_ALL_FRAMES, CLEANUP_INTERVAL_SECONDS
from app.db.session import SessionLocal
from app.db import models

_lock = threading.Lock()

class StorageManager:
    """
    Manage an in-memory buffer of the most recent frames and perform deletions
    according to motion events and retention policy.
    """

    def __init__(self, upload_dir: Path, buffer_size: int = PRE_MOTION_BUFFER, retention_hours: int = RETENTION_HOURS):
        self.upload_dir = upload_dir
        self.buffer_size = int(buffer_size)
        self.retention_hours = int(retention_hours)
        # Buffer holds tuples: (image_id:int, filepath:Path, timestamp:datetime)
        self.buffer: Deque[Tuple[int, Path, datetime]] = deque(maxlen=self.buffer_size)
        # Set of image_ids explicitly preserved (due to motion)
        self.preserved_ids = set()
        # start periodic cleanup flag
        self._cleanup_thread = None
        self._stop_event = threading.Event()

    def add_new_image(self, image_id: int, filepath: Path, timestamp: Optional[datetime] = None):
        """
        Add a new saved image to the buffer. This does NOT decide deletion yet.
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        with _lock:
            self.buffer.append((image_id, filepath, timestamp))

    def handle_motion_result(self, image_id: int, is_motion: bool):
        """
        Called after motion analysis for the image with image_id.
        - if is_motion: mark everything in the buffer as preserved (they may be kept)
        - if not is_motion: remove older images outside the buffer if KEEP_ALL_FRAMES is False
        """
        with _lock:
            if is_motion:
                # Preserve buffer images
                for img_id, _, _ in self.buffer:
                    self.preserved_ids.add(img_id)
                # nothing else to delete now
            else:
                # No motion — we allow deletions
                if KEEP_ALL_FRAMES:
                    return
                # Delete any images older than current buffer window and not preserved.
                buffer_ids = {img_id for img_id, _, _ in self.buffer}
                self._delete_images_not_in(buffer_ids)

    def _delete_images_not_in(self, keep_ids):
        """
        Delete images whose id is not in keep_ids and not in preserved_ids.
        """
        db = SessionLocal()
        try:
            rows = db.query(models.ImageLog).all()
            for r in rows:
                if r.id in keep_ids or r.id in self.preserved_ids:
                    continue
                # delete file and DB row
                try:
                    if r.filename and os.path.exists(r.filename):
                        os.remove(r.filename)
                except Exception:
                    pass
                try:
                    db.delete(r)
                    db.commit()
                except Exception:
                    db.rollback()
        finally:
            db.close()

    def start_periodic_cleanup(self):
        """
        Start background thread to delete old files beyond retention_hours.
        Safe to call multiple times.
        """
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return
        self._stop_event.clear()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def stop_periodic_cleanup(self):
        self._stop_event.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=2)

    def _cleanup_loop(self):
        while not self._stop_event.is_set():
            try:
                self.run_cleanup_once()
            except Exception:
                pass
            self._stop_event.wait(CLEANUP_INTERVAL_SECONDS)

    def run_cleanup_once(self):
        """
        Delete files older than retention_hours and corresponding DB rows.
        """
        cutoff = datetime.utcnow() - timedelta(hours=self.retention_hours)
        db = SessionLocal()
        try:
            rows = db.query(models.ImageLog).filter(models.ImageLog.timestamp < cutoff).all()
            for r in rows:
                try:
                    if r.filename and os.path.exists(r.filename):
                        os.remove(r.filename)
                except Exception:
                    pass
                try:
                    db.delete(r)
                    db.commit()
                except Exception:
                    db.rollback()
        finally:
            db.close()

# singleton instance
storage_manager = StorageManager(upload_dir=UPLOAD_DIR, buffer_size=PRE_MOTION_BUFFER, retention_hours=RETENTION_HOURS)
