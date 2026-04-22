import numpy as np
from typing import List, Dict, Any
from ultralytics import YOLO
from app.vision.interfaces import BaseTracker

class YoloTracker(BaseTracker):
    """
    Implementation of BaseTracker using Ultralytics' built-in BoT-SORT/ByteTrack.
    """
    def __init__(self, model_path: str, tracker_type: str = "bytetrack.yaml"):
        self.model = YOLO(model_path)
        self.tracker_type = tracker_type

    def update(self, detections: np.ndarray, frame: np.ndarray) -> List[Dict[str, Any]]:
        results = self.model.track(
            frame, 
            persist=True, 
            tracker=self.tracker_type, 
            imgsz=480, 
            verbose=False
        )
        
        tracked_objects = []
        if len(results) > 0 and results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().numpy()
            scores = results[0].boxes.conf.cpu().numpy()
            classes = results[0].boxes.cls.int().cpu().numpy()

            for box, track_id, score, cls_id in zip(boxes, track_ids, scores, classes):
                tracked_objects.append({
                    "bbox": [float(box[0]), float(box[1]), float(box[2]), float(box[3])],
                    "track_id": int(track_id),
                    "confidence": float(score),
                    "class_id": int(cls_id)
                })
                
        return tracked_objects