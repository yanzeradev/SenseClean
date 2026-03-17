import cv2
from ultralytics import YOLO

def tracker(video_path, model_path):
    print("Loading model...")
    model = YOLO(model_path)

    print("Opening video...")
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Error: Could not open video.")
        return
    
    print("Processing video...")
    while True:
        ret, frame = cap.read()

        if not ret:
            print("End of video or error reading frame.")
            break

        results = model.track(frame, conf=0.5, persist=True, tracker="botsort.yaml")

        result = results[0]

        frame_with_boxes = result.plot()

        if result.boxes is not None and result.boxes.id is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            tracker_ids = result.boxes.id.int().cpu().numpy()
            scores = result.boxes.conf.cpu().numpy()

            for box, track_id, score in zip(boxes, tracker_ids, scores):
                x1, y1, x2, y2 = map(float, box)

                json_data = {
                    "cam_id": 1,
                    "bbox": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                    "score": round(float(score), 2),
                    "track_id": int(track_id)
                }

                print(f"Detection: {json_data}")

        cv2.imshow('SenseVision', frame_with_boxes)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Exiting video processing.")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    video_path = "test.mp4"
    model_path = "model_gender.pt"
    tracker(video_path, model_path)