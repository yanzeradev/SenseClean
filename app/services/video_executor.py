import asyncio
import cv2
import supervision as sv
import numpy as np # NEEDED FOR SCALING
from app.database import SessionLocal
from app.repositories.video import VideoRepository
from app.services.task_manager import task_manager, JobStatus
from app.vision.pipeline import VideoPipeline
from app.vision.detectors.yolo_detector import YoloDetector
from app.vision.trackers.yolo_tracker import YoloTracker
from app.vision.analytics import ZoneAnalytics
from app.core.config import MODEL_PATH
from app.schemas.video import ProcessVideoRequest
from app.services.report_service import ReportService
import os
import time

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
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0 # Get FPS for video writer
    cap.release()

    # --- Video Writer Setup (Saving the processed video) ---
    # --- Video Writer Setup (Saving the processed video) ---
    os.makedirs("static/output_videos", exist_ok=True)
    out_video_path = f"static/output_videos/{video_id}.mp4" # 💥 Mudamos para MP4
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') # 💥 Codec MP4V (MUITO mais rápido na CPU)
    out = cv2.VideoWriter(out_video_path, fourcc, fps, (true_width, true_height))
    
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
    
    analytics = ZoneAnalytics(
        entrant_line=scaled_entrant_line, 
        passerby_line=scaled_passerby_line, 
        in_side_direction=request_data.in_side
    )
    
    pipeline = VideoPipeline(video_source=video_path, detector=detector, tracker=tracker)
    
   # 💥 PINCÉIS PARA O VIDEO: Mesma estética Premium do Live_Manager
    box_annotator = sv.BoxAnnotator(thickness=2)
    label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=1)
    trace_annotator = sv.TraceAnnotator(thickness=2, trace_length=60, position=sv.Position.BOTTOM_CENTER)

    try:
        job["ready_event"].set()
        start_time = time.time() 
        frames_processados = 0
        
        async for frame, tracking_result in pipeline.process():
            
            tracks = tracking_result.get("analytics_data", [])
            detections = tracking_result.get("sv_detections") # Pega o objeto já tratado
            
            analytics.update(tracks)
            
            def draw_polyline(img, points, color):
                if len(points) < 2: return
                for i in range(len(points) - 1):
                    p1 = (int(points[i]['x']), int(points[i]['y']))
                    p2 = (int(points[i+1]['x']), int(points[i+1]['y']))
                    cv2.line(img, p1, p2, color, 3)

            draw_polyline(frame, scaled_entrant_line, (0, 255, 0)) 
            draw_polyline(frame, scaled_passerby_line, (0, 255, 255)) 

            # 💥 NOVA MÁGICA VISUAL MODERNIZADA PARA OS VÍDEOS
            if detections is not None and len(detections) > 0:
                
                # Efeito Vidro Transparente
                overlay = frame.copy()
                for bbox, class_id in zip(detections.xyxy, detections.class_id):
                    x1, y1, x2, y2 = map(int, bbox)
                    color = sv.ColorPalette.DEFAULT.by_idx(class_id).as_bgr()
                    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
                cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)

                # Bordas e Rastros
                frame = box_annotator.annotate(scene=frame, detections=detections)
                frame = trace_annotator.annotate(scene=frame, detections=detections)
                
                labels = [f"ID: {tracker_id}" for tracker_id in detections.tracker_id]
                frame = label_annotator.annotate(scene=frame, detections=detections, labels=labels)
            
            cv2.rectangle(frame, (10, 10), (250, 100), (0, 0, 0), -1)
            cv2.putText(frame, f"Entrantes: {analytics.counts['entrant']}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            out.write(frame)
            success, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60]) # Reduza a qualidade pra 60 pra ficar mais leve!
            if success:
                await job["queue"].put(buffer.tobytes())
            
            # 💥 Cálculo de FPS em tempo real a cada 30 frames
            frames_processados += 1
            if frames_processados % 30 == 0:
                fps_atual = frames_processados / (time.time() - start_time)
                print(f"🚀 VELOCIDADE DA IA: {fps_atual:.2f} FPS")

            await asyncio.sleep(0.001)

        # --- 💥 FINALIZATION PHASE ---
        out.release() # Save the physical video
        
        # 1. Compute Majority Voting
        final_results = analytics.get_final_results()
        
        # 2. Generate Excel Report
        report_url = ReportService.generate_excel(video_id, final_results)
        
        # 3. Update active memory
        task_manager.set_status(video_id, JobStatus.COMPLETED)
        
        # 4. Persist everything to the Database!
        # The results JSON natively saves inside the SQLAlchemy column
        repo.save_results(
            video_id=video_id, 
            processed_path=f"/static/output_videos/{video_id}.webm", 
            results=final_results
        )

    except Exception as e:
        print(f"Error processing video {video_id}: {e}")
        out.release()
        task_manager.set_status(video_id, JobStatus.FAILED)
        repo.update_status(video_id, "failed")
        
    finally:
        await job["queue"].put(None)
        db.close()