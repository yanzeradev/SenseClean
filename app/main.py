import os
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # NEW IMPORT
from app.database import engine, get_db
from app.models import Base
from app.api import detection, video

# Create required directories for static files
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/frames", exist_ok=True)
os.makedirs("static/output_videos", exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SenseClean API",
    description="API for tracking and counting people",
    version="1.0.0"
)

origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/health", tags=["Status"])
async def health_check():
    return {"status": "online", "message": "API is up and running!"}

app.include_router(detection.router)
app.include_router(video.router)