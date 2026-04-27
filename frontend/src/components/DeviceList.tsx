import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Camera, Search, Plus, RefreshCw, Settings, Trash2, Eye, X, PencilLine, Map as MapIcon, ActivitySquare, Timer, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";

interface Point { x: number; y: number; }

// 💥 1. Recebemos o dimsRef aqui
const DrawingCanvas = ({ imageUrl, entrantPoints, setEntrantPoints, passerbyPoints, setPasserbyPoints, polygonPoints, setPolygonPoints, activeLine, inSide, dimsRef }: any) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [isLoading, setIsLoading] = useState(true);

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
        if (!cvs || !img || isLoading) return;

        const render = () => {
            cvs.width = cvs.clientWidth;
            cvs.height = cvs.clientHeight;
            
            // 💥 2. Salva o tamanho silenciosamente sem dar crash no React
            if (dimsRef) {
                dimsRef.current = { width: cvs.width, height: cvs.height };
            }
            
            const ctx = cvs.getContext('2d');
            if (!ctx) return;
            ctx.clearRect(0, 0, cvs.width, cvs.height);
            drawLine(ctx, entrantPoints, '#22c55e', "Entrantes");
            drawLine(ctx, passerbyPoints, '#eab308', "Passantes");
            
            if (polygonPoints.length > 0) {
                ctx.fillStyle = 'rgba(168, 85, 247, 0.3)'; // Roxo translúcido
                ctx.strokeStyle = '#a855f7';
                ctx.lineWidth = 2;
                ctx.beginPath();
                polygonPoints.forEach((p: Point, i: number) => {
                    i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
                    ctx.fillRect(p.x - 4, p.y - 4, 8, 8);
                });
                ctx.closePath();
                ctx.fill();
                ctx.stroke();
            }
        };

        if (img.complete) render();
        else img.onload = render;
    }, [entrantPoints, passerbyPoints, polygonPoints, activeLine, imageUrl, inSide]);

    const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
        const cvs = canvasRef.current;
        if(!cvs) return;
        const rect = cvs.getBoundingClientRect();
        
        // Removemos o scaleX e scaleY. O mouse bate perfeitamente com a ponta do pincel agora!
        const pt = { x: e.clientX - rect.left, y: e.clientY - rect.top };
        
        if (activeLine === 'entrant') setEntrantPoints([...entrantPoints, pt]);
        else if (activeLine === 'passerby') setPasserbyPoints([...passerbyPoints, pt]);
        else setPolygonPoints([...polygonPoints, pt]);
    };

    return (
        <div ref={containerRef} className="relative w-full aspect-video rounded-lg overflow-hidden border border-gray-700 bg-black">
            <img 
                src={imageUrl} 
                alt="Snapshot" 
                className={`w-full h-full object-fill block transition-opacity duration-300 ${isLoading ? 'opacity-0' : 'opacity-100'}`} 
                crossOrigin="anonymous" 
                onLoad={() => setIsLoading(false)} 
            />
            <canvas ref={canvasRef} onClick={handleClick} className="absolute top-0 left-0 w-full h-full cursor-crosshair z-10" />
        </div>
    );
};

const SnapshotViewer = ({ deviceId }: { deviceId: number }) => {
  const [url, setUrl] = useState(`/api/devices/${deviceId}/snapshot?t=${Date.now()}`);
  const [isError, setIsError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const handleError = () => {
    setIsError(true);
    setIsLoading(false);
    setTimeout(() => {
      setUrl(`/api/devices/${deviceId}/snapshot?t=${Date.now()}`);
      setIsError(false);
      setIsLoading(true);
    }, 3000);
  };

  return (
    <div className="relative w-full h-full bg-gray-950 flex items-center justify-center">
      {isLoading && !isError && (
        <div className="absolute inset-0 flex flex-col items-center justify-center z-20 bg-gray-900">
          <RefreshCw className="w-5 h-5 animate-spin text-blue-500 mb-2" />
          <span className="text-xs text-gray-400">Carregando imagem...</span>
        </div>
      )}
      <img 
        src={url} alt="Camera" 
        className={`w-full h-full object-fill transition-opacity duration-500 ${isLoading || isError ? 'opacity-0' : 'opacity-100'}`} 
        onError={handleError} onLoad={() => setIsLoading(false)}
      />
      {isError && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-950 z-20">
          <RefreshCw className="w-5 h-5 animate-spin text-red-500 mb-2" />
          <span className="text-xs text-red-400 font-medium">Reconectando...</span>
        </div>
      )}
    </div>
  );
};

