import asyncio
import cv2
from app.database import SessionLocal
from app.repositories.video import VideoRepository
from app.services.task_manager import task_manager, JobStatus
from app.vision.pipeline import VideoPipeline
from app.vision.detectors.yolo_detector import YoloDetector
from app.vision.trackers.yolo_tracker import YoloTracker
from app.vision.analytics import ZoneAnalytics
from app.core.config import MODEL_PATH

async def process_video_background(video_id: str, video_path: str, in_side: str):
    """
    The main background task that acts as the Producer.
    It runs the AI pipeline and pushes processed frames to the queue.
    """
    # 1. Create a fresh DB Session dedicated to this background task
    db = SessionLocal()
    repo = VideoRepository(db)
    
    # 2. Retrieve the active job state
    job = task_manager.get_job(video_id)
    if not job:
        db.close()
        return

    # 3. Initialize Vision Components
    detector = YoloDetector(model_path=str(MODEL_PATH))
    tracker = YoloTracker(model_path=str(MODEL_PATH))
    
    # MOCK LINES: In the future, these will come from the user request (Frontend)
    entrant_line = [{'x': 100, 'y': 300}, {'x': 500, 'y': 300}]
    passerby_line = [{'x': 100, 'y': 150}, {'x': 500, 'y': 150}]
    
    analytics = ZoneAnalytics(entrant_line, passerby_line, in_side_direction=in_side)
    pipeline = VideoPipeline(video_source=video_path, detector=detector, tracker=tracker)
    
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    current_frame = 0

    try:
        # Signal that processing has officially started
        job["ready_event"].set()
        
        # 💥 CHANGE 1: Use 'async for' to consume the AsyncGenerator
        async for frame, tracks in pipeline.process():
            # Update analytics with current tracks
            analytics.update(tracks)
            
            # --- Draw results on the frame ---
            for track in tracks:
                x1, y1, x2, y2 = map(int, track["bbox"])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"ID: {track['track_id']}", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Draw score
            cv2.putText(frame, f"Entrants: {analytics.counts['entrant']}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            cv2.putText(frame, f"Passerby: {analytics.counts['passerby']}", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            # Encode frame to JPEG
            success, buffer = cv2.imencode('.jpg', frame)
            if success:
                await job["queue"].put(buffer.tobytes())
            
            # Update progress
            current_frame += 1
            if total_frames > 0 and current_frame % 5 == 0:
                task_manager.update_progress(video_id, (current_frame / total_frames) * 100)

            # 💥 CHANGE 2: The "Breathing Room"
            # Explicitly yields control to the event loop so it can send the video stream to the browser
            await asyncio.sleep(0.001)

        # Processing finished successfully
        task_manager.set_status(video_id, JobStatus.COMPLETED)
        repo.save_results(video_id, processed_path="path/to/save.mp4", results=analytics.counts)

    except Exception as e:
        print(f"Error processing video {video_id}: {e}")
        task_manager.set_status(video_id, JobStatus.FAILED)
        repo.update_status(video_id, "failed")
        
    finally:
        # Put a None token in the queue to tell the consumer the video ended
        await job["queue"].put(None)
        db.close()