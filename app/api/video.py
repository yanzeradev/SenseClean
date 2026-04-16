from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict

from app.database import get_db
from app.repositories.video import VideoRepository
from app.services.task_manager import task_manager, JobStatus
from app.services.video_executor import process_video_background
from app.services.file_service import FileService # NEW IMPORT
from app.schemas.video import ProcessVideoRequest

router = APIRouter(
    prefix="/videos",
    tags=["Video Processing"],
)

# --- NEW SCHEMAS FOR CANVAS COORDINATES ---
class FrameDimensions(BaseModel):
    width: int
    height: int

class ProcessVideoRequest(BaseModel):
    video_id: str
    in_side: str  # 'left' or 'right'
    entrant_line_points: List[Dict[str, float]]
    passerby_line_points: List[Dict[str, float]]
    frame_dimensions: FrameDimensions

@router.get("/")
async def list_videos(db: Session = Depends(get_db)):
    """
    Fetches the history of all processed videos.
    """
    repo = VideoRepository(db)
    return repo.get_all()

# --- NEW UPLOAD ENDPOINT ---
@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Receives a video, saves it, extracts the first frame, and returns the data for the UI Canvas.
    """
    try:
        video_id = FileService.save_uploaded_video(file)
        first_frame_url = FileService.extract_first_frame(video_id)
        
        return {
            "video_id": video_id,
            "video_path": f"static/uploads/{video_id}.mp4",
            "first_frame_url": first_frame_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- UPDATED PROCESS ENDPOINT ---
@router.post("/process")
async def start_video_processing(
    request: ProcessVideoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    repo = VideoRepository(db)
    
    # We reconstruct the physical path using the ID
    video_path = f"static/uploads/{request.video_id}.mp4"
    
    # Save to database (Updating your repo logic slightly to use the ID)
    video_record = repo.create(original_video_path=video_path)
    # Force the DB ID to match our physical file ID to avoid confusion
    video_record.id = request.video_id
    db.commit()
    
    task_manager.create_job(video_id=video_record.id)
    task_manager.set_status(video_id=video_record.id, status=JobStatus.PROCESSING)
    repo.update_status(video_id=video_record.id, new_status="processing")
    
    # Send all the dynamic data to the background task!
    background_tasks.add_task(
        process_video_background, 
        video_id=video_record.id, 
        video_path=video_path, 
        request_data=request # Passing the full request object
    )
    
    return {
        "message": "Video processing started.",
        "video_id": video_record.id,
        "status": "processing"
    }

@router.get("/{video_id}/status")
async def get_video_status(video_id: str):
    job = task_manager.get_job(video_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found in active memory.")
        
    return {
        "video_id": video_id,
        "status": job["status"],
        "progress": job["progress"]
    }

# 💥 THE CONSUMER!
@router.get("/{video_id}/stream")
async def stream_video(video_id: str):
    """
    Streams the video frames from RAM via HTTP Multipart.
    """
    job = task_manager.get_job(video_id)
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found.")

    async def frame_generator():
        # Wait until the background task signals it has initialized OpenCV
        await job["ready_event"].wait()
        
        while True:
            # Read from the Queue
            frame_bytes = await job["queue"].get()
            
            # A None token means the processing finished
            if frame_bytes is None:
                break
                
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    # Return a continuous stream using the specific boundary format browsers understand
    return StreamingResponse(frame_generator(), media_type='multipart/x-mixed-replace; boundary=frame')