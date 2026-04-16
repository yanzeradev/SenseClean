from pydantic import BaseModel
from typing import List, Dict

class FrameDimensions(BaseModel):
    width: int
    height: int

class ProcessVideoRequest(BaseModel):
    video_id: str
    in_side: str  # 'left' or 'right'
    entrant_line_points: List[Dict[str, float]]
    passerby_line_points: List[Dict[str, float]]
    frame_dimensions: FrameDimensions