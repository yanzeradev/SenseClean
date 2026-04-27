import numpy as np
from typing import List, Dict, Any
from ultralytics import YOLO
from app.vision.interfaces import BaseTracker

class YoloTracker(BaseTracker):
    """
    Implementation of BaseTracker using Ultralytics' built-in BoT-SORT/ByteTrack.
    """
    # MÁGICA 1: Trocando para bytetrack (Mais rápido e ignora perdas de frames)
    def __init__(self, model_path: str, tracker_type: str = "bytetrack.yaml"):
        self.model = YOLO(model_path)
        self.tracker_type = tracker_type

    def update(self, detections: np.ndarray, frame: np.ndarray) -> Dict[str, Any]:
        import supervision as sv 

        results = self.model.track(
            frame, 
            persist=True, 
            tracker=self.tracker_type, 
            imgsz=640,   
            # MÁGICA 2: Baixando a confiança para 0.25 (A IA não "solta" a pessoa se ela borrar na imagem)
            conf=0.25,   
            iou=0.5,    
            verbose=False,
            device="0", 
            half=True,     
        )
        
        tracked_objects = []
        sv_detections = None

        if len(results) > 0:
            sv_detections = sv.Detections.from_ultralytics(results[0])

            if results[0].boxes is not None and results[0].boxes.id is not None:
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
                    
        # Retornamos os dados analíticos (pro banco) e o objeto do Supervision (pra desenhar)
        return {
            "analytics_data": tracked_objects,
            "sv_detections": sv_detections
        }