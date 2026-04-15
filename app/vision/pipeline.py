import cv2
import numpy as np
import asyncio
from typing import AsyncGenerator, Tuple, List, Dict, Any
from app.vision.interfaces import BaseDetector, BaseTracker

class VideoPipeline:
    """
    Orchestrates the video reading, detection, and tracking processes.
    Uses an Async Generator pattern and Worker Threads to prevent Event Loop blocking.
    """

    def __init__(self, video_source: str, detector: BaseDetector, tracker: BaseTracker):
        self.video_source = video_source
        self.detector = detector
        self.tracker = tracker

    def _process_single_frame(self, cap: cv2.VideoCapture) -> Tuple[bool, np.ndarray, List[Dict[str, Any]]]:
        """
        Synchronous method containing the heavy CPU/GPU operations.
        This is designed to be executed inside a separate Thread.
        """
        ret, frame = cap.read()
        if not ret:
            return False, None, []
            
        detections = self.detector.detect(frame)
        tracks = self.tracker.update(detections, frame)
        
        return True, frame, tracks

    async def process(self) -> AsyncGenerator[Tuple[np.ndarray, List[Dict[str, Any]]], None]:
        """
        Starts the video processing loop asynchronously.
        """
        cap = cv2.VideoCapture(self.video_source)

        if not cap.isOpened():
            raise ValueError(f"Could not open video source: {self.video_source}")

        try:
            while True:
                # 💥 MAGIC HAPPENS HERE:
                # We send the heavy lifting to a background thread.
                # The 'await' lets FastAPI answer frontend requests while waiting for the frame!
                ret, frame, tracks = await asyncio.to_thread(self._process_single_frame, cap)
                
                if not ret:
                    break

                yield frame, tracks
                
        finally:
            cap.release()