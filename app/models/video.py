from sqlalchemy import Column, String, DateTime, JSON, Integer
from datetime import datetime
from app.database import Base
import uuid
from sqlalchemy import Date

class Video(Base):
    """
    SQLAlchemy model representing a Video processing job in the database.
    """
    __tablename__ = "videos"

    # We use UUID (String) instead of Integer for security (harder to guess URLs)
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    
    # Paths to the physical files
    original_video_path = Column(String, nullable=False)
    processed_video_path = Column(String, nullable=True)
    
    user_id = Column(Integer, index=True, nullable=True)
    
    reference_date = Column(Date, nullable=True, index=True)

    status = Column(String, default="pending", index=True)
    
    results = Column(JSON, nullable=True)
    
    # Automatically track when the record was created
    created_at = Column(DateTime, default=datetime.now)