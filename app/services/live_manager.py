import asyncio
import cv2
import time
import os
import json
import requests
import subprocess
import numpy as np
import traceback
from datetime import datetime
from typing import Dict, Any

from app.database import SessionLocal
from app.repositories.device import DeviceRepository
from app.repositories.video import VideoRepository
from app.vision.analytics import ZoneAnalytics
from app.vision.interfaces import BaseDetector, BaseTracker

# Filas de memória para transmissão MJPEG ao Frontend
monitor_queues: Dict[int, asyncio.Queue] = {} 
active_tasks: Dict[int, asyncio.Task] = {}
stop_signals: Dict[int, asyncio.Event] = {} 

async def restart_camera(device_id: int):
    """
    Sinaliza a parada de uma câmera. O Scheduler a reiniciará no próximo ciclo.
    """
    if device_id in stop_signals:
        print(f"🔄 Reiniciando Câmera {device_id}...")
        stop_signals[device_id].set()
        
        if device_id in active_tasks:
            try:
                await asyncio.wait_for(active_tasks[device_id], timeout=2.0)
            except: pass
            del active_tasks[device_id]
        
        if device_id in stop_signals: del stop_signals[device_id]
        if device_id in monitor_queues: del monitor_queues[device_id]

def get_stream_resolution(rtsp_url: str) -> tuple[int, int]:
    """Descobre a resolução nativa do stream RTSP usando FFprobe."""
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", rtsp_url]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        if output:
            parts = output.split(',')
            if len(parts) >= 2:
                w, h = int(parts[0]), int(parts[1])
                if w > 0 and h > 0: return w, h
    except: pass
    return 1920, 1080 # Fallback Full HD

async def scheduler_loop(detector: BaseDetector, tracker: BaseTracker):
    """
    O Coração do Self-Healing. Roda a cada 3 segundos verificando quem deve estar ligado.
    """
    print("⏰ Scheduler de Câmeras Iniciado (Modo Self-Healing).")
    while True:
        try:
            # 1. Limpeza de tarefas mortas (Câmeras que caíram por erro de rede)
            for dev_id in list(active_tasks.keys()):
                task = active_tasks[dev_id]
                if task.done():
                    if dev_id in active_tasks: del active_tasks[dev_id]
                    if dev_id in stop_signals: del stop_signals[dev_id]
                    if dev_id in monitor_queues: del monitor_queues[dev_id]
                    print(f"♻️ Câmera {dev_id} limpa da memória e pronta para reconexão.")

            # 2. Verificação de Agendamento no Banco de Dados
            db = SessionLocal()
            device_repo = DeviceRepository(db)
            devices = [d for d in device_repo.get_all() if d.is_configured]
            
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")
            
            for dev in devices:
                if not dev.processing_start_time or not dev.processing_end_time or not dev.lines_config:
                    continue
                
                start, end = dev.processing_start_time, dev.processing_end_time
                is_time = start <= current_time_str < end
                
                # INICIAR
                if is_time and dev.id not in active_tasks:
                    print(f"▶️ Iniciando Câmera: {dev.name}")
                    stop_event = asyncio.Event()
                    stop_signals[dev.id] = stop_event
                    monitor_queues[dev.id] = asyncio.Queue(maxsize=2)
                    
                    task = asyncio.create_task(
                        run_live_camera_ffmpeg(dev.id, dev.rtsp_url, dev.lines_config, stop_event, detector, tracker)
                    )
                    active_tasks[dev.id] = task

                # PARAR
                elif not is_time and dev.id in active_tasks:
                    print(f"⏹️ Parando Câmera: {dev.name} (Fora de Horário)")
                    await restart_camera(dev.id)

            db.close()
        except Exception as e:
            print(f"❌ Erro no Scheduler: {e}")
        
        await asyncio.sleep(3)

