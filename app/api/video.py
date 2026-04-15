from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse # NEW IMPORT
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.repositories.video import VideoRepository
from app.services.task_manager import task_manager, JobStatus

# Import our new executor!
from app.services.video_executor import process_video_background

router = APIRouter(
    prefix="/videos",
    tags=["Video Processing"],
)

class ProcessVideoRequest(BaseModel):
    video_path: str
    in_side: str

@router.post("/process")
async def start_video_processing(
    request: ProcessVideoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    repo = VideoRepository(db)
    video_record = repo.create(original_video_path=request.video_path)
    
    task_manager.create_job(video_id=video_record.id)
    task_manager.set_status(video_id=video_record.id, status=JobStatus.PROCESSING)
    repo.update_status(video_id=video_record.id, new_status="processing")
    
    # 💥 ACTION! Send to background task
    background_tasks.add_task(process_video_background, video_record.id, request.video_path, request.in_side)
    
    return {
        "message": "Video processing started successfully.",
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