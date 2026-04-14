import cv2
import numpy as np
from typing import Generator, Tuple, List, Dict, Any
from app.vision.interfaces import BaseDetector, BaseTracker

class VideoPipeline:
    """
    Orchestrates the video reading, detection, and tracking processes.
    Uses a generator pattern to yield results frame-by-frame, ensuring memory efficiency.
    """

    def __init__(self, video_source: str, detector: BaseDetector, tracker: BaseTracker):
        """
        Args:
            video_source (str): Path to the video file or RTSP stream URL.
            detector (BaseDetector): An instance of a class implementing BaseDetector.
            tracker (BaseTracker): An instance of a class implementing BaseTracker.
        """
        self.video_source = video_source
        self.detector = detector
        self.tracker = tracker

    def process(self) -> Generator[Tuple[np.ndarray, List[Dict[str, Any]]], None, None]:
        """
        Starts the video processing loop.

        Yields:
            Tuple[np.ndarray, List[Dict]]: A tuple containing the current frame (numpy array) 
                                           and a list of tracked objects for that frame.
        """
        cap = cv2.VideoCapture(self.video_source)

        if not cap.isOpened():
            raise ValueError(f"Could not open video source: {self.video_source}")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Step 1: Detect objects in the current frame
                detections = self.detector.detect(frame)

                # Step 2: Update the tracker with the new detections
                tracks = self.tracker.update(detections, frame)

                # Yield the frame and the tracks to the consumer
                yield frame, tracks

        finally:
            # Ensures resources are released even if an exception occurs
            cap.release()