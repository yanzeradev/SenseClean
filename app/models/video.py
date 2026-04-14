from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime, timezone
from app.database import Base
import uuid

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
    
    # Status tracks the lifecycle: pending, processing, completed, failed
    status = Column(String, default="pending", index=True)
    
    # Store the final analytics results directly as JSON
    results = Column(JSON, nullable=True)
    
    # Automatically track when the record was created
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))