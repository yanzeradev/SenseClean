import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileSpreadsheet, Download, Clock, AlertCircle, RefreshCw, Video, Camera, Activity } from "lucide-react";
import { api } from "@/lib/api";

interface VideoHistory {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'live_processing' | 'done';
  created_at: string;
  processed_video_path: string | null;
  results: {
    total_geral?: { Total: number; Homem: number; Mulher: number; NaoIdentificado: number };
    entrantes?: { Total: number; Homem: number; Mulher: number; NaoIdentificado: number };
    passantes?: { Total: number; Homem: number; Mulher: number; NaoIdentificado: number };
  } | null;
}

export function Dashboard() {
  const [videos, setVideos] = useState<VideoHistory[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await api.get("/videos/");
      setVideos(data);
    } catch (error) {
      console.error("Erro ao buscar histórico:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    }).format(date);
  };

  // 💥 SEPARAMOS OS UPLOADS DAS CÂMERAS AO VIVO
  const uploadedVideos = videos.filter(v => !v.id.startsWith('live_'));
  const liveSessions = videos.filter(v => v.id.startsWith('live_'));

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground gap-4">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
        <p>Carregando relatórios...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">Histórico de Processamento</h2>
          <p className="text-muted-foreground text-sm">Visualize os dados detalhados e baixe os relatórios.</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchHistory} className="gap-2">
          <RefreshCw className="w-4 h-4" /> Atualizar Dados
        </Button>
      </div>

      <Tabs defaultValue="cameras" className="w-full">
        <TabsList className="grid w-full max-w-[400px] grid-cols-2 mb-6">
          <TabsTrigger value="cameras" className="gap-2"><Camera className="w-4 h-4"/> Câmeras Locais</TabsTrigger>
          <TabsTrigger value="videos" className="gap-2"><Video className="w-4 h-4"/> Uploads</TabsTrigger>
        </TabsList>

        {/* =========================================================
            ABA: CÂMERAS (SESSÕES AO VIVO)
        ========================================================= */}
        <TabsContent value="cameras">
          {liveSessions.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-gray-800 rounded-xl bg-gray-900/30">
              <Camera className="w-12 h-12 text-gray-700 mx-auto mb-4" />
              <p className="text-gray-400">Nenhum dado de câmera capturado ainda.</p>
              <p className="text-xs text-gray-500 mt-2">Configure uma câmera para iniciar a extração de dados.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {liveSessions.map((session) => {
                const devId = session.id.split('_')[1];
                const res = session.results || {};
                const entrantes = res.entrantes || { Homem: 0, Mulher: 0, NaoIdentificado: 0, Total: 0 };
                const passantes = res.passantes || { Homem: 0, Mulher: 0, NaoIdentificado: 0, Total: 0 };
                const isLive = session.status === 'live_processing';

                return (
                  <Card key={session.id} className={`bg-gray-900/80 overflow-hidden flex flex-col ${isLive ? 'border-blue-800' : 'border-gray-800'}`}>
                    <CardHeader className="pb-2 border-b border-gray-800/50 bg-gray-950">
                      <div className="flex justify-between items-start">
                        <div>
                          <CardTitle className="text-md text-white">Câmera ID: {devId}</CardTitle>
                          <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
                            <Clock className="w-3 h-3" /> Início: {formatDate(session.created_at)}
                          </div>
                        </div>
                        {isLive ? (
                          <Badge className="bg-blue-600/20 text-blue-400 border border-blue-500/30 flex gap-1 items-center">
                            <Activity className="w-3 h-3 animate-pulse" /> Capturando
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="bg-gray-800 text-gray-400">Encerrado</Badge>
                        )}
                      </div>
                    </CardHeader>
                    
                    <CardContent className="flex-1 pt-4">
                      {/* ESTATÍSTICAS DETALHADAS */}
                      <div className="space-y-3">
                        <div className="bg-green-950/20 border border-green-900/30 p-3 rounded-lg">
                          <p className="text-sm text-green-400 font-bold mb-2 flex justify-between">
                            Entrantes <span className="bg-green-900/50 px-2 rounded-md">{entrantes.Total}</span>
                          </p>
                          <div className="flex justify-between text-xs text-gray-300 px-1">
                            <span>Homens: <b className="text-white">{entrantes.Homem}</b></span>
                            <span>Mulheres: <b className="text-white">{entrantes.Mulher}</b></span>
                            <span>N/I: <b className="text-white">{entrantes.NaoIdentificado}</b></span>
                          </div>
                        </div>
                        
                        <div className="bg-yellow-950/20 border border-yellow-900/30 p-3 rounded-lg">
                          <p className="text-sm text-yellow-500 font-bold mb-2 flex justify-between">
                            Passantes <span className="bg-yellow-900/50 px-2 rounded-md">{passantes.Total}</span>
                          </p>
                          <div className="flex justify-between text-xs text-gray-300 px-1">
                            <span>Homens: <b className="text-white">{passantes.Homem}</b></span>
                            <span>Mulheres: <b className="text-white">{passantes.Mulher}</b></span>
                            <span>N/I: <b className="text-white">{passantes.NaoIdentificado}</b></span>
                          </div>
                        </div>
                      </div>

                      <p className="text-xs text-center mt-4 text-gray-500 italic">
                        {isLive ? `Sincronizado agora` : `Última sincronização no fim da sessão`}
                      </p>
                    </CardContent>

                    <CardFooter className="pt-3 pb-3 bg-gray-950 border-t border-gray-800">
                      <Button 
                        variant="secondary" 
                        className="w-full gap-2 text-xs bg-green-900/20 text-green-400 hover:bg-green-900/40"
                        disabled={!session.results}
                        onClick={() => {
                          const a = document.createElement('a');
                          a.href = `/api/static/reports/${session.id}_report.xlsx`;
                          a.download = `relatorio_${session.id}.xlsx`;
                          a.click();
                        }}
                      >
                        <FileSpreadsheet className="w-4 h-4" /> Baixar Excel
                      </Button>
                    </CardFooter>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>

        {/* =========================================================
            ABA: UPLOADS DE VÍDEO (COMPORTAMENTO ANTIGO)
        ========================================================= */}
        <TabsContent value="videos">
          {uploadedVideos.length === 0 ? (
             <div className="text-center py-12 border border-dashed border-gray-800 rounded-xl bg-gray-900/30">
             <Video className="w-12 h-12 text-gray-700 mx-auto mb-4" />
             <p className="text-gray-400">Nenhum vídeo processado ainda.</p>
           </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {uploadedVideos.map((vid) => (
                <Card key={vid.id} className="overflow-hidden border-gray-800 bg-gray-900/50 flex flex-col">
                  {/* Capa do Vídeo */}
                  <div className="relative aspect-video bg-black border-b border-gray-800">
                    <img 
                      src={`/api/static/frames/${vid.id}.jpg`} 
                      alt="Thumbnail"
                      className="w-full h-full object-cover opacity-80 hover:opacity-100 transition-opacity"
                      onError={(e) => { (e.target as HTMLImageElement).src = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='; }}
                    />
                    <div className="absolute top-2 right-2">
                      {vid.status === 'completed' && <Badge className="bg-green-600">Concluído</Badge>}
                      {vid.status === 'processing' && <Badge className="bg-blue-600 animate-pulse">Processando</Badge>}
                      {vid.status === 'failed' && <Badge variant="destructive">Falhou</Badge>}
                      {vid.status === 'pending' && <Badge variant="secondary">Pendente</Badge>}
                    </div>
                  </div>

                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-mono text-gray-300 truncate" title={vid.id}>
                      Vídeo MP4
                    </CardTitle>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
                      <Clock className="w-3 h-3" /> {formatDate(vid.created_at)}
                    </div>
                  </CardHeader>

                  <CardContent className="flex-1">
                    {vid.status === 'completed' && vid.results ? (
                      <div className="grid grid-cols-2 gap-2 mt-2">
                        <div className="bg-gray-800/50 p-2 rounded-md text-center border border-gray-700">
                          <p className="text-xs text-gray-400">Entrantes</p>
                          <p className="text-xl font-bold text-green-500">{vid.results.entrantes?.Total || 0}</p>
                        </div>
                        <div className="bg-gray-800/50 p-2 rounded-md text-center border border-gray-700">
                          <p className="text-xs text-gray-400">Passantes</p>
                          <p className="text-xl font-bold text-yellow-500">{vid.results.passantes?.Total || 0}</p>
                        </div>
                      </div>
                    ) : vid.status === 'failed' ? (
                      <div className="flex items-center gap-2 text-red-400 mt-4 text-sm bg-red-950/20 p-2 rounded-md">
                        <AlertCircle className="w-4 h-4" /> Erro na análise.
                      </div>
                    ) : (
                      <div className="mt-4 text-sm text-gray-400 text-center py-2">
                        Aguardando finalização...
                      </div>
                    )}
                  </CardContent>

                  <CardFooter className="pt-2 gap-2 bg-gray-900 border-t border-gray-800">
                    <Button 
                      variant="default" className="flex-1 gap-2 text-xs" disabled={vid.status !== 'completed'}
                      onClick={() => { const a = document.createElement('a'); a.href = `/api/static/output_videos/${vid.id}.webm`; a.download = `video_${vid.id}.webm`; a.click(); }}
                    >
                      <Download className="w-4 h-4" /> Vídeo
                    </Button>
                    <Button 
                      variant="secondary" className="flex-1 gap-2 text-xs bg-green-900/30 text-green-400 hover:bg-green-900/50" disabled={vid.status !== 'completed'}
                      onClick={() => { const a = document.createElement('a'); a.href = `/api/static/reports/${vid.id}_report.xlsx`; a.download = `relatorio_${vid.id}.xlsx`; a.click(); }}
                    >
                      <FileSpreadsheet className="w-4 h-4" /> Excel
                    </Button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}