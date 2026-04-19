import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileSpreadsheet, Download, Clock, AlertCircle, RefreshCw, Video } from "lucide-react";
import { api } from "@/lib/api";

// Tipagem rigorosa baseada no modelo SQLAlchemy (Video) do backend
interface VideoHistory {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  processed_video_path: string | null;
  results: {
    total_geral?: { Total: number; Homem: number; Mulher: number };
    entrantes?: { Total: number };
    passantes?: { Total: number };
  } | null;
}

export function Dashboard() {
  const [videos, setVideos] = useState<VideoHistory[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      // Faz o GET na nossa rota root do prefixo /videos
      const data = await api.get("/videos/");
      setVideos(data);
    } catch (error) {
      console.error("Erro ao buscar histórico:", error);
    } finally {
      setLoading(false);
    }
  };

  // Busca os dados assim que o componente é montado na tela
  useEffect(() => {
    fetchHistory();
  }, []);

  // Formata a data (Ex: 14/04/2026 às 15:30)
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    }).format(date);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground gap-4">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
        <p>Carregando histórico...</p>
      </div>
    );
  }

  if (videos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] border-2 border-dashed border-gray-800 rounded-xl bg-gray-900/30 text-center p-6">
        <Video className="w-12 h-12 text-gray-700 mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Nenhum vídeo processado ainda</h2>
        <p className="text-muted-foreground">Vá até a aba "Análise de Vídeo" para iniciar sua primeira contagem.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">Histórico de Processamento</h2>
          <p className="text-muted-foreground text-sm">Visualize os resultados e baixe os relatórios gerados.</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchHistory} className="gap-2">
          <RefreshCw className="w-4 h-4" /> Atualizar
        </Button>
      </div>

      {/* Grid Responsivo para os Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {videos.map((vid) => (
          <Card key={vid.id} className="overflow-hidden border-gray-800 bg-gray-900/50 flex flex-col">
            
            {/* Imagem de Capa do Vídeo */}
            <div className="relative aspect-video bg-black border-b border-gray-800">
              <img 
                src={`/static/frames/${vid.id}.jpg`} 
                alt="Thumbnail"
                className="w-full h-full object-cover opacity-80 hover:opacity-100 transition-opacity"
                onError={(e) => {
                  // Fallback se a imagem não existir
                  (e.target as HTMLImageElement).src = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
                }}
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
                ID: {vid.id.split('-')[0]}...
              </CardTitle>
              <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
                <Clock className="w-3 h-3" />
                {formatDate(vid.created_at)}
              </div>
            </CardHeader>

            <CardContent className="flex-1">
              {vid.status === 'completed' && vid.results ? (
                <div className="grid grid-cols-2 gap-2 mt-2">
                  <div className="bg-gray-800/50 p-2 rounded-md text-center">
                    <p className="text-xs text-gray-400">Entrantes</p>
                    <p className="text-xl font-bold text-green-500">{vid.results.entrantes?.Total || 0}</p>
                  </div>
                  <div className="bg-gray-800/50 p-2 rounded-md text-center">
                    <p className="text-xs text-gray-400">Passantes</p>
                    <p className="text-xl font-bold text-yellow-500">{vid.results.passantes?.Total || 0}</p>
                  </div>
                </div>
              ) : vid.status === 'failed' ? (
                <div className="flex items-center gap-2 text-red-400 mt-4 text-sm bg-red-950/20 p-2 rounded-md">
                  <AlertCircle className="w-4 h-4" />
                  Houve um erro na análise.
                </div>
              ) : (
                <div className="mt-4 text-sm text-gray-400 text-center py-2">
                  Aguardando finalização...
                </div>
              )}
            </CardContent>

            <CardFooter className="pt-2 gap-2 bg-gray-900 border-t border-gray-800">
              <Button 
                variant="default" 
                className="flex-1 gap-2 text-xs" 
                disabled={vid.status !== 'completed'}
                onClick={() => {
                  // Força o navegador a baixar em vez de tentar abrir na aba
                  const a = document.createElement('a');
                  a.href = `/static/output_videos/${vid.id}.webm`;
                  a.download = `video_${vid.id}.webm`;
                  a.click();
                }}
              >
                <Download className="w-4 h-4" /> Vídeo
              </Button>
              <Button 
                variant="secondary" 
                className="flex-1 gap-2 text-xs bg-green-900/30 text-green-400 hover:bg-green-900/50 hover:text-green-300"
                disabled={vid.status !== 'completed'}
                onClick={() => {
                  const a = document.createElement('a');
                  a.href = `/static/reports/${vid.id}_report.xlsx`;
                  a.download = `relatorio_${vid.id}.xlsx`;
                  a.click();
                }}
              >
                <FileSpreadsheet className="w-4 h-4" /> Excel
              </Button>
            </CardFooter>
            
          </Card>
        ))}
      </div>
    </div>
  );
}