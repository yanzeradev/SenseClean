from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Detection
from app.schemas import DetectionCreate, DetectionResponse

router = APIRouter(
    prefix="/detection",
    tags=["Detection"],
)

@router.post("/", response_model=DetectionResponse)
def create_detection(detection: DetectionCreate, db: Session = Depends(get_db)):
    
    db_detection = Detection(**detection.model_dump())

    db.add(db_detection)
    db.commit()
    db.refresh(db_detection)

    return db_detection