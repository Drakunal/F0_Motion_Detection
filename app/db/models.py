from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class ImageLog(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=False, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class MotionEvent(Base):
    __tablename__ = "motion_events"
    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    diff_score = Column(Float, nullable=True)
    is_motion = Column(Boolean, default=False)
