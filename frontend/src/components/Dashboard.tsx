import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Camera, Video, RefreshCw, Activity, Users, ArrowRightToLine, ArrowLeftFromLine, ArrowLeft, Eye, X, Map as MapIcon } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from "@/lib/api";

export function Dashboard() {
  const [videos, setVideos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSession, setSelectedSession] = useState<any | null>(null);
  
  // Controles de Modais
  const [viewingStream, setViewingStream] = useState<string | null>(null);
  const [viewingHeatmap, setViewingHeatmap] = useState<string | null>(null); // 💥 NOVO

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await api.get("/videos/");
      setVideos(data);
      if (selectedSession) {
        const updated = data.find((v: any) => v.id === selectedSession.id);
        if (updated) setSelectedSession(updated);
      }
    } catch (error) {
      console.error("Erro ao buscar histórico:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchHistory(); }, []);

  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0');
  const dd = String(today.getDate()).padStart(2, '0');
  const todayStr = `${yyyy}${mm}${dd}`;

  const todaysSessions = videos.filter(v => 
    v.id.startsWith('daily_') && v.id.endsWith(todayStr)
  );

  const uniqueLiveSessionsMap = new Map();
  todaysSessions.forEach(session => {
    const camId = session.id.split('_')[1]; 
    if (uniqueLiveSessionsMap.has(camId)) {
        const existingSession = uniqueLiveSessionsMap.get(camId);
        if (new Date(session.created_at) > new Date(existingSession.created_at)) {
            uniqueLiveSessionsMap.set(camId, session);
        }
    } else {
        uniqueLiveSessionsMap.set(camId, session);
    }
  });

  const liveSessions = Array.from(uniqueLiveSessionsMap.values());

  if (loading && videos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground gap-4">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
        <p>Carregando relatórios...</p>
      </div>
    );
  }

  // ============================================================================
  // TELA 2: PAINEL DETALHADO DA CÂMERA (ENTERPRISE)
  // ============================================================================
  if (selectedSession) {
    const devId = selectedSession.id.split('_')[1].replace('cam', '');
    const res = selectedSession.results || {};
    const entrantes = res.entrantes?.Total || 0;
    const passantes = res.passantes?.Total || 0;
    const ocupacaoAtual = Math.max(0, entrantes - passantes);
    const totalMovimento = entrantes + passantes;

    const chartData: any[] = []; 
    const recentData: any[] = res.recent_events?.slice(0, 15) || []; 

    return (
      <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => setSelectedSession(null)} className="rounded-full bg-gray-900 hover:bg-gray-800 border-none">
              <ArrowLeft className="w-5 h-5 text-gray-300" />
            </Button>
            <div>
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                Câmera {devId} <span className="flex h-3 w-3 relative"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span><span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span></span>
              </h2>
              <p className="text-muted-foreground text-sm">Monitoramento Diário Consolidado</p>
            </div>
          </div>
          <div className="flex gap-2">
            
            {/* 💥 NOVO BOTÃO: MAPA DE CALOR */}
            <Button variant="outline" size="sm" onClick={() => setViewingHeatmap(devId)} className="gap-2 bg-purple-900/20 text-purple-400 border-purple-900/50 hover:bg-purple-900/40">
              <MapIcon className="w-4 h-4" /> Mapa de Calor
            </Button>

            <Button variant="outline" size="sm" onClick={() => setViewingStream(`/api/devices/${devId}/monitor_stream`)} className="gap-2 bg-blue-900/20 text-blue-400 border-blue-900/50 hover:bg-blue-900/40">
              <Eye className="w-4 h-4" /> Ver Câmera IA
            </Button>
            <Button variant="outline" size="sm" onClick={fetchHistory} className="gap-2 bg-gray-900/50 border-gray-700 text-gray-300 hover:text-white hover:bg-gray-800">
              <RefreshCw className="w-4 h-4" /> Atualizar Dados
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-gray-900/50 border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-400">TOTAL HOJE</CardTitle>
              <Users className="w-4 h-4 text-blue-500" />
            </CardHeader>
            <CardContent><div className="text-3xl font-bold text-white">{totalMovimento}</div></CardContent>
          </Card>
          <Card className="bg-gray-900/50 border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-400">ENTRADAS</CardTitle>
              <ArrowRightToLine className="w-4 h-4 text-green-500" />
            </CardHeader>
            <CardContent><div className="text-3xl font-bold text-white">{entrantes}</div></CardContent>
          </Card>
          <Card className="bg-gray-900/50 border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-400">SAÍDAS</CardTitle>
              <ArrowLeftFromLine className="w-4 h-4 text-yellow-500" />
            </CardHeader>
            <CardContent><div className="text-3xl font-bold text-white">{passantes}</div></CardContent>
          </Card>
          <Card className="bg-gray-900/50 border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-400">OCUPAÇÃO ATUAL</CardTitle>
              <Activity className="w-4 h-4 text-purple-500" />
            </CardHeader>
            <CardContent><div className="text-3xl font-bold text-white">{ocupacaoAtual}</div></CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2 bg-gray-900/50 border-gray-800">
            <CardHeader>
              <CardTitle className="text-md flex items-center gap-2"><Activity className="w-4 h-4 text-blue-500"/> Fluxo de Pessoas (24h)</CardTitle>
            </CardHeader>
            <CardContent className="h-[300px] flex items-center justify-center">
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <div/>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-500 text-sm">Aguardando dados estruturados por horário para desenhar o gráfico.</p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-gray-900/50 border-gray-800">
            <CardHeader>
              <CardTitle className="text-md">Detecções Recentes</CardTitle>
            </CardHeader>
            <CardContent>
              {recentData.length > 0 ? (
                <div className="space-y-4 h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                    {recentData.map((item: any, i: number) => (
                      <div key={i} className="flex items-center justify-between border-b border-gray-800 pb-3 last:border-0">
                        <div>
                          <p className={`text-sm font-bold ${item.type === 'Entrada' ? 'text-green-500' : 'text-yellow-500'}`}>
                            {item.type}
                          </p>
                          <p className="text-xs text-gray-400">{item.gender}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-gray-300 font-mono">{item.time}</p>
                        </div>
                      </div>
                    ))}
                </div>
              ) : (
                <p className="text-gray-500 text-sm text-center py-8">Nenhuma detecção registrada recentemente.</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* MODAL DA CÂMERA AO VIVO */}
        {viewingStream && (
          <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4" onClick={() => setViewingStream(null)}>
            <div className="relative w-full max-w-4xl bg-black border border-gray-700 rounded-xl overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
              <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-950">
                <h3 className="font-bold text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-blue-500 animate-pulse" /> Visão da IA em Tempo Real
                </h3>
                <Button variant="ghost" size="icon" onClick={() => setViewingStream(null)} className="text-gray-400 hover:text-white">
                  <X className="w-5 h-5" />
                </Button>
              </div>
              <div className="aspect-video w-full bg-gray-900 flex items-center justify-center">
                <img src={viewingStream} alt="Live AI Stream" className="w-full h-full object-contain" />
              </div>
            </div>
          </div>
        )}

        {/* 💥 NOVO MODAL DO MAPA DE CALOR */}
        {viewingHeatmap && (
          <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4" onClick={() => setViewingHeatmap(null)}>
            <div className="relative w-full max-w-4xl bg-black border border-gray-700 rounded-xl overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
              <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-950">
                <h3 className="font-bold text-white flex items-center gap-2">
                  <MapIcon className="w-4 h-4 text-purple-500" /> Mapa de Calor Térmico
                </h3>
                <Button variant="ghost" size="icon" onClick={() => setViewingHeatmap(null)} className="text-gray-400 hover:text-white">
                  <X className="w-5 h-5" />
                </Button>
              </div>
              <div className="aspect-video w-full bg-gray-900 flex flex-col items-center justify-center relative">
                
                {/* Imagem do Heatmap (Se der erro, ele mostra a mensagem bonita abaixo) */}
                <img 
                  src={`/api/devices/${viewingHeatmap}/heatmap?t=${Date.now()}`} 
                  alt="Heatmap" 
                  className="absolute inset-0 w-full h-full object-contain z-10"
                  onError={(e) => {
                    // Esconde a imagem quebrada
                    (e.target as HTMLImageElement).style.display = 'none';
                    // Pega a div de loading e mostra ela
                    const fallback = document.getElementById('heatmap-fallback');
                    if (fallback) fallback.style.display = 'flex';
                  }}
                />

                {/* Mensagem de Fallback (Enquanto a gente não programa o Backend) */}
                <div id="heatmap-fallback" className="hidden flex-col items-center justify-center text-center p-6 z-0">
                  <RefreshCw className="w-10 h-10 animate-spin text-purple-500 mb-4 opacity-50" />
                  <h4 className="text-lg font-bold text-white mb-2">Processando Densidade Térmica</h4>
                  <p className="text-sm text-gray-400 max-w-md">
                    A Inteligência Artificial está coletando os rastros de movimentação. O Mapa de Calor será gerado assim que houver dados suficientes.
                  </p>
                </div>

              </div>
              <div className="bg-gray-950 p-3 border-t border-gray-800 flex justify-center gap-4 text-xs text-gray-400">
                <div className="flex items-center gap-2"><div className="w-3 h-3 bg-blue-500 rounded-full"></div> Baixo Fluxo</div>
                <div className="flex items-center gap-2"><div className="w-3 h-3 bg-yellow-500 rounded-full"></div> Médio Fluxo</div>
                <div className="flex items-center gap-2"><div className="w-3 h-3 bg-red-500 rounded-full"></div> Alto Fluxo</div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ============================================================================
  // TELA 1: VITRINE DE CÂMERAS (GRID INICIAL)
  // ============================================================================
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">Painel de Lojas</h2>
          <p className="text-muted-foreground text-sm">Selecione uma câmera para ver o painel detalhado de hoje.</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchHistory} className="gap-2 bg-gray-900 border-gray-700 hover:bg-gray-800 text-white">
          <RefreshCw className="w-4 h-4" /> Atualizar
        </Button>
      </div>

      <Tabs defaultValue="cameras" className="w-full">
        <TabsList className="grid w-full max-w-[400px] grid-cols-2 mb-6 bg-gray-900/50">
          <TabsTrigger value="cameras" className="gap-2 data-[state=active]:bg-blue-600 data-[state=active]:text-white"><Camera className="w-4 h-4"/> Câmeras Diárias</TabsTrigger>
          <TabsTrigger value="videos" className="gap-2 data-[state=active]:bg-blue-600 data-[state=active]:text-white"><Video className="w-4 h-4"/> Uploads</TabsTrigger>
        </TabsList>

        <TabsContent value="cameras">
          {liveSessions.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-gray-800 rounded-xl bg-gray-900/30">
              <Camera className="w-12 h-12 text-gray-700 mx-auto mb-4" />
              <p className="text-gray-400">Nenhum dado capturado hoje.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {liveSessions.map((session) => {
                const devId = session.id.split('_')[1].replace('cam', '');
                return (
                  <Card key={session.id} className="bg-gray-900/80 overflow-hidden border-gray-800 flex flex-col group">
                    <div className="relative aspect-video bg-black overflow-hidden border-b border-gray-800">
                      <img 
                        src={`/api/devices/${devId}/snapshot?t=${new Date().getTime()}`} 
                        alt="Snapshot" 
                        className="w-full h-full object-fill opacity-80 group-hover:opacity-100 transition-all duration-300 group-hover:scale-105"
                        onError={(e) => { (e.target as HTMLImageElement).src = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='; }}
                      />
                      <div className="absolute top-2 right-2 bg-green-500/20 border border-green-500/50 text-green-400 text-xs px-2 py-1 rounded-full backdrop-blur-sm flex items-center gap-1">
                        <Activity className="w-3 h-3 animate-pulse" /> Online Hoje
                      </div>
                    </div>
                    <CardContent className="p-4 flex flex-col flex-1">
                      <h3 className="text-lg font-bold text-white mb-auto mt-4 text-center">Câmera {devId}</h3>
                      <Button 
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium shadow-lg shadow-blue-900/20"
                        onClick={() => setSelectedSession(session)}
                      >
                        Ver Dados do Dia
                      </Button>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>
        
        <TabsContent value="videos">
          <div className="text-center py-12 border border-dashed border-gray-800 rounded-xl bg-gray-900/30">
            <Video className="w-12 h-12 text-gray-700 mx-auto mb-4" />
            <p className="text-gray-400">Área de Uploads off-line.</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}