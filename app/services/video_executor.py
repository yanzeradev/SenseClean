import asyncio
import cv2
import numpy as np # NEEDED FOR SCALING
from app.database import SessionLocal
from app.repositories.video import VideoRepository
from app.services.task_manager import task_manager, JobStatus
from app.vision.pipeline import VideoPipeline
from app.vision.detectors.yolo_detector import YoloDetector
from app.vision.trackers.yolo_tracker import YoloTracker
from app.vision.analytics import ZoneAnalytics
from app.core.config import MODEL_PATH
# Import the schema to type hint the request
from app.schemas.video import ProcessVideoRequest

async def process_video_background(video_id: str, video_path: str, request_data: ProcessVideoRequest):
    db = SessionLocal()
    repo = VideoRepository(db)
    job = task_manager.get_job(video_id)
    if not job:
        db.close()
        return

    # Open video temporarily just to get its true resolution
    cap = cv2.VideoCapture(video_path)
    true_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    true_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    # 💥 SCALE CALCULATION (Fixing the Resolution Mismatch)
    # scale = true_video_size / frontend_canvas_size
    scale_x = true_width / request_data.frame_dimensions.width if request_data.frame_dimensions.width else 1
    scale_y = true_height / request_data.frame_dimensions.height if request_data.frame_dimensions.height else 1

    def scale_points(points: list) -> list:
        return [{'x': int(p['x'] * scale_x), 'y': int(p['y'] * scale_y)} for p in points]

    # Apply the scaling to the coordinates received from the frontend
    scaled_entrant_line = scale_points(request_data.entrant_line_points)
    scaled_passerby_line = scale_points(request_data.passerby_line_points)

    detector = YoloDetector(model_path=str(MODEL_PATH))
    tracker = YoloTracker(model_path=str(MODEL_PATH))
    
    # Inject the scaled lines into the Analytics engine
    analytics = ZoneAnalytics(
        entrant_line=scaled_entrant_line, 
        passerby_line=scaled_passerby_line, 
        in_side_direction=request_data.in_side
    )
    
    pipeline = VideoPipeline(video_source=video_path, detector=detector, tracker=tracker)
    current_frame = 0

    try:
        job["ready_event"].set()
        
        async for frame, tracks in pipeline.process():
            analytics.update(tracks)
            
            # --- Draw Lines on the Video (Visual Feedback) ---
            # Helper to draw lines
            def draw_polyline(img, points, color):
                if len(points) < 2: return
                for i in range(len(points) - 1):
                    p1 = (int(points[i]['x']), int(points[i]['y']))
                    p2 = (int(points[i+1]['x']), int(points[i+1]['y']))
                    cv2.line(img, p1, p2, color, 3)

            draw_polyline(frame, scaled_entrant_line, (0, 255, 0)) # Green for Entrants
            draw_polyline(frame, scaled_passerby_line, (0, 255, 255)) # Yellow for Passerbys
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