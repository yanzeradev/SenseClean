from pydantic import BaseModel, Field
from datetime import datetime

class DetectionBase(BaseModel):
    cam_id: int = Field(..., description="camera ID")
    # limits the list to 4 fields
    bbox: list[float] = Field(..., min_length=4, max_length=4, description="bounding box coordinates [x_min, y_min, x_max, y_max]")
    # limits the input to between 0 and 1
    confidence: float = Field(..., ge=0.0, le=1.0, description="detection score")
    track_id: int = Field(..., description="tracking ID")

class DetectionCreate(DetectionBase):
    pass

class DetectionResponse(DetectionBase):
    id: int = Field(..., description="detection ID")
    timestamp: datetime = Field(..., description="detection timestamp")

    # configures the model to allow population by field name or by attribute name
    class Config:
        from_attributes = True