import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Camera, Search, Plus, RefreshCw, Settings, Trash2, Eye, X, PencilLine } from "lucide-react";
import { api } from "@/lib/api";

interface Point { x: number; y: number; }

// --- COMPONENTE DE DESENHO (HERDADO DA FASE 1) ---
const DrawingCanvas = ({ imageUrl, entrantPoints, setEntrantPoints, passerbyPoints, setPasserbyPoints, activeLine, inSide }: any) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const drawLine = (ctx: CanvasRenderingContext2D, points: Point[], color: string, label: string) => {
        if (points.length === 0) return;
        ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.fillStyle = color;
        ctx.beginPath();
        points.forEach((p, i) => { i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y); ctx.fillRect(p.x - 4, p.y - 4, 8, 8); });
        ctx.stroke();

        if (points.length >= 2 && label === "Entrantes") {
            const mid = Math.floor(points.length / 2);
            const p1 = points[mid - 1] || points[0]; const p2 = points[mid];
            const mx = (p1.x + p2.x) / 2; const my = (p1.y + p2.y) / 2;
            const dx = p2.x - p1.x; const dy = p2.y - p1.y;
            const len = Math.sqrt(dx * dx + dy * dy) || 1;
            const unX = -dy / len; const unY = dx / len;
            ctx.font = 'bold 16px sans-serif'; ctx.fillStyle = 'white';
            ctx.fillText(inSide === 'right' ? "IN" : "OUT", mx + unX * 30, my + unY * 30);
            ctx.fillText(inSide === 'right' ? "OUT" : "IN", mx - unX * 30, my - unY * 30);
        }
    };

    useEffect(() => {
        const cvs = canvasRef.current;
        const img = containerRef.current?.querySelector('img');
        if (!cvs || !img) return;

        const render = () => {
            cvs.width = img.naturalWidth || img.width;
            cvs.height = img.naturalHeight || img.height;
            const ctx = cvs.getContext('2d');
            if (!ctx) return;
            ctx.clearRect(0, 0, cvs.width, cvs.height);
            drawLine(ctx, entrantPoints, '#22c55e', "Entrantes");
            drawLine(ctx, passerbyPoints, '#eab308', "Passantes");
        };

        if (img.complete) render();
        else img.onload = render;
    }, [entrantPoints, passerbyPoints, activeLine, imageUrl, inSide]);

    const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
        const cvs = canvasRef.current;
        if(!cvs) return;
        const rect = cvs.getBoundingClientRect();
        const scaleX = cvs.width / rect.width;
        const scaleY = cvs.height / rect.height;
        const pt = { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY };
        activeLine === 'entrant' ? setEntrantPoints([...entrantPoints, pt]) : setPasserbyPoints([...passerbyPoints, pt]);
    };

    return (
        <div ref={containerRef} className="relative w-full rounded-lg overflow-hidden border border-gray-700 bg-black">
            <img src={imageUrl} alt="Snapshot" className="w-full h-auto block" crossOrigin="anonymous" />
            <canvas ref={canvasRef} onClick={handleClick} className="absolute top-0 left-0 w-full h-full cursor-crosshair z-10" />
        </div>
    );
};

