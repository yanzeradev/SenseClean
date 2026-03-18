from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from app.vision import tracker_video
import shutil
from app.core import MODEL_PATH
import uuid
from pathlib import Path

router = APIRouter(
    prefix="/video",
    tags=["Video Stream"],
)

@router.post("/upload")
def upload_video(file: UploadFile = File(...)):
    unique_id = uuid.uuid4().hex
    path_temp = f"temp_{unique_id}_{file.filename}"

    with open(path_temp, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)


    return {"status": "sucesso", "video_path": path_temp}

@router.get("/stream")
def stream_video(video_path: str):

    return StreamingResponse(
        tracker_video(video_path, MODEL_PATH),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )