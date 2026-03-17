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

        results = model(frame, conf=0.5)
        frame_with_boxes = results[0].plot()

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