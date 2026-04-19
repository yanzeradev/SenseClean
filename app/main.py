import os
import asyncio # NEW IMPORT
from contextlib import asynccontextmanager # NEW IMPORT
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base
from app.api import detection, video, device, auth
from app.services import live_manager # IMPORT LIVE MANAGER
from app.vision.detectors.yolo_detector import YoloDetector
from app.vision.trackers.yolo_tracker import YoloTracker
from app.core.config import MODEL_PATH

os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/frames", exist_ok=True)
os.makedirs("static/output_videos", exist_ok=True)
os.makedirs("static/reports", exist_ok=True)

Base.metadata.create_all(bind=engine)

# --- THE LIFESPAN (Inicia o Scheduler) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Iniciando Motor de IA e Scheduler...")
    try:
        # Instancia os modelos IA globais uma única vez
        detector = YoloDetector(model_path=str(MODEL_PATH))
        tracker = YoloTracker(model_path=str(MODEL_PATH))
        
        # Dispara a tarefa do Scheduler de câmeras ao vivo em background
        asyncio.create_task(live_manager.scheduler_loop(detector, tracker))
    except Exception as e:
        print(f"❌ Erro ao iniciar IA: {e}")
    
    yield # O servidor fica rodando aqui
    
    print("🛑 Desligando servidor...")

# Passamos o lifespan para o FastAPI
app = FastAPI(
    title="SenseClean API", 
    lifespan=lifespan,
    root_path="/api"  
)

origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static/", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(detection.router)
app.include_router(video.router)
app.include_router(device.router)

@app.get("/health", tags=["Status"])
async def health_check():
    return {"status": "online", "message": "API is up and running!"}

app.include_router(detection.router)
app.include_router(video.router)