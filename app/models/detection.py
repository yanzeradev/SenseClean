from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from datetime import datetime, timezone
from app.database import Base

class Detection(Base):
    __tablename__ = "detections"

    # index is used to speed up queries on this column
    id = Column(Integer, primary_key=True, index=True)
    cam_id = Column(Integer, index=True)
    bbox = Column(JSON)
    score = Column(Float)
    track_id = Column(Integer)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))