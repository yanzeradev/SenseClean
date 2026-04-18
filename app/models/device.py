from sqlalchemy import Column, Integer, String, Boolean, JSON
from app.database import Base

class Device(Base):
    """
    SQLAlchemy model representing an IP Camera/RTSP Device.
    """
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    ip_address = Column(String, nullable=False, index=True)
    port = Column(Integer, default=554)
    username = Column(String, nullable=True)
    password = Column(String, nullable=True)
    rtsp_url = Column(String, nullable=True)

    user_id = Column(Integer, index=True, nullable=True)
    
    # State flags
    is_configured = Column(Boolean, default=False)
    
    # Advanced scheduling and rules
    processing_start_time = Column(String, nullable=True) # Ex: "08:00"
    processing_end_time = Column(String, nullable=True)   # Ex: "18:00"
    lines_config = Column(JSON, nullable=True)            # Stores entrant and passerby lines