export function DeviceList() {
  const [devices, setDevices] = useState<any[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [scannedIps, setScannedIps] = useState<string[]>([]);
  
  // Modals state
  const [showAddModal, setShowAuthModal] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [activeDevice, setActiveDevice] = useState<any>(null);
  
  const [viewingDevice, setViewingDevice] = useState<any>(null);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  
  // Config Form States
  const [authForm, setAuthForm] = useState({ ip: '', username: 'admin', password: '', port: '554' });
  const [configForm, setConfigForm] = useState({ start: '08:00', end: '18:00' });
  
  // Drawing Canvas States
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null);
  const [entrantPoints, setEntrantPoints] = useState<Point[]>([]);
  const [passerbyPoints, setPasserbyPoints] = useState<Point[]>([]);
  const [activeLine, setActiveLine] = useState<'entrant' | 'passerby'>('entrant');
  const [inSide, setInSide] = useState<'right' | 'left'>('right');

  const loadDevices = async () => {
    try {
      const res = await api.get('/devices/');
      setDevices(res);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { loadDevices(); }, []);

  const handleScan = async () => {
    setIsScanning(true);
    try {
      const ips = await api.get('/devices/scan');
      setScannedIps(ips);
      if (ips.length === 0) alert("Nenhuma câmera encontrada. O Firewall pode estar bloqueando a varredura.");
    } catch (e) { alert("Erro ao escanear rede."); }
    setIsScanning(false);
  };

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/devices/autodiscover', { 
        ip_address: authForm.ip, username: authForm.username, password: authForm.password, port: authForm.port || '554' 
      });
      setShowAuthModal(false);
      loadDevices();
      alert("Câmera adicionada com sucesso!");
    } catch (e: any) { alert("Falha ao conectar: " + e.message); }
  };

  const handleDelete = async (id: number) => {
    if(!confirm("Remover esta câmera?")) return;
    try {
      await api.delete(`/devices/${id}`);
      loadDevices();
    } catch (e) {}
  };

  // 💥 FUNÇÃO ATUALIZADA: Puxa o Snapshot e restaura as linhas velhas
  const handleOpenConfig = (dev: any) => {
      setActiveDevice(dev);
      setConfigForm({ start: dev.processing_start_time || '08:00', end: dev.processing_end_time || '18:00' });
      
      if (dev.lines_config) {
          setEntrantPoints(dev.lines_config.entrant || []);
          setPasserbyPoints(dev.lines_config.passerby || []);
          setInSide(dev.lines_config.in_side || 'right');
      } else {
          setEntrantPoints([]); setPasserbyPoints([]); setInSide('right');
      }
      
      // Adiciona o Timestamp para o navegador não puxar a foto do cache velho
      setSnapshotUrl(`http://127.0.0.1:8000/devices/${dev.id}/snapshot?t=${new Date().getTime()}`);
      setShowConfigModal(true);
  };

  const handleSaveConfig = async () => {
    if(!activeDevice) return;
    try {
      const linesConfig = { entrant: entrantPoints, passerby: passerbyPoints, in_side: inSide };
      
      await api.put(`/devices/${activeDevice.id}/config`, {
        processing_start_time: configForm.start,
        processing_end_time: configForm.end,
        lines_config: linesConfig
      });
      setShowConfigModal(false);
      alert("Configurações salvas! A IA assumirá as novas regras no horário configurado.");
      loadDevices();
    } catch (e) { alert("Erro ao salvar."); }
  };

  const handleViewStream = async (dev: any) => {
    try {
      const res = await api.get(`/devices/${dev.id}/stream-camera`);
      const go2rtcUrl = `http://127.0.0.1:1984/api/stream.mp4?src=${res.stream_name}`;
      setStreamUrl(go2rtcUrl);
      setViewingDevice(dev);
    } catch (e) { alert("Erro ao iniciar o stream da câmera."); }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">Câmeras Locais (Edge)</h2>
          <p className="text-muted-foreground text-sm">Escaneie a rede e adicione câmeras RTSP para IA em tempo real.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handleScan} disabled={isScanning}>
            {isScanning ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : <Search className="w-4 h-4 mr-2" />}
            {isScanning ? "Buscando..." : "Escanear Rede"}
          </Button>
          <Button onClick={() => { setAuthForm({...authForm, ip: ''}); setShowAuthModal(true); }}>
            <Plus className="w-4 h-4 mr-2" /> Adicionar Manual
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {devices.map(dev => (
          <Card key={dev.id} className="bg-gray-900 border-gray-800 flex flex-col overflow-hidden">
            <div className="relative aspect-video bg-black border-b border-gray-800 flex items-center justify-center">
              {/* O NOVO STREAM: Mostra a IA rodando ou cai para o Frame limpo do Go2RTC! */}
              <img 
                src={`http://127.0.0.1:8000/devices/${dev.id}/monitor_stream`} 
                alt="Monitor" className="w-full h-full object-cover"
              />
              <Badge className="absolute top-2 right-2 bg-green-600">Online</Badge>
            </div>
            
            <CardContent className="p-4 flex-1">
              <h3 className="font-bold text-lg text-white">{dev.name}</h3>
              <p className="text-sm font-mono text-gray-400">{dev.ip_address}</p>
              
              <div className="mt-4 bg-gray-800 p-2 rounded-md text-xs text-gray-300">
                <strong>Horário IA:</strong> {dev.processing_start_time || '--:--'} às {dev.processing_end_time || '--:--'}
              </div>
            </CardContent>

            <div className="bg-gray-950 p-2 flex gap-2 border-t border-gray-800">
              <Button variant="secondary" className="flex-1 gap-2 bg-blue-900/30 text-blue-400 hover:bg-blue-900/50" onClick={() => handleViewStream(dev)}>
                <Eye className="w-4 h-4" /> Visualizar
              </Button>
              <Button variant="secondary" className="flex-1 gap-2" onClick={() => handleOpenConfig(dev)}>
                <Settings className="w-4 h-4" /> Configurar
              </Button>
              <Button variant="destructive" size="icon" onClick={() => handleDelete(dev.id)}>
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </Card>
        ))}
      </div>

      {/* MODAL CONFIGURAR */}
      {showConfigModal && activeDevice && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-4xl bg-gray-900 border-gray-700 max-h-[95vh] overflow-y-auto">
            <CardHeader><CardTitle>Configurar: {activeDevice.name}</CardTitle></CardHeader>
            <CardContent className="space-y-6">
               
               <div className="space-y-3">
                 <h3 className="font-medium text-white">1. Desenhe as Linhas de Contagem</h3>
                 <div className="flex gap-2 flex-wrap">
                    <Button variant={activeLine === 'entrant' ? 'default' : 'outline'} size="sm" onClick={() => setActiveLine('entrant')} className="gap-2 bg-green-600 hover:bg-green-700 text-white border-none"><PencilLine className="w-4 h-4"/> Entrantes</Button>
                    <Button variant={activeLine === 'passerby' ? 'default' : 'outline'} size="sm" onClick={() => setActiveLine('passerby')} className="gap-2 bg-yellow-600 hover:bg-yellow-700 text-white border-none"><PencilLine className="w-4 h-4"/> Passantes</Button>
                    <Button variant="outline" size="sm" onClick={() => setInSide(inSide === 'right' ? 'left' : 'right')}><RefreshCw className="w-4 h-4 mr-2"/> Inverter Lado</Button>
                    <Button variant="destructive" size="sm" onClick={() => activeLine === 'entrant' ? setEntrantPoints([]) : setPasserbyPoints([])}><Trash2 className="w-4 h-4 mr-2"/> Limpar</Button>
                 </div>
                 {snapshotUrl ? (
                     <DrawingCanvas 
                        imageUrl={snapshotUrl} 
                        entrantPoints={entrantPoints} setEntrantPoints={setEntrantPoints} 
                        passerbyPoints={passerbyPoints} setPasserbyPoints={setPasserbyPoints} 
                        activeLine={activeLine} inSide={inSide} 
                     />
                 ) : (
                     <div className="w-full h-64 bg-gray-800 animate-pulse rounded-lg flex items-center justify-center">Carregando imagem...</div>
                 )}
               </div>

               <div className="space-y-3">
                 <h3 className="font-medium text-white">2. Agendamento da IA</h3>
                 <div className="grid grid-cols-2 gap-4">
                     <div><label className="text-xs text-gray-400">Hora Início</label><Input type="time" value={configForm.start} onChange={e=>setConfigForm({...configForm, start: e.target.value})} /></div>
                     <div><label className="text-xs text-gray-400">Hora Fim</label><Input type="time" value={configForm.end} onChange={e=>setConfigForm({...configForm, end: e.target.value})} /></div>
                 </div>
               </div>
               
               <div className="flex gap-2 pt-4">
                  <Button type="button" variant="outline" className="flex-1" onClick={()=>setShowConfigModal(false)}>Cancelar</Button>
                  <Button type="button" onClick={handleSaveConfig} className="flex-1 bg-green-600">Salvar e Reiniciar IA</Button>
                </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* MODAL ADICIONAR */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-md bg-gray-900 border-gray-700">
            <CardHeader><CardTitle>Conectar Câmera</CardTitle></CardHeader>
            <CardContent>
              <form onSubmit={handleConnect} className="space-y-4">
                <div className="grid grid-cols-4 gap-4">
                  <div className="col-span-3"><label className="text-xs text-gray-400">IP da Câmera</label><Input value={authForm.ip} onChange={e=>setAuthForm({...authForm, ip: e.target.value})} required /></div>
                  <div className="col-span-1"><label className="text-xs text-gray-400">Porta</label><Input value={authForm.port} onChange={e=>setAuthForm({...authForm, port: e.target.value})} placeholder="554" /></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="text-xs text-gray-400">Usuário</label><Input value={authForm.username} onChange={e=>setAuthForm({...authForm, username: e.target.value})} required /></div>
                  <div><label className="text-xs text-gray-400">Senha</label><Input type="password" value={authForm.password} onChange={e=>setAuthForm({...authForm, password: e.target.value})} required /></div>
                </div>
                <div className="flex gap-2 pt-4">
                  <Button type="button" variant="outline" className="flex-1" onClick={()=>setShowAuthModal(false)}>Cancelar</Button>
                  <Button type="submit" className="flex-1 bg-blue-600">Conectar</Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* MODAL VISUALIZAR AO VIVO */}
      {viewingDevice && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4" onClick={() => { setViewingDevice(null); setStreamUrl(null); }}>
          <div className="w-full max-w-4xl bg-gray-900 border border-gray-700 rounded-xl overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-950">
              <h3 className="font-bold text-white flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>{viewingDevice.name} - Ao Vivo</h3>
              <Button variant="ghost" size="icon" onClick={() => { setViewingDevice(null); setStreamUrl(null); }} className="text-gray-400 hover:text-white"><X className="w-5 h-5" /></Button>
            </div>
            <div className="bg-black aspect-video flex items-center justify-center relative">
              {streamUrl ? (
                <video ref={videoRef} src={streamUrl} className="w-full h-full object-contain" controls muted playsInline preload="auto"
                  onCanPlay={() => { if (videoRef.current) videoRef.current.play().catch(()=>console.log("Autoplay bloqueado")); }}
                />
              ) : ( <RefreshCw className="w-8 h-8 animate-spin text-gray-500" /> )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}