export function DeviceList() {
  const [devices, setDevices] = useState<any[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [scannedIps, setScannedIps] = useState<string[]>([]);
  
  const [showAddModal, setShowAuthModal] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [activeDevice, setActiveDevice] = useState<any>(null);
  
  const [viewingDevice, setViewingDevice] = useState<any>(null);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  
  const [authForm, setAuthForm] = useState({ ip: '', username: 'admin', password: '', port: '554' });
  const [configForm, setConfigForm] = useState({ name: '', start: '08:00', end: '18:00' });
  const [isConnecting, setIsConnecting] = useState(false);

  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null);
  const [entrantPoints, setEntrantPoints] = useState<Point[]>([]);
  const canvasDimsRef = useRef({ width: 640, height: 360 });
  const [passerbyPoints, setPasserbyPoints] = useState<Point[]>([]);
  const [polygonPoints, setPolygonPoints] = useState<Point[]>([]);
  const [activeLine, setActiveLine] = useState<'entrant' | 'passerby' | 'polygon'>('entrant');
  const [inSide, setInSide] = useState<'right' | 'left'>('right');
  const [canvasDims, setCanvasDims] = useState({ width: 0, height: 0 });

  const [modules, setModules] = useState({
    heatmap: false,
    trails: false,
    dwell: false,
    loitering: false
  });

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
    setIsConnecting(true);
    try {
      await api.post('/devices/autodiscover', { 
        ip_address: authForm.ip, username: authForm.username, password: authForm.password, port: authForm.port || '554' 
      });
      setShowAuthModal(false);
      loadDevices();
      alert("Câmera adicionada com sucesso!");
    } catch (e: any) { 
      alert("Falha ao conectar: " + e.message); 
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if(!confirm("Remover esta câmera?")) return;
    try {
      await api.delete(`/devices/${id}`);
      loadDevices();
    } catch (e) {}
  };

  const handleOpenConfig = (dev: any) => {
      setActiveDevice(dev);
      setConfigForm({ 
          name: dev.name || '', 
          start: dev.processing_start_time || '08:00', 
          end: dev.processing_end_time || '18:00' 
      });
      
      if (dev.lines_config) {
          setEntrantPoints(dev.lines_config.entrant || []);
          setPasserbyPoints(dev.lines_config.passerby || []);
          setPolygonPoints(dev.lines_config.polygon || []);
          setInSide(dev.lines_config.in_side || 'right');
          // Carrega os módulos salvos ou deixa falso como padrão
          setModules(dev.lines_config.modules || { heatmap: false, trails: false, dwell: false, loitering: false });
      } else {
          setEntrantPoints([]); setPasserbyPoints([]); setInSide('right');
          setModules({ heatmap: false, trails: false, dwell: false, loitering: false });
      }
      
      setSnapshotUrl(`/api/devices/${dev.id}/snapshot?t=${new Date().getTime()}`);
      setShowConfigModal(true);
  };

  const handleSaveConfig = async () => {
    if(!activeDevice) return;
    try {
      // 💥 4. Enviamos as coordenadas e o tamanho exato da tela para a API
      const linesConfig = { 
          entrant: entrantPoints, 
          passerby: passerbyPoints, 
          polygon: polygonPoints, 
          in_side: inSide, 
          modules: modules,
          canvas_dims: canvasDimsRef.current 
      };
      
      await api.put(`/devices/${activeDevice.id}/config`, {
        name: configForm.name,
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
      const go2rtcUrl = `/live/api/stream.mp4?src=${res.stream_name}`;
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

      {scannedIps.length > 0 && (
        <div className="bg-blue-950/30 border border-blue-900 rounded-lg p-4 animate-in fade-in slide-in-from-top-4">
          <h3 className="text-sm font-medium text-blue-300 mb-3 flex items-center gap-2">
            <Search className="w-4 h-4" /> Câmeras Encontradas (Clique para conectar)
          </h3>
          <div className="flex flex-wrap gap-2">
            {scannedIps.map(ip => (
              <Button 
                key={ip} variant="outline" 
                className="bg-blue-900/40 border-blue-700 text-blue-100 hover:bg-blue-700 hover:text-white"
                onClick={() => {
                  setAuthForm({ ip: ip, username: 'admin', password: '', port: '554' });
                  setShowAuthModal(true);
                }}
              >
                <Camera className="w-4 h-4 mr-2" /> {ip}
              </Button>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {devices.map(dev => (
          <Card key={dev.id} className="bg-gray-900 border-gray-800 flex flex-col overflow-hidden">
            <div className="relative aspect-video bg-black border-b border-gray-800 flex items-center justify-center overflow-hidden">
              <SnapshotViewer deviceId={dev.id} />
              <Badge className="absolute top-2 right-2 bg-green-600 z-10">Online</Badge>
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
                <Eye className="w-4 h-4" /> Ao Vivo
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
          <Card className="w-full max-w-4xl bg-gray-900 border-gray-700 max-h-[95vh] overflow-y-auto custom-scrollbar">
            <CardHeader className="flex flex-row justify-between items-center border-b border-gray-800 pb-4">
              <CardTitle>Configurar: {activeDevice.name}</CardTitle>
              <Button variant="ghost" size="icon" onClick={() => setShowConfigModal(false)}><X className="w-5 h-5"/></Button>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
               
               <div className="space-y-2">
                 <label className="text-xs text-gray-400 font-medium uppercase tracking-wider">Nome da Câmera / Setor</label>
                 <Input 
                    value={configForm.name} 
                    onChange={e => setConfigForm({...configForm, name: e.target.value})} 
                    className="bg-gray-950 border-gray-700 text-white"
                 />
               </div>

               {/* 💥 SEÇÃO 2: MÓDULOS DE INTELIGÊNCIA */}
               <div className="space-y-3 bg-gray-950/50 p-4 rounded-xl border border-gray-800">
                 <h3 className="font-medium text-white flex items-center gap-2"><ActivitySquare className="w-4 h-4 text-blue-400"/> Módulos de Inteligência Analítica</h3>
                 <p className="text-xs text-gray-400 mb-4">A contagem de fluxo (Entradas/Saídas) está sempre ativa. Ative recursos avançados abaixo:</p>
                 
                 <div className="grid grid-cols-2 gap-3">
                   <Button 
                      variant="outline" 
                      className={`justify-start gap-3 h-auto py-3 ${modules.heatmap ? 'bg-blue-900/30 border-blue-500 text-blue-100' : 'bg-gray-900 border-gray-700 text-gray-400'}`}
                      onClick={() => setModules({...modules, heatmap: !modules.heatmap})}
                    >
                     <MapIcon className={`w-5 h-5 ${modules.heatmap ? 'text-blue-400' : 'text-gray-500'}`} />
                     <div className="text-left">
                       <div className="font-bold text-sm">Mapa de Calor (Heatmap)</div>
                       <div className="text-[10px] opacity-70">Identifica zonas quentes da loja</div>
                     </div>
                   </Button>

                   <Button 
                      variant="outline" 
                      className={`justify-start gap-3 h-auto py-3 ${modules.trails ? 'bg-purple-900/30 border-purple-500 text-purple-100' : 'bg-gray-900 border-gray-700 text-gray-400'}`}
                      onClick={() => setModules({...modules, trails: !modules.trails})}
                    >
                     <ActivitySquare className={`w-5 h-5 ${modules.trails ? 'text-purple-400' : 'text-gray-500'}`} />
                     <div className="text-left">
                       <div className="font-bold text-sm">Rastros (Tracking Trails)</div>
                       <div className="text-[10px] opacity-70">Desenha a trajetória do cliente</div>
                     </div>
                   </Button>

                   <Button 
                      variant="outline" 
                      className={`justify-start gap-3 h-auto py-3 ${modules.dwell ? 'bg-green-900/30 border-green-500 text-green-100' : 'bg-gray-900 border-gray-700 text-gray-400'}`}
                      onClick={() => setModules({...modules, dwell: !modules.dwell})}
                    >
                     <Timer className={`w-5 h-5 ${modules.dwell ? 'text-green-400' : 'text-gray-500'}`} />
                     <div className="text-left">
                       <div className="font-bold text-sm">Tempo de Permanência</div>
                       <div className="text-[10px] opacity-70">Cronometra a atenção na vitrine</div>
                     </div>
                   </Button>

                   <Button 
                      variant="outline" 
                      className={`justify-start gap-3 h-auto py-3 ${modules.loitering ? 'bg-red-900/30 border-red-500 text-red-100' : 'bg-gray-900 border-gray-700 text-gray-400'}`}
                      onClick={() => setModules({...modules, loitering: !modules.loitering})}
                    >
                     <ShieldAlert className={`w-5 h-5 ${modules.loitering ? 'text-red-400' : 'text-gray-500'}`} />
                     <div className="text-left">
                       <div className="font-bold text-sm">Alerta de Vadiagem</div>
                       <div className="text-[10px] opacity-70">Segurança contra atitudes suspeitas</div>
                     </div>
                   </Button>
                 </div>
               </div>

               <div className="space-y-3">
                 <h3 className="font-medium text-white">Linhas de Contagem de Fluxo</h3>
                 <div className="flex gap-2 flex-wrap">
                    <Button variant={activeLine === 'entrant' ? 'default' : 'outline'} size="sm" onClick={() => setActiveLine('entrant')} className="gap-2 bg-green-600 hover:bg-green-700 text-white border-none"><PencilLine className="w-4 h-4"/> Entrantes</Button>
                    <Button variant={activeLine === 'passerby' ? 'default' : 'outline'} size="sm" onClick={() => setActiveLine('passerby')} className="gap-2 bg-yellow-600 hover:bg-yellow-700 text-white border-none"><PencilLine className="w-4 h-4"/> Passantes</Button>
                    <Button variant="outline" size="sm" onClick={() => setInSide(inSide === 'right' ? 'left' : 'right')}><RefreshCw className="w-4 h-4 mr-2"/> Inverter Lado</Button>
                    <Button variant="destructive" size="sm" onClick={() => {
                        if (activeLine === 'entrant') setEntrantPoints([]);
                        else if (activeLine === 'passerby') setPasserbyPoints([]);
                        else if (activeLine === 'polygon') setPolygonPoints([]);
                    }}><Trash2 className="w-4 h-4 mr-2"/> Limpar</Button>
                    <Button variant={activeLine === 'polygon' ? 'default' : 'outline'} size="sm" onClick={() => setActiveLine('polygon')} className="gap-2 bg-purple-600 hover:bg-purple-700 text-white border-none"><MapIcon className="w-4 h-4"/> Zona Dwell</Button>
                 </div>
                 {snapshotUrl ? (
                     <DrawingCanvas 
                        imageUrl={snapshotUrl} 
                        entrantPoints={entrantPoints} setEntrantPoints={setEntrantPoints} 
                        passerbyPoints={passerbyPoints} setPasserbyPoints={setPasserbyPoints} 
                        polygonPoints={polygonPoints} setPolygonPoints={setPolygonPoints} 
                        activeLine={activeLine} inSide={inSide} 
                        dimsRef={canvasDimsRef} // 💥 5. Passamos a referência
                     />
                 ) : (
                     <div className="w-full h-64 bg-gray-800 animate-pulse rounded-lg flex items-center justify-center">Carregando imagem...</div>
                 )}
               </div>

               <div className="space-y-3">
                 <h3 className="font-medium text-white">Agendamento da IA</h3>
                 <div className="grid grid-cols-2 gap-4">
                     <div><label className="text-xs text-gray-400">Hora Início</label><Input type="time" value={configForm.start} onChange={e=>setConfigForm({...configForm, start: e.target.value})} className="bg-gray-950 border-gray-700" /></div>
                     <div><label className="text-xs text-gray-400">Hora Fim</label><Input type="time" value={configForm.end} onChange={e=>setConfigForm({...configForm, end: e.target.value})} className="bg-gray-950 border-gray-700" /></div>
                 </div>
               </div>
               
               <div className="flex gap-2 pt-4">
                  <Button type="button" variant="outline" className="flex-1 bg-transparent border-gray-600" onClick={()=>setShowConfigModal(false)}>Cancelar</Button>
                  <Button type="button" onClick={handleSaveConfig} className="flex-1 bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-900/20">Salvar e Reiniciar Câmera</Button>
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
                  <div className="col-span-3"><label className="text-xs text-gray-400">IP da Câmera</label><Input value={authForm.ip} onChange={e=>setAuthForm({...authForm, ip: e.target.value})} required className="bg-gray-950 border-gray-700" /></div>
                  <div className="col-span-1"><label className="text-xs text-gray-400">Porta</label><Input value={authForm.port} onChange={e=>setAuthForm({...authForm, port: e.target.value})} placeholder="554" className="bg-gray-950 border-gray-700" /></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="text-xs text-gray-400">Usuário</label><Input value={authForm.username} onChange={e=>setAuthForm({...authForm, username: e.target.value})} required className="bg-gray-950 border-gray-700" /></div>
                  <div><label className="text-xs text-gray-400">Senha</label><Input type="password" value={authForm.password} onChange={e=>setAuthForm({...authForm, password: e.target.value})} required className="bg-gray-950 border-gray-700" /></div>
                </div>
                <div className="flex gap-2 pt-4">
                  <Button type="button" variant="outline" className="flex-1 bg-transparent border-gray-600" onClick={()=>setShowAuthModal(false)} disabled={isConnecting}>
                    Cancelar
                  </Button>
                  <Button type="submit" className="flex-1 bg-blue-600 hover:bg-blue-700 text-white" disabled={isConnecting}>
                    {isConnecting ? <><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Conectando...</> : "Conectar"}
                  </Button>
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
            <div className="bg-black aspect-video flex items-center justify-center relative overflow-hidden">
              {streamUrl ? (
                <video ref={videoRef} src={streamUrl} className="w-full h-full object-fill" controls muted playsInline preload="auto"
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