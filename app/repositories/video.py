from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.models.video import Video
from datetime import date

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

    def create(self, original_video_path: str, user_id: int) -> Video:
        db_video = Video(
            original_video_path=original_video_path,
            status="pending",
            user_id=user_id 
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
    
    def get_all(self, user_id: int) -> list[Video]:
        """Returns all videos for a specific user."""
        return self.db.query(Video).filter(Video.user_id == user_id).order_by(Video.created_at.desc()).all()


    def get_or_create_daily_session(self, device_id: int, user_id: int) -> Video:
        """
        Lógica Enterprise: Busca a sessão de hoje para esta câmera. 
        Se não existir, cria uma nova. Se existir, reaproveita!
        """
        today = date.today()
        
        session_id = f"daily_cam{device_id}_{today.strftime('%Y%m%d')}"
        
        existing_session = self.get_by_id(session_id)
        
        if existing_session:
            existing_session.status = "live_processing"
            self.db.commit()
            return existing_session
            
        new_session = Video(
            id=session_id,
            original_video_path=f"Live Stream Cam {device_id}",
            status="live_processing",
            user_id=user_id,
            reference_date=today,
            results={
                "entrantes": {"Homem": 0, "Mulher": 0, "NaoIdentificado": 0, "Total": 0},
                "passantes": {"Homem": 0, "Mulher": 0, "NaoIdentificado": 0, "Total": 0}
            }
        )
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)
        
        return new_session