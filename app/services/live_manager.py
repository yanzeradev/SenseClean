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
from collections import defaultdict, deque
import supervision as sv
import math
import threading
from queue import Queue, Empty

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
heatmap_data: Dict[int, list] = {}

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

def _camera_reader_worker(rtsp_url: str, cam_data: dict, stop_event: asyncio.Event):
    """
    Trabalhador invisível. Tenta conectar e atualiza a foto na memória na velocidade da rede.
    """
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|max_delay;5000000"
    cap = None
    
    while not stop_event.is_set():
        # Se a câmera não existe ou caiu, tenta (re)conectar de fundo
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not cap.isOpened():
                cam_data["online"] = False
                time.sleep(2) # Espera 2s antes de tentar de novo
                continue
                
        ret, frame = cap.read()
        
        # Se a rede oscilar e falhar o frame
        if not ret:
            cam_data["online"] = False
            cap.release()
            cap = None
            time.sleep(1)
            continue

        # MÁGICA: Substitui a foto instantaneamente na memória RAM
        cam_data["frame"] = frame
        cam_data["online"] = True
        
    if cap:
        cap.release()


async def run_live_camera(device_id: int, rtsp_url: str, lines_config: dict, stop_event: asyncio.Event, tracker: BaseTracker):
    """
    O Motor inspirado no SenseOpen: Usa OpenCV puro e processa os trackers de forma eficiente.
    """
    db = SessionLocal()
    from app.models.video import Video
    from app.repositories.device import DeviceRepository
    
    dev = DeviceRepository(db).get_by_id(device_id)
    user_id = dev.user_id if dev else None
    
    repo_inicial = VideoRepository(db)
    sessao_diaria = repo_inicial.get_or_create_daily_session(device_id, user_id)
    video_id = sessao_diaria.id
    
    bagagem_resultados = sessao_diaria.results or {
        "entrantes": {"Homem": 0, "Mulher": 0, "NaoIdentificado": 0, "Total": 0},
        "passantes": {"Homem": 0, "Mulher": 0, "NaoIdentificado": 0, "Total": 0},
        "total_geral": {"Homem": 0, "Mulher": 0, "NaoIdentificado": 0, "Total": 0}
    }
    bagagem_entrantes = bagagem_resultados.get("entrantes", {}).get("Total", 0)
    bagagem_passantes = bagagem_resultados.get("passantes", {}).get("Total", 0)

    try:
        # 1. TRADUÇÃO GO2RTC
        stream_name = f"camera_{device_id}"
        rtsp_for_go2rtc = rtsp_url.replace("go2rtc", "host.docker.internal").replace("localhost", "host.docker.internal")
        local_rtsp = f"rtsp://go2rtc:8554/{stream_name}"
        
        try:
            # Jogamos o Requests para uma thread para ele não travar o FastAPI!
            await asyncio.to_thread(
                requests.put, "http://go2rtc:1984/api/streams", 
                params={"src": rtsp_for_go2rtc, "name": stream_name}, timeout=2
            )
        except Exception: 
            local_rtsp = rtsp_url

        print(f"🔌 Ingestão de Memória: {local_rtsp}")

        # 💥 O FIM DAS FILAS: Usamos um dicionário compartilhado simples e à prova de falhas
        cam_data = {"frame": None, "online": False}
        reader_thread = threading.Thread(
            target=_camera_reader_worker, 
            args=(local_rtsp, cam_data, stop_event),
            daemon=True
        )
        reader_thread.start()

        entrant_line = lines_config.get('entrant', [])
        passerby_line = lines_config.get('passerby', [])
        in_side = lines_config.get('in_side', 'right')
        analytics = ZoneAnalytics(entrant_line, passerby_line, in_side)
        analytics.counts["entrant"] = bagagem_entrantes
        analytics.counts["passerby"] = bagagem_passantes
        
        last_save = time.time()
        last_snap = 0
        frame_count = 0
        last_tracks = {"analytics_data": [], "sv_detections": None} 
        
        box_annotator = sv.BoxAnnotator(thickness=2)
        label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=1)
        
        mask_annotator = sv.MaskAnnotator()
        
        # Lógica Opcional do PolygonZone
        polygon_points = lines_config.get('polygon', [])
        zone = None
        zone_annotator = None
        
        if len(polygon_points) >= 3:
            # Converte as coordenadas do Frontend para o Supervision
            poly_arr = np.array([[p['x'], p['y']] for p in polygon_points], np.int32)
            zone = sv.PolygonZone(polygon=poly_arr)
            zone_annotator = sv.PolygonZoneAnnotator(zone=zone, color=sv.Color.from_hex("#A855F7"), thickness=2)
        
        track_history = defaultdict(lambda: deque(maxlen=150)) 
        dwell_timers = {} 

        while not stop_event.is_set():
            
            # Se a câmera caiu, o FastAPI apenas "dorme" por meio segundo e deixa o site funcionar!
            if not cam_data["online"] or cam_data["frame"] is None:
                await asyncio.sleep(0.5)
                continue
                
            # Pega uma cópia da foto mais fresca disponível na memória
            frame = cam_data["frame"].copy()

            # Snapshot Cache (Sem travar a CPU)
            if time.time() - last_snap > 1.0:
                ret_clean, buffer_clean = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                if ret_clean: latest_frames[device_id] = buffer_clean.tobytes()
                last_snap = time.time()

            # 💥 ADEUS MARCHA_IA: Como o frame na memória é sempre o do exato milissegundo,
            # não precisamos mais calcular lixo de rede. A IA roda no talo do que a GPU aguentar!
            tracking_result = await asyncio.to_thread(tracker.update, None, frame)
            
            tracks = tracking_result.get("analytics_data", [])
            sv_detections = tracking_result.get("sv_detections")

            analytics.update(tracks)

                # Lógica do Mapa de Calor
            if lines_config.get("modules", {}).get("heatmap", False):
                    if device_id not in heatmap_data:
                        heatmap_data[device_id] = []
                    
                    for t in tracks:
                        cx = int((t["bbox"][0] + t["bbox"][2]) / 2)
                        cy = int((t["bbox"][1] + t["bbox"][3]) / 2) 
                        heatmap_data[device_id].append((cx, cy))
                    
                    # Limita a memória a 10.000 pontos
                    if len(heatmap_data[device_id]) > 10000:
                        heatmap_data[device_id] = heatmap_data[device_id][-10000:]
            else:
                # Nos frames pulados, recuperamos da memória com segurança
                tracking_result = last_tracks
                if isinstance(tracking_result, dict):
                    tracks = tracking_result.get("analytics_data", [])
                    sv_detections = tracking_result.get("sv_detections")
                else:
                    tracks = []
                    sv_detections = None

            if len(tracks) > 0:
                print(f"👀 CAM {device_id} Vendo {len(tracks)} pessoa(s) | Bounding Box do ID {tracks[0]['track_id']}: {tracks[0]['bbox']}")

            # --- DESENHO EM TELA ---
            if len(tracks) > 0:
                xyxy = np.array([t["bbox"] for t in tracks])
                tracker_id = np.array([t["track_id"] for t in tracks])
                class_id = np.array([t["class_id"] for t in tracks])
                
                detections = sv.Detections(
                    xyxy=xyxy,
                    tracker_id=tracker_id,
                    class_id=class_id
                )

                # 💥 1. RASTRO ESTILO "COMETA FLUIDO" (Costurando os frames)
                if lines_config.get("modules", {}).get("trails", False):
                    current_ids = [t["track_id"] for t in tracks]
                    for tid in list(track_history.keys()):
                        if tid not in current_ids:
                            del track_history[tid]

                    for track in tracks:
                        tid = track['track_id']
                        # Centro da cintura
                        cx = int((track["bbox"][0] + track["bbox"][2]) / 2)
                        cy = int((track["bbox"][1] + track["bbox"][3]) / 2)
                        
                        # Guarda a posição (Pode tirar o math.sqrt, queremos todos os frames válidos)
                        track_history[tid].append((cx, cy))
                        
                        history = list(track_history[tid])
                        history_len = len(history)
                        
                        # MÁGICA VISUAL: Preenchendo os buracos
                        if history_len > 1:
                            for i in range(1, history_len):
                                pt1 = history[i - 1]
                                pt2 = history[i]
                                
                                # A espessura cresce suavemente (da ponta mais fina até 10px no corpo da pessoa)
                                thickness = int(10 * (i / history_len)) + 1
                                
                                # 1. Desenha a linha ligando um ponto ao outro (isso tapa o buraco do FPS)
                                cv2.line(frame, pt1, pt2, (255, 0, 255), thickness, cv2.LINE_AA)
                                
                                # 2. Desenha a bolha arredondada nas emendas para o traço ficar macio
                                cv2.circle(frame, pt2, thickness // 2, (255, 0, 255), -1, cv2.LINE_AA)

                labels = []
                current_time = time.time()
                
                # Verifica quem está dentro do Polígono (Se ele existir)
                is_inside = [False] * len(tracks)
                if zone is not None:
                    is_inside = zone.trigger(detections=detections)
                    frame = zone_annotator.annotate(scene=frame) # Desenha a zona translúcida

                for tid in list(dwell_timers.keys()):
                    if tid not in current_ids:
                        del dwell_timers[tid]

                for i, t_id in enumerate(tracker_id):
                    label = f"ID: {t_id}"
                    
                    if lines_config.get("modules", {}).get("dwell", False):
                        if zone is None or is_inside[i]:
                            if t_id not in dwell_timers:
                                dwell_timers[t_id] = current_time
                            segundos = int(current_time - dwell_timers[t_id])
                            label += f" ({segundos}s)"
                        else:
                            if t_id in dwell_timers:
                                del dwell_timers[t_id]
                    
                    labels.append(label)

                # 💥 O GRANDE FINAL: DESENHANDO A SILHUETA
                # Se as máscaras existirem (Modelo de Segmentação), ele pinta o corpo!
                if sv_detections.mask is not None:
                    frame = mask_annotator.annotate(scene=frame, detections=sv_detections)
                else:
                    # Se cair aqui, é porque o modelo antigo (Sem Máscara) teimou em rodar!
                    print("⚠️ AVISO: Máscaras não encontradas! A IA ainda está usando o modelo de Bounding Box.")
                    frame = box_annotator.annotate(scene=frame, detections=sv_detections)

                # Desenha a Etiqueta (ID e Tempo) por cima da silhueta
                frame = label_annotator.annotate(scene=frame, detections=sv_detections, labels=labels)

            # --- Linhas de Contagem (Verde e Amarelo) ---
            if len(entrant_line) > 1:
                pts = np.array([ [p['x'], p['y']] for p in entrant_line ], np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], False, (0, 255, 0), 3)
            
            if len(passerby_line) > 1:
                pts = np.array([ [p['x'], p['y']] for p in passerby_line ], np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], False, (0, 255, 255), 3)

            # Placares
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
                    atuais = analytics.get_final_results()
                    
                    old_events = bagagem_resultados.get("recent_events", [])
                    new_events = atuais.get("recent_events", [])
                    
                    # Apenas junta as listas e pega os 100 últimos. 
                    # Isso evita o bug de deletar quem passa no mesmo exato segundo!
                    combined_events = sorted(old_events + new_events, key=lambda x: x["time"], reverse=True)[:100]

                    # Usa sempre um dicionário padrão como base para evitar chaves faltantes (KeyError)
                    base_keys = {"Homem": 0, "Mulher": 0, "NaoIdentificado": 0, "Total": 0}

                    merged_results = {
                        "entrantes": {k: atuais["entrantes"].get(k, 0) + bagagem_resultados.get("entrantes", base_keys).get(k, 0) for k in base_keys},
                        "passantes": {k: atuais["passantes"].get(k, 0) + bagagem_resultados.get("passantes", base_keys).get(k, 0) for k in base_keys},
                        "total_geral": {k: atuais.get("total_geral", base_keys).get(k, 0) + bagagem_resultados.get("total_geral", base_keys).get(k, 0) for k in base_keys},
                        "recent_events": combined_events
                    }
                    
                    with SessionLocal() as db_save:
                        repo_save = VideoRepository(db_save)
                        repo_save.update_status(video_id, "live_processing")
                        vid = repo_save.get_by_id(video_id)
                        if vid:
                            vid.results = merged_results # 💥 Salva a soma total!
                            db_save.commit()
                except Exception as e:
                    print(f"Erro ao salvar estatísticas: {e}")
                last_save = time.time()
            
            await asyncio.sleep(0.01)

    except Exception as e:
        print(f"❌ Erro fatal Câmera {device_id}: {traceback.format_exc()}")
    finally:
        db.close()
        if device_id in live_frames: del live_frames[device_id]
        if device_id in latest_frames: del latest_frames[device_id]
        if device_id in heatmap_data: del heatmap_data[device_id]
        
        try:
            with SessionLocal() as db_final:
                VideoRepository(db_final).update_status(video_id, "done")
        except: pass
        print(f"✅ Câmera {device_id} Encerrada.")