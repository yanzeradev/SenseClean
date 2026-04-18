from pydantic import BaseModel
from typing import Optional, Dict, Any

class DeviceBase(BaseModel):
    ip_address: str
    port: int = 554

class DeviceConnect(DeviceBase):
    """Used for initial autodiscovery connection"""
    username: str
    password: str

class DeviceUpdate(BaseModel):
    """Used when the frontend saves canvas lines and schedules"""
    name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    manufacturer: Optional[str] = None
    processing_start_time: Optional[str] = None
    processing_end_time: Optional[str] = None
    lines_config: Optional[Dict[str, Any]] = None

class DeviceResponse(DeviceBase):
    """Data sent back to the React frontend"""
    id: int
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    is_configured: bool
    rtsp_url: Optional[str] = None
    processing_start_time: Optional[str] = None
    processing_end_time: Optional[str] = None
    lines_config: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True