from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, get_db
from app.models import Base, Detection
from app.schemas import DetectionCreate, DetectionResponse
from app.api import detection, video

# command for creating tables in the database based on the models
Base.metadata.create_all(bind=engine)

# Instance of FastAPI
app = FastAPI(
    title = "My FastAPI Application",
    description = "API for system tracking and counting people",
    version = "1.0.0"
)

# Allowed origins for CORS
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    #"https://sensevision.com.br",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Endpoint to check if the API is working
@app.get("/health", tags=["Status"])
async def health_check():
    return {
        "status": "online",
        "project": "SenseVision API",
        "message": "API is up and running!"
    }

app.include_router(detection.router)
app.include_router(video.router)