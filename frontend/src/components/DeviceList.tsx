import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Camera, Search, Plus, RefreshCw, Settings, Trash2, Activity, Eye, X } from "lucide-react";
import { api } from "@/lib/api";

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
  
  
  // Forms
  const videoRef = useRef<HTMLVideoElement>(null); 
  const [authForm, setAuthForm] = useState({ ip: '', username: 'admin', password: '', port: '554' });
  const [configForm, setConfigForm] = useState({ start: '08:00', end: '18:00' });

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
      // 💥 ADICIONA ESTE AVISO
      if (ips.length === 0) {
        alert("Nenhuma câmera encontrada. (O Firewall ou Docker pode estar bloqueando a varredura. Use o Adicionar Manual).");
      }
    } catch (e) { alert("Erro ao escanear rede."); }
    setIsScanning(false);
  };

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/devices/autodiscover', { 
        ip_address: authForm.ip, 
        username: authForm.username, 
        password: authForm.password, 
        // 💥 Puxa a porta do formulário, se tiver vazio usa a 554
        port: authForm.port || '554' 
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
      alert("Câmera removida com sucesso!");
    } catch (e) {}
  };

  const handleSaveConfig = async () => {
    if(!activeDevice) return;
    try {
      // Cria linhas mockadas provisórias. Em produção, você adiciona o DrawingCanvas aqui.
      const mockLines = {
          entrant: [{x: 100, y: 300}, {x: 500, y: 300}],
          passerby: [{x: 100, y: 150}, {x: 500, y: 150}],
          in_side: 'right'
      };
      
      await api.put(`/devices/${activeDevice.id}/config`, {
        processing_start_time: configForm.start,
        processing_end_time: configForm.end,
        lines_config: mockLines
      });
      setShowConfigModal(false);
      alert("Agendamento salvo! A IA assumirá no horário configurado.");
      loadDevices();
    } catch (e) {}
  };

  const handleViewStream = async (dev: any) => {
    try {
      const res = await api.get(`/devices/${dev.id}/stream-camera`);
      // Pega o nome do stream (ex: camera_1) e usa a rota /api/stream.mp4 nativa do Go2RTC
      const go2rtcUrl = `http://127.0.0.1:1984/api/stream.mp4?src=${res.stream_name}`;
      setStreamUrl(go2rtcUrl);
      setViewingDevice(dev);
    } catch (e) {
      alert("Erro ao iniciar o stream da câmera.");
    }
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
        <Card className="bg-blue-900/20 border-blue-800">
          <CardHeader><CardTitle className="text-sm text-blue-400">Câmeras Descobertas na Rede</CardTitle></CardHeader>
          <CardContent className="flex gap-2 flex-wrap">
            {scannedIps.map(ip => (
              <Badge key={ip} className="cursor-pointer bg-blue-800 hover:bg-blue-700 p-2 text-sm" 
                     onClick={() => { setAuthForm({...authForm, ip}); setShowAuthModal(true); }}>
                📷 {ip} (Clique para autenticar)
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {devices.map(dev => (
          <Card key={dev.id} className="bg-gray-900 border-gray-800 flex flex-col overflow-hidden">
            <div className="relative aspect-video bg-black border-b border-gray-800 flex items-center justify-center">
              {/* O Streaming Monitor da Câmera (Se estiver no horário configurado, toca o vídeo) */}
              <img 
                src={`http://127.0.0.1:8000/devices/${dev.id}/monitor_stream`} 
                alt="Monitor" className="w-full h-full object-cover"
                onError={(e) => { (e.target as HTMLImageElement).src = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='; }}
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
              <Button variant="secondary" className="flex-1 gap-2 bg-blue-900/30 text-blue-400 hover:bg-blue-900/50 hover:text-blue-300" onClick={() => handleViewStream(dev)}>
                <Eye className="w-4 h-4" /> Visualizar
              </Button>
              <Button variant="secondary" className="flex-1 gap-2" onClick={() => {
                 setActiveDevice(dev);
                 setConfigForm({ start: dev.processing_start_time || '08:00', end: dev.processing_end_time || '18:00' });
                 setShowConfigModal(true);
              }}>
                <Settings className="w-4 h-4" /> Agendar
              </Button>
              <Button variant="destructive" size="icon" onClick={() => handleDelete(dev.id)}>
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </Card>
        ))}
      </div>

      {/* MODAL ADICIONAR */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-md bg-gray-900 border-gray-700">
            <CardHeader><CardTitle>Conectar Câmera</CardTitle></CardHeader>
            <CardContent>
              <form onSubmit={handleConnect} className="space-y-4">
                
                {/* 💥 IP E PORTA LADO A LADO */}
                <div className="grid grid-cols-4 gap-4">
                  <div className="col-span-3">
                    <label className="text-xs text-gray-400">IP da Câmera</label>
                    <Input value={authForm.ip} onChange={e=>setAuthForm({...authForm, ip: e.target.value})} placeholder="Ex: 127.0.0.1" required />
                  </div>
                  <div className="col-span-1">
                    <label className="text-xs text-gray-400">Porta</label>
                    <Input value={authForm.port} onChange={e=>setAuthForm({...authForm, port: e.target.value})} placeholder="554" />
                  </div>
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

      {/* MODAL CONFIGURAÇÃO (AGENDAMENTO) */}
      {showConfigModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-sm bg-gray-900 border-gray-700">
            <CardHeader><CardTitle>Agendamento de IA</CardTitle></CardHeader>
            <CardContent className="space-y-4">
               <div><label className="text-xs text-gray-400">Hora Início</label><Input type="time" value={configForm.start} onChange={e=>setConfigForm({...configForm, start: e.target.value})} /></div>
               <div><label className="text-xs text-gray-400">Hora Fim</label><Input type="time" value={configForm.end} onChange={e=>setConfigForm({...configForm, end: e.target.value})} /></div>
               
               <div className="flex gap-2 pt-4">
                  <Button type="button" variant="outline" className="flex-1" onClick={()=>setShowConfigModal(false)}>Cancelar</Button>
                  <Button type="button" onClick={handleSaveConfig} className="flex-1 bg-green-600">Salvar e Reiniciar</Button>
                </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 💥 MODAL DE STREAMING AO VIVO */}
      {viewingDevice && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4" onClick={() => { setViewingDevice(null); setStreamUrl(null); }}>
          <div className="w-full max-w-4xl bg-gray-900 border border-gray-700 rounded-xl overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
            
            {/* Header do Player */}
            <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-950">
              <h3 className="font-bold text-white flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
                {viewingDevice.name} - Ao Vivo
              </h3>
              <Button variant="ghost" size="icon" onClick={() => { setViewingDevice(null); setStreamUrl(null); }} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </Button>
            </div>
            
            {/* Player de Vídeo em HTML5 nativo processando o stream MP4 do Go2RTC */}
            <div className="bg-black aspect-video flex items-center justify-center relative">
              {streamUrl ? (
                <video 
                  ref={videoRef}
                  src={streamUrl} 
                  className="w-full h-full object-contain" 
                  controls 
                  muted 
                  playsInline 
                  preload="auto"
                  onCanPlay={() => {
                    if (videoRef.current) {
                        videoRef.current.play().catch(e => console.log("Navegador bloqueou autoplay:", e));
                    }
                  }}
                />
              ) : (
                <RefreshCw className="w-8 h-8 animate-spin text-gray-500" />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}