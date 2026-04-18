import asyncio
import socket
import subprocess
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from typing import List
import cv2
import numpy as np
import requests

from app.database import get_db
from app.repositories.device import DeviceRepository
from app.schemas.device import DeviceResponse, DeviceConnect, DeviceUpdate
from app.services import live_manager
from app.api.auth import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/devices",
    tags=["Devices"],
)

# Semáforo ajustado: 50 conexões por vez para não travar o Windows
scan_semaphore = asyncio.Semaphore(50)

async def check_port(ip: str, port: int, timeout: float = 1.5):
    """Testa se a porta da câmera está aberta. Timeout maior (1.5s) para câmeras Wi-Fi/lentas."""
    async with scan_semaphore:
        try:
            conn = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(conn, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return ip
        except Exception:
            return None

@router.get("/scan", response_model=List[str])
async def scan_network():
    """Varre as redes locais (forçando as padrões do Brasil e a rede atual)."""
    print("🕵️ Iniciando varredura de rede...")
    
    # 1. IPs que OBRIGATORIAMENTE vamos testar (Redes de roteadores comuns no Brasil)
    subnets_to_test = set(['192.168.0', '192.168.1', '10.0.0'])
    
    # 2. Tenta descobrir a rede real da máquina e adiciona na lista
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))
        local_ip = s.getsockname()[0]
        s.close()
        base_ip = '.'.join(local_ip.split('.')[:-1])
        subnets_to_test.add(base_ip)
        print(f"📍 Rede detectada do PC: {base_ip}.x")
    except Exception:
        pass

    tasks = []
    print(f"📡 Varrendo as redes: {', '.join(subnets_to_test)} em busca da porta 554 (RTSP)...")
    
    # Cria a fila de testes varrendo do IP 1 até o 254 em cada rede
    for subnet in subnets_to_test:
        for i in range(1, 255):
            ip = f"{subnet}.{i}"
            tasks.append(check_port(ip, 554))
            
    # Dispara tudo (respeitando o semáforo)
    results = await asyncio.gather(*tasks)
    
    # Filtra apenas os que responderam
    found_ips = list(set([ip for ip in results if ip is not None]))
    
    print(f"✅ Varredura concluída. Câmeras encontradas: {found_ips}")
    return found_ips

@router.get("/", response_model=List[DeviceResponse])
def list_devices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    return DeviceRepository(db).get_all(user_id=current_user.id)

@router.post("/autodiscover")
async def autodiscover_camera(dev: DeviceConnect, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
        if not existing_dev:
            new_dev = repo.create(
                ip_address=dev.ip_address, port=dev.port, 
                username=dev.username, password=dev.password, 
                rtsp_url=url_ch1, manufacturer=manufacturer,
                user_id=current_user.id
            )
        
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

@router.get("/{device_id}/snapshot")
def get_snapshot(device_id: int, db: Session = Depends(get_db)):
    """Retorna uma imagem estática (JPEG) da câmera para o Canvas de desenho do Frontend."""
    repo = DeviceRepository(db)
    dev = repo.get_by_id(device_id)
    if not dev: raise HTTPException(404, "Câmera não encontrada")
    
    stream_name = f"camera_{dev.id}"
    rtsp_for_go2rtc = dev.rtsp_url.replace("127.0.0.1", "host.docker.internal").replace("localhost", "host.docker.internal") + "#tcp"
    
    # 1. Garante que a câmera está registrada no motor
    try:
        requests.put("http://127.0.0.1:1984/api/streams", params={"src": rtsp_for_go2rtc, "name": stream_name}, timeout=2)
    except: pass

    # 2. Pede um frame instantâneo
    try:
        res = requests.get(f"http://127.0.0.1:1984/api/frame.jpeg?src={stream_name}", timeout=15)
        if res.status_code == 200:
            # Devolve a imagem crua, assim a tag <img> do HTML entende nativamente!
            return Response(content=res.content, media_type="image/jpeg")
    except Exception as e:
        print(f"Erro no snapshot: {e}")
        pass
        
    raise HTTPException(500, "Não foi possível capturar o frame da câmera. Ela está online?")

@router.get("/{device_id}/monitor_stream")
async def monitor_stream(device_id: int, db: Session = Depends(get_db)):
    """Rota MJPEG que consome a fila da IA ou faz fallback exibindo a imagem limpa da câmera"""
    repo = DeviceRepository(db)
    dev = repo.get_by_id(device_id)
    if not dev: raise HTTPException(404, "Dispositivo não encontrado")
        
    stream_name = f"camera_{dev.id}"

    async def frame_generator():
        while True:
            # 1. TENTA PEGAR O VÍDEO COM AS CAIXAS VERDES DA IA
            if device_id in live_manager.monitor_queues:
                q = live_manager.monitor_queues[device_id]
                try:
                    frame_bytes = await asyncio.wait_for(q.get(), timeout=1.0)
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    continue
                except: pass
            
            # 2. IA DESLIGADA? TENTA PEGAR O FRAME LIMPO DA CÂMERA (VIA GO2RTC)
            try:
                res = await asyncio.to_thread(requests.get, f"http://127.0.0.1:1984/api/frame.jpeg?src={stream_name}", timeout=2)
                if res.status_code == 200:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + res.content + b'\r\n')
                    await asyncio.sleep(1.0) # Puxa 1 frame por segundo para não pesar o dashboard
                    continue
            except Exception:
                pass
            
            # 3. CÂMERA DESLIGADA/CAIU A REDE
            loading_img = np.zeros((360, 640, 3), np.uint8)
            cv2.putText(loading_img, "Offline / Conectando...", (140, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            _, loading_buffer = cv2.imencode('.jpg', loading_img)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + loading_buffer.tobytes() + b'\r\n')
            await asyncio.sleep(2.0)

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@router.get("/{device_id}/stream-camera")
def stream_camera_feed(device_id: int, db: Session = Depends(get_db)):
    """Registra a câmera no serviço Go2RTC traduzindo o IP se for Localhost."""
    repo = DeviceRepository(db)
    dev = repo.get_by_id(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

    stream_name = f"camera_{dev.id}"
    
    # 💥 O SEGREDO: Se for 127.0.0.1, manda o Docker olhar para a máquina host!
    rtsp_for_go2rtc = dev.rtsp_url.replace("127.0.0.1", "host.docker.internal").replace("localhost", "host.docker.internal") + "#tcp"
    
    go2rtc_api_url = "http://127.0.0.1:1984/api/streams"
    
    payload = {
        "src": rtsp_for_go2rtc,
        "name": stream_name
    }

    try:
        requests.put(go2rtc_api_url, params=payload, timeout=2)
    except Exception as e:
        print(f"⚠️ Erro ao contatar Go2RTC: {e}")

    return {"stream_name": stream_name}