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
live_frames: Dict[int, bytes] = {}
active_tasks: Dict[int, asyncio.Task] = {}
stop_signals: Dict[int, asyncio.Event] = {} 
latest_frames: Dict[int, bytes] = {}

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
        if device_id in live_frames: del live_frames[device_id] 

async def get_stream_resolution(rtsp_url: str) -> tuple[int, int]:
    """Descobre a resolução nativa de forma assíncrona para não travar o backend."""
    try:
        # 💥 Executa o FFprobe sem bloquear o loop principal
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0", 
            "-show_entries", "stream=width,height", "-of", "csv=p=0", 
            rtsp_url
        ]
        
        # Usamos asyncio.create_subprocess_exec para não travar
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Timeout de 5 segundos: se a câmera não responder a resolução, abortamos
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        output = stdout.decode().strip()
        
        if output:
            parts = output.split(',')
            if len(parts) >= 2:
                w, h = int(parts[0]), int(parts[1])
                if w > 0 and h > 0: return w, h
    except Exception as e:
        print(f"⚠️ Não foi possível obter resolução de {rtsp_url}: {e}")
        
    return 1280, 720 # Fallback HD (mais leve que Full HD para evitar novos travamentos)

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
                    if dev_id in live_frames: del live_frames[dev_id]
                    print(f"♻️ Câmera {dev_id} limpa da memória e pronta para reconexão.")

            # 2. Verificação de Agendamento no Banco de Dados
            db = SessionLocal()
            device_repo = DeviceRepository(db)
            devices = [d for d in device_repo.get_all_system_devices() if d.is_configured]
            
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")
            
            for dev in devices:
                if not dev.processing_start_time or not dev.processing_end_time or not dev.lines_config:
                    continue
                
                start, end = dev.processing_start_time, dev.processing_end_time
                
                if start <= end:
                    # Turno normal (ex: 08:00 às 18:00)
                    is_time = start <= current_time_str < end
                else:
                    # Turno de madrugada (ex: 18:00 às 08:00)
                    is_time = current_time_str >= start or current_time_str < end
                
                # INICIAR
                if is_time and dev.id not in active_tasks:
                    print(f"▶️ Iniciando Câmera: {dev.name}")
                    stop_event = asyncio.Event()
                    stop_signals[dev.id] = stop_event
                    
                    task = asyncio.create_task(
                        run_live_camera(dev.id, dev.rtsp_url, dev.lines_config, stop_event, tracker)
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

async def run_live_camera(device_id: int, rtsp_url: str, lines_config: dict, stop_event: asyncio.Event, tracker: BaseTracker):
    """
    O Motor inspirado no SenseOpen: Usa OpenCV puro e processa os trackers de forma eficiente.
    """
    db = SessionLocal()
    from app.models.video import Video
    from app.repositories.device import DeviceRepository
    
    dev = DeviceRepository(db).get_by_id(device_id)
    user_id = dev.user_id if dev else None
    
    video_id = f"live_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    nova_sessao = Video(id=video_id, original_video_path=f"Live Stream Cam {device_id}", status="live_processing", user_id=user_id)
    db.add(nova_sessao)
    db.commit()

    try:
        # 1. TRADUÇÃO GO2RTC
        stream_name = f"camera_{device_id}"
        rtsp_for_go2rtc = rtsp_url.replace("go2rtc", "host.docker.internal").replace("localhost", "host.docker.internal")
        local_rtsp = f"rtsp://go2rtc:8554/{stream_name}"
        
        try:
            requests.put("http://go2rtc:1984/api/streams", params={"src": rtsp_for_go2rtc, "name": stream_name}, timeout=3)
        except Exception: 
            local_rtsp = rtsp_url

        print(f"🔌 Ingestão OpenCV: {local_rtsp}")

        # 2. INSTÂNCIA OPENCV (Estilo SenseOpen)
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        cap = cv2.VideoCapture(local_rtsp)
        # O segredo para não atrasar a imagem ao vivo: Buffer minúsculo
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        entrant_line = lines_config.get('entrant', [])
        passerby_line = lines_config.get('passerby', [])
        in_side = lines_config.get('in_side', 'right')
        analytics = ZoneAnalytics(entrant_line, passerby_line, in_side)
        
        last_save = time.time()
        last_snap = 0
        frame_count = 0
        
        while not stop_event.is_set():
            # Leitura assíncrona do OpenCV
            ret, frame = await asyncio.to_thread(cap.read)
            
            if not ret:
                print(f"⚠️ Perda de sinal na câmera {device_id}. Reconectando...")
                await asyncio.sleep(2)
                break # Quebra o loop, o scheduler vai limpar a memória e reconectar sozinho!
            
            # Pula alguns frames para manter 15 FPS (suave o suficiente pro Tracker não perder a pessoa, leve pra CPU)
            frame_count += 1
            if frame_count % 2 != 0:
                continue

            # Snapshot Cache (Sem travar a CPU)
            if time.time() - last_snap > 1.0:
                ret_clean, buffer_clean = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                if ret_clean: latest_frames[device_id] = buffer_clean.tobytes()
                last_snap = time.time()

           # --- PROCESSAMENTO IA (Agora sim, igual ao SenseOpen!) ---
            tracks = await asyncio.to_thread(tracker.update, None, frame)
            
            # Atualiza regras de cruzamento
            analytics.update(tracks)

            if len(tracks) > 0:
                print(f"👀 CAM {device_id} Vendo {len(tracks)} pessoa(s) | Bounding Box do ID {tracks[0]['track_id']}: {tracks[0]['bbox']}")

            # --- DESENHO EM TELA ---
            for track in tracks:
                x1, y1, x2, y2 = map(int, track["bbox"])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"ID: {track['track_id']} ({track.get('class_id', '')})", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            if len(entrant_line) > 1:
                pts = np.array([ [p['x'], p['y']] for p in entrant_line ], np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], False, (0, 255, 0), 3)
            
            if len(passerby_line) > 1:
                pts = np.array([ [p['x'], p['y']] for p in passerby_line ], np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], False, (0, 255, 255), 3)

            cv2.rectangle(frame, (10, 10), (250, 100), (0, 0, 0), -1)
            cv2.putText(frame, f"Entrantes: {analytics.counts['entrant']}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(frame, f"Passantes: {analytics.counts['passerby']}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            # --- STREAM MJPEG PARA DASHBOARD ---
            ret_live, buffer_live = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            if ret_live: 
                live_frames[device_id] = buffer_live.tobytes()

            # --- SALVAMENTO NO BANCO ---
            if time.time() - last_save > 2:
                try:
                    current_results = analytics.get_final_results()
                    with SessionLocal() as db_save:
                        repo_save = VideoRepository(db_save)
                        repo_save.update_status(video_id, "live_processing")
                        vid = repo_save.get_by_id(video_id)
                        if vid:
                            vid.results = current_results
                            db_save.commit()
                except Exception as e:
                    print(f"Erro ao salvar estatísticas: {e}")
                last_save = time.time()
            
            await asyncio.sleep(0.001)

    except Exception as e:
        print(f"❌ Erro fatal Câmera {device_id}: {traceback.format_exc()}")
    finally:
        if 'cap' in locals(): cap.release()
        db.close()
        if device_id in live_frames: del live_frames[device_id] # 💥 Limpa ao sair
        if device_id in latest_frames: del latest_frames[device_id]
        
        try:
            with SessionLocal() as db_final:
                VideoRepository(db_final).update_status(video_id, "done")
        except: pass
        print(f"✅ Câmera {device_id} Encerrada.")