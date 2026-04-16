from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.models.video import Video

class VideoRepository:
    """
    Repository pattern to isolate database operations for the Video entity.
    Keeps SQLAlchemy queries out of the FastAPI routing layer.
    """
    
    def __init__(self, db_session: Session):
        """
        Injects the database session into the repository.
        """
        self.db = db_session

    def get_by_id(self, video_id: str) -> Optional[Video]:
        """Fetches a video by its UUID."""
        return self.db.query(Video).filter(Video.id == video_id).first()

    def create(self, original_video_path: str) -> Video:
        """Creates a new video record in the database."""
        db_video = Video(
            original_video_path=original_video_path,
            status="pending"
        )
        self.db.add(db_video)
        self.db.commit()
        self.db.refresh(db_video)
        return db_video

    def update_status(self, video_id: str, new_status: str) -> Optional[Video]:
        """Updates only the status of the video."""
        db_video = self.get_by_id(video_id)
        if db_video:
            db_video.status = new_status
            self.db.commit()
            self.db.refresh(db_video)
        return db_video

    def save_results(self, video_id: str, processed_path: str, results: Dict[str, Any]) -> Optional[Video]:
        """Saves the final output path and the analytical results."""
        db_video = self.get_by_id(video_id)
        if db_video:
            db_video.processed_video_path = processed_path
            db_video.results = results
            db_video.status = "completed"
            self.db.commit()
            self.db.refresh(db_video)
        return db_video
    
    def get_all(self) -> list[Video]:
        """Returns all videos ordered by newest first."""
        return self.db.query(Video).order_by(Video.created_at.desc()).all()