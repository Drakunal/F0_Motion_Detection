# app/services/motion_service.py
from PIL import Image, ImageChops, ImageStat
from io import BytesIO
from sqlalchemy.orm import Session
from app.db import models

class MotionService:
    """
    Simple frame-difference motion detector using Pillow.
    """

    def __init__(self, threshold: float = 200000.0):
        self.threshold = threshold
        self._prev_gray = None  # store previous frame as PIL.Image in 'L' mode

    def _open_image_gray(self, img_bytes: bytes) -> Image.Image:
        bio = BytesIO(img_bytes)
        img = Image.open(bio)
        img = img.convert("L")  # grayscale
        return img

    def compute_diff_score(self, img_bytes: bytes) -> float:
        cur_gray = self._open_image_gray(img_bytes)

        if self._prev_gray is None:
            self._prev_gray = cur_gray
            return 0.0

        # Ensure same size
        if self._prev_gray.size != cur_gray.size:
            self._prev_gray = self._prev_gray.resize(cur_gray.size)

        diff = ImageChops.difference(cur_gray, self._prev_gray)

        bbox = diff.getbbox()
        if bbox is None:
            score = 0.0
        else:
            stat = ImageStat.Stat(diff)
            score = float(stat.sum[0])

        self._prev_gray = cur_gray

        return score

    def is_motion(self, score: float) -> bool:
        return score > self.threshold

    def analyze_and_record(self, db: Session, image_id: int, img_bytes: bytes):
        score = self.compute_diff_score(img_bytes)
        motion_flag = self.is_motion(score)
        me = models.MotionEvent(
            image_id=image_id,
            diff_score=score,
            is_motion=motion_flag,
        )
        db.add(me)
        db.commit()
        db.refresh(me)
        return me
