import cv2
import numpy as np
import asyncio
import threading
from queue import Queue, Empty
from typing import AsyncGenerator, Tuple, List, Dict, Any
from app.vision.interfaces import BaseDetector, BaseTracker

class VideoPipeline:
    def __init__(self, video_source: str, detector: BaseDetector, tracker: BaseTracker):
        self.video_source = video_source
        self.detector = detector
        self.tracker = tracker
        
        # O Buffer! Guarda até 60 frames na RAM para a GPU nunca ficar esperando
        self.frame_queue = Queue(maxsize=60)
        self.stopped = False

    def _reader_thread(self):
        """Thread dedicada APENAS a extrair frames do arquivo o mais rápido possível."""
        cap = cv2.VideoCapture(self.video_source)
        
        if not cap.isOpened():
            self.stopped = True
            return

        while not self.stopped:
            if not self.frame_queue.full():
                ret, frame = cap.read()
                if not ret:
                    self.stopped = True
                    break
                self.frame_queue.put(frame)
            else:
                # Se a fila encher (a CPU leu mais rápido que a GPU processou), descansa 1ms
                import time
                time.sleep(0.001) 
                
        cap.release()

    def _process_single_frame(self, frame: np.ndarray) -> Tuple[bool, np.ndarray, List[Dict[str, Any]]]:
        """A GPU processa o frame que já estava pronto na fila."""
        # Note que removemos a leitura (cap.read) daqui!
        detections = self.detector.detect(frame)
        tracks = self.tracker.update(detections, frame)
        return True, frame, tracks

    async def process(self) -> AsyncGenerator[Tuple[np.ndarray, List[Dict[str, Any]]], None]:
        """Orquestrador Assíncrono"""
        
        # Inicia a Thread que vai "encher" o nosso balde de frames
        reader_t = threading.Thread(target=self._reader_thread, daemon=True)
        reader_t.start()

        try:
            while True:
                try:
                    # Tenta pegar um frame do balde (espera no máximo 0.1s se estiver vazio)
                    frame = self.frame_queue.get(timeout=0.1)
                except Empty:
                    if self.stopped:
                        break # O vídeo acabou
                    continue

                # Manda o frame que já está na memória para a GPU processar
                ret, processed_frame, tracks = await asyncio.to_thread(self._process_single_frame, frame)
                
                yield processed_frame, tracks
                
        finally:
            self.stopped = True
            reader_t.join(timeout=1.0)