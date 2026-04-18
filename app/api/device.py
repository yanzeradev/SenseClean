import asyncio
import socket
import subprocess
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import cv2
import numpy as np

from app.database import get_db
from app.repositories.device import DeviceRepository
from app.schemas.device import DeviceResponse, DeviceConnect, DeviceUpdate
from app.services import live_manager

router = APIRouter(
    prefix="/devices",
    tags=["Devices"],
)

async def check_port(ip: str, port: int, timeout: float = 0.5):
    try:
        conn = asyncio.open_connection(ip, port)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return ip
    except:
        return None

@router.get("/scan", response_model=List[str])
async def scan_network():
    """Varre a rede local em busca de portas 554 (RTSP) abertas."""
    target_subnets = ['192.168.0.', '192.168.1.']
    
    # Tenta descobrir a subrede atual da máquina
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))
        local_ip = s.getsockname()[0]
        s.close()
        container_subnet = '.'.join(local_ip.split('.')[:-1]) + '.'
        if container_subnet not in target_subnets and not container_subnet.startswith('172.'):
            target_subnets.append(container_subnet)
    except Exception: pass

    tasks = []
    for subnet in target_subnets:
        for i in range(1, 255):
            tasks.append(check_port(f"{subnet}{i}", 554, timeout=1.0))
            
    results = await asyncio.gather(*tasks)
    return [ip for ip in results if ip is not None]

@router.get("/", response_model=List[DeviceResponse])
def list_devices(db: Session = Depends(get_db)):
    return DeviceRepository(db).get_all()

@router.post("/autodiscover")
async def autodiscover_camera(dev: DeviceConnect, db: Session = Depends(get_db)):
    """Testa múltiplos padrões RTSP com a lógica nativa do FFprobe (H.265 e UDP suportados)."""
    from urllib.parse import quote
    import ffmpeg # 💥 IMPORTANDO O FFMPEG-PYTHON DO SEU LEGADO
    
    safe_user, safe_pass = quote(dev.username), quote(dev.password)
    
    # 💥 A LISTA EXATA DO SEU SenseOpen/tools/video_capture.py
    patterns = [
        ('Yoosee/udp', '/onvif1', 'udp', False),
        ('Yoosee/tcp', '/onvif1', 'tcp', False),
        ('Intelbras/tcp', '/cam/realmonitor?channel={ch}&subtype=0', 'tcp', True),
        ('Intelbras/udp', '/cam/realmonitor?channel={ch}&subtype=0', 'udp', True),
        ('Yoosee Nova/udp', '/live/ch0', 'udp', False),
        ('Yoosee Nova/tcp', '/live/ch0', 'tcp', False),
        ('Hikvision/tcp', '/Streaming/Channels/{ch}01', 'tcp', False)
    ]
    
    working_config = None
    
    # 1. Teste Inicial
    for name, path_template, proto, is_multi in patterns:
        test_url = f"rtsp://{safe_user}:{safe_pass}@{dev.ip_address}:{dev.port}{path_template.format(ch=1)}"
        print(f"🕵️ Testando {name}...")
        
        try:
            # 💥 TIMEOUT EM MICROSSEGUNDOS E PROTOCOLO DIRETO NO PROBE (SEGREDO DO SEU LEGADO)
            await asyncio.to_thread(ffmpeg.probe, test_url, rtsp_transport=proto, timeout='5000000')
            working_config = (name, path_template, proto, is_multi)
            print(f"✅ SUCESSO! Conectado via {name}")
            break 
        except Exception:
            continue
            
    if not working_config:
        raise HTTPException(status_code=400, detail="Câmera não respondeu em nenhum padrão. Verifique usuário e senha.")

    manufacturer, path_template, proto, is_multi = working_config
    repo = DeviceRepository(db)
    
    url_ch1 = f"rtsp://{safe_user}:{safe_pass}@{dev.ip_address}:{dev.port}{path_template.format(ch=1)}"
    existing_dev = next((d for d in repo.get_all() if d.rtsp_url == url_ch1), None)
    
    if not existing_dev:
        new_dev = repo.create(
            ip_address=dev.ip_address, port=dev.port, 
            username=dev.username, password=dev.password, 
            rtsp_url=url_ch1, manufacturer=manufacturer
        )
        if is_multi:
            config_update = DeviceUpdate(name=f"Cam {dev.ip_address.split('.')[-1]} - Canal 1")
            repo.update(new_dev.id, config_update)

    # 3. Escaneamento Multi-Canal (DVRs)
    if is_multi:
        print("🕵️ DVR detectado! Varrendo canais 2 ao 16...")
        async def check_channel(ch_num):
            url = f"rtsp://{safe_user}:{safe_pass}@{dev.ip_address}:{dev.port}{path_template.format(ch=ch_num)}"
            try:
                # Timeout menor para os canais secundários
                await asyncio.to_thread(ffmpeg.probe, url, rtsp_transport=proto, timeout='3000000')
                return ch_num, url
            except:
                return None

        tasks = [check_channel(ch) for ch in range(2, 17)]
        results = await asyncio.gather(*tasks)
        
        for res in results:
            if res:
                ch_num, url = res
                existing_ch = next((d for d in repo.get_all() if d.rtsp_url == url), None)
                if not existing_ch:
                    print(f"   ✅ Canal {ch_num} Ativo! Salvando...")
                    dev_ch = repo.create(
                        ip_address=dev.ip_address, port=dev.port, 
                        username=dev.username, password=dev.password, 
                        rtsp_url=url, manufacturer=manufacturer
                    )
                    config_update = DeviceUpdate(name=f"Cam {dev.ip_address.split('.')[-1]} - Canal {ch_num}")
                    repo.update(dev_ch.id, config_update)
                    
    return {"status": "success"}

@router.put("/{device_id}/config")
async def update_device_config(device_id: int, config: DeviceUpdate, db: Session = Depends(get_db)):
    repo = DeviceRepository(db)
    dev = repo.update(device_id, config)
    if not dev: raise HTTPException(404, "Câmera não encontrada")
    
    # Reinicia o motor ao vivo para aplicar as novas linhas/horários
    await live_manager.restart_camera(device_id)
    return {"message": "Configurações aplicadas com sucesso!"}

@router.delete("/{device_id}", status_code=204)
def delete_device(device_id: int, db: Session = Depends(get_db)):
    if not DeviceRepository(db).delete(device_id):
        raise HTTPException(404, "Câmera não encontrada")
    return {"ok": True}

@router.get("/{device_id}/monitor_stream")
async def monitor_stream(device_id: int):
    """Rota MJPEG que consome a fila da câmera processada pelo Live Manager"""
    async def frame_generator():
        # Fallback de carregamento
        loading_img = np.zeros((360, 640, 3), np.uint8)
        cv2.putText(loading_img, "Conectando IA...", (180, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, loading_buffer = cv2.imencode('.jpg', loading_img)
        
        while True:
            if device_id in live_manager.monitor_queues:
                q = live_manager.monitor_queues[device_id]
                try:
                    frame_bytes = await asyncio.wait_for(q.get(), timeout=2.0)
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    continue
                except: pass
            
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + loading_buffer.tobytes() + b'\r\n')
            await asyncio.sleep(1.0)

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")