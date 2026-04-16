import cv2
import uuid
import shutil
import os
from fastapi import UploadFile

class FileService:
    """
    Handles all file system operations to keep the API layer clean.
    """
    
    @staticmethod
    def save_uploaded_video(upload_file: UploadFile) -> str:
        """
        Saves the uploaded file to disk and returns the unique video_id.
        """
        video_id = str(uuid.uuid4())
        file_path = f"static/uploads/{video_id}.mp4"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
            
        return video_id

    @staticmethod
    def extract_first_frame(video_id: str) -> str:
        """
        Reads the saved video, extracts the first frame, saves it as a JPEG, 
        and returns the public URL for the frontend.
        """
        video_path = f"static/uploads/{video_id}.mp4"
        frame_path = f"static/frames/{video_id}.jpg"
        
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            cv2.imwrite(frame_path, frame)
            return f"/static/frames/{video_id}.jpg"
            
        raise ValueError("Could not read the video file to extract the first frame.")