async def run_live_camera_ffmpeg(device_id: int, rtsp_url: str, lines_config: dict, stop_event: asyncio.Event, detector: BaseDetector, tracker: BaseTracker):
    """
    O Processo isolado que gerencia 1 câmera ao vivo.
    """
    db = SessionLocal()
    video_repo = VideoRepository(db)
    
    # Criamos um "Video" no banco para registrar as estatísticas da sessão ao vivo
    video_id = f"live_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    process = None
    
    try:
        # Configuração do Pipeline e do Go2RTC
        stream_name = f"camera_{device_id}"
        go2rtc_api = "http://127.0.0.1:1984/api/streams"
        
        # 💥 TRADUÇÃO DE IP PARA O DOCKER
        rtsp_for_go2rtc = rtsp_url.replace("127.0.0.1", "host.docker.internal").replace("localhost", "host.docker.internal")
        local_rtsp = rtsp_url 
        
        try:
            # Envia a URL traduzida para o go2rtc
            requests.put(go2rtc_api, params={"src": rtsp_for_go2rtc, "name": stream_name}, timeout=2)
        except Exception: 
            print("⚠️ go2rtc não respondeu. Consumindo vídeo direto da câmera.")


        # Inicializa o registro no banco de dados para os gráficos
        video_record = video_repo.create(original_video_path=local_rtsp)
        video_record.id = video_id
        db.commit()

        WIDTH, HEIGHT = get_stream_resolution(local_rtsp)
        FRAME_SIZE = WIDTH * HEIGHT * 3 

        print(f"🔌 Ingestão FFMPEG: {local_rtsp} ({WIDTH}x{HEIGHT})")
        
        if WIDTH == 0 or HEIGHT == 0: return

        command = ['ffmpeg', '-rtsp_transport', 'tcp', '-i', local_rtsp, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-r', '15', '-an', '-sn', '-y', '-']
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8)

        # --- A MÁGICA DA ARQUITETURA LIMPA ---
        # Instanciamos o nosso Motor Matemático da Fase 1, injetando as linhas do banco
        entrant_line = lines_config.get('entrant', [])
        passerby_line = lines_config.get('passerby', [])
        in_side = lines_config.get('in_side', 'right')
        
        analytics = ZoneAnalytics(entrant_line, passerby_line, in_side)
        
        t0 = time.time()
        last_save = time.time()
        
        while not stop_event.is_set():
            try:
                # Leitura síncrona do Pipe FFMPEG isolada numa Thread
                raw_frame = await asyncio.to_thread(process.stdout.read, FRAME_SIZE)
            except ValueError:
                break 
            
            if len(raw_frame) != FRAME_SIZE:
                await asyncio.sleep(0.5)
                continue

            frame = np.frombuffer(raw_frame, np.uint8).reshape((HEIGHT, WIDTH, 3)).copy()

            # --- PROCESSAMENTO IA OFF-LOADED ---
            detections = await asyncio.to_thread(detector.detect, frame)
            tracks = await asyncio.to_thread(tracker.update, detections, frame)
            
            # --- ATUALIZAÇÃO DA LÓGICA DE NEGÓCIO ---
            analytics.update(tracks)

            # --- DESENHO EM TELA (Visuals) ---
            for track in tracks:
                x1, y1, x2, y2 = map(int, track["bbox"])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"ID: {track['track_id']}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Desenha as linhas físicas
            if len(entrant_line) > 1:
                pts = np.array([ [p['x'], p['y']] for p in entrant_line ], np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], False, (0, 255, 0), 3)
            
            if len(passerby_line) > 1:
                pts = np.array([ [p['x'], p['y']] for p in passerby_line ], np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], False, (0, 255, 255), 3)

            # Placar Live
            cv2.rectangle(frame, (10, 10), (250, 100), (0, 0, 0), -1)
            cv2.putText(frame, f"Entrantes: {analytics.counts['entrant']}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(frame, f"Passantes: {analytics.counts['passerby']}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            # --- STREAMING PARA O REACT ---
            if device_id in monitor_queues:
                q = monitor_queues[device_id]
                if q.full():
                    try: q.get_nowait()
                    except: pass
                
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                if ret: await q.put(buffer.tobytes())

            # --- SALVAMENTO NO BANCO (A CADA 2 SEGUNDOS) ---
            if time.time() - last_save > 2:
                try:
                    # Capturamos o JSON limpo através da função interna do ZoneAnalytics
                    current_results = analytics.get_final_results()
                    with SessionLocal() as db_save:
                        repo_save = VideoRepository(db_save)
                        repo_save.update_status(video_id, "live_processing")
                        
                        vid = repo_save.get_by_id(video_id)
                        vid.results = current_results
                        db_save.commit()
                except Exception as e:
                    print(f"Erro ao salvar estatísticas: {e}")
                last_save = time.time()
            
            await asyncio.sleep(0.001) # Yield to event loop

    except Exception as e:
        print(f"❌ Erro fatal Câmera {device_id}: {traceback.format_exc()}")
    finally:
        if process: process.terminate()
        db.close()
        if device_id in monitor_queues: del monitor_queues[device_id]
        
        try:
            with SessionLocal() as db_final:
                VideoRepository(db_final).update_status(video_id, "done")
        except: pass
        print(f"✅ Câmera {device_id} Desconectada.")