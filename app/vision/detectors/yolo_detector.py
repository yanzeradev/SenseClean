import numpy as np
from ultralytics import YOLO
from app.vision.interfaces import BaseDetector

class YoloDetector(BaseDetector):
    """
    Production-ready YOLO detector implementing the BaseDetector interface.
    Handles GPU warmup and standardizes output for downstream trackers.
    """
    
    def __init__(self, model_path: str, device: str = "cpu", conf_threshold: float = 0.4, imgsz: int = 640):
        self.model = YOLO(model_path).to(device)
        self.conf_threshold = conf_threshold
        self.imgsz = imgsz
        
        self._warmup()

    def _warmup(self) -> None:
        """
        Performs a dummy inference to allocate memory on the GPU.
        This prevents the first actual frame from taking significantly longer to process.
        """
        dummy_frame = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
        self.model(dummy_frame, verbose=False)

    def detect(self, frame: np.ndarray) -> np.ndarray:
        """
        Executes YOLO inference and filters the results.
        """
        # half=True is highly recommended for TensorRT/CUDA environments to speed up FP16 inference
        use_half_precision = "cuda" in str(self.model.device)
        
        results = self.model(
            frame, 
            imgsz=self.imgsz, 
            conf=self.conf_threshold, 
            iou=0.5, 
            half=use_half_precision,
            verbose=False
        )
        
        if len(results) == 0 or len(results[0].boxes) == 0:
            return np.empty((0, 6))

        # Ultralytics natively returns a tensor of shape (N, 6)
        # Columns: [x1, y1, x2, y2, confidence, class_id]
        return results[0].boxes.data.cpu().numpy()