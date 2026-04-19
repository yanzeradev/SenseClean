import React, { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Upload, Play, Trash2, PencilLine, CheckCircle2, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";

interface Point { x: number; y: number; }
interface FrameDimensions { width: number; height: number; }

export function VideoAnalysis() {
  const [stage, setStage] = useState<'upload' | 'drawing' | 'processing' | 'finished' | 'error'>('upload');
  
  const [videoId, setVideoId] = useState<string | null>(null);
  const [firstFrameUrl, setFirstFrameUrl] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  
  const [entrantPoints, setEntrantPoints] = useState<Point[]>([]);
  const [passerbyPoints, setPasserbyPoints] = useState<Point[]>([]);
  const [activeLine, setActiveLine] = useState<'entrant' | 'passerby'>('entrant');
  const [inSide, setInSide] = useState<'right' | 'left'>('right');
  const [frameDims, setFrameDims] = useState<FrameDimensions | null>(null);
  const [imageTimestamp, setImageTimestamp] = useState(Date.now());

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  // --- ACTIONS ---
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setStage('upload'); // Show loading state briefly if we add a spinner
    try {
      const data = await api.upload("/videos/upload", file);
      setVideoId(data.video_id);
      setFirstFrameUrl("/api" + data.first_frame_url); 
      setStage('drawing');
    } catch (err: any) {
      alert("Erro ao enviar vídeo: " + err.message);
    }
  };

  const handleProcess = async () => {
    if (entrantPoints.length < 2 || passerbyPoints.length < 2) {
      alert("Desenhe ambas as linhas (Entrantes e Passantes) com pelo menos 2 pontos.");
      return;
    }
    if (!frameDims || !videoId) return;

    setStage('processing');
    setProgress(0);

    try {
      await api.post("/videos/process", {
        video_id: videoId,
        in_side: inSide,
        entrant_line_points: entrantPoints,
        passerby_line_points: passerbyPoints,
        frame_dimensions: frameDims
      });
    } catch (err: any) {
      alert("Erro ao processar: " + err.message);
      setStage('error');
    }
  };

  const resetApp = () => {
    setStage('upload');
    setVideoId(null);
    setFirstFrameUrl(null);
    setEntrantPoints([]);
    setPasserbyPoints([]);
    setProgress(0);
  };

  // --- POLLING EFFECT ---
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (videoId && stage === "processing") {
      interval = setInterval(async () => {
        try {
          const data = await api.get(`/videos/${videoId}/status`);
          setProgress(data.progress);
          if (data.status === "completed") setStage('finished');
          else if (data.status === "failed") setStage('error');
        } catch (error) {
          console.error("Erro no polling", error);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [videoId, stage]);

  // --- CANVAS DRAWING EFFECT ---
  useEffect(() => {
    const cvs = canvasRef.current;
    const img = imgRef.current;
    if (!cvs || !img || !img.complete || stage !== 'drawing') return;

    const ctx = cvs.getContext('2d');
    if (!ctx) return;

    cvs.width = cvs.clientWidth;
    cvs.height = cvs.clientHeight;
    ctx.clearRect(0, 0, cvs.width, cvs.height);

    const drawLine = (pts: Point[], color: string, label: string) => {
      if (pts.length === 0) return;
      ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.fillStyle = color;
      ctx.beginPath();
      pts.forEach((p, i) => {
        if (i === 0) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
        ctx.fillRect(p.x - 4, p.y - 4, 8, 8);
      });
      ctx.stroke();

      if (pts.length >= 2 && label === "Entrantes") {
        const mid = Math.floor(pts.length / 2);
        const p1 = pts[mid - 1] || pts[0]; const p2 = pts[mid];
        const mx = (p1.x + p2.x) / 2; const my = (p1.y + p2.y) / 2;
        const dx = p2.x - p1.x; const dy = p2.y - p1.y;
        const len = Math.sqrt(dx * dx + dy * dy) || 1;
        const unX = -dy / len; const unY = dx / len;
        
        ctx.font = 'bold 16px sans-serif'; ctx.fillStyle = 'white';
        ctx.fillText(inSide === 'right' ? "IN" : "OUT", mx + unX * 30, my + unY * 30);
        ctx.fillText(inSide === 'right' ? "OUT" : "IN", mx - unX * 30, my - unY * 30);
      }
    };

    drawLine(entrantPoints, '#22c55e', "Entrantes");
    drawLine(passerbyPoints, '#eab308', "Passantes");
  }, [entrantPoints, passerbyPoints, inSide, stage]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const pt = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    activeLine === 'entrant' 
        ? setEntrantPoints([...entrantPoints, pt]) 
        : setPasserbyPoints([...passerbyPoints, pt]);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Configuração de Análise</CardTitle>
          <CardDescription>
            {stage === 'upload' ? "Carregue um vídeo MP4 para iniciar." : "Desenhe as linhas de contagem no frame abaixo."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          
          {/* UPLOAD STAGE */}
          {stage === 'upload' && (
            <div className="border-2 border-dashed rounded-xl h-[400px] flex flex-col items-center justify-center gap-4 bg-muted/30">
              <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center text-primary">
                <Upload className="w-6 h-6" />
              </div>
              <div className="text-center">
                <p className="font-medium">Selecione um arquivo de vídeo</p>
                <p className="text-sm text-muted-foreground">MP4, AVI ou MKV (Máx. 500MB)</p>
              </div>
              <Label htmlFor="video-upload" className="cursor-pointer">
                <div className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors font-medium">
                  Escolher Arquivo
                </div>
                <Input id="video-upload" type="file" className="hidden" onChange={handleUpload} accept="video/*" />
              </Label>
            </div>
          )}

          {/* DRAWING STAGE */}
          {stage === 'drawing' && firstFrameUrl && (
            <div className="space-y-4">
              <div className="relative rounded-lg overflow-hidden bg-black border border-border">
                <img 
                  ref={imgRef}
                  src={`${firstFrameUrl}?t=${imageTimestamp}`} 
                  alt="Primeiro Frame"
                  className="w-full h-auto object-contain block"
                  onLoad={(e) => setFrameDims({ width: e.currentTarget.width, height: e.currentTarget.height })}
                  onError={() => {
                    setTimeout(() => {
                      setImageTimestamp(Date.now());
                    }, 1500);
                  }}
                />
                <canvas
                  ref={canvasRef}
                  className="absolute top-0 left-0 w-full h-full cursor-crosshair z-20"
                  onClick={handleCanvasClick}
                />
              </div>

              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-wrap gap-2">
                  <Button 
                    variant={activeLine === "entrant" ? "default" : "outline"} 
                    size="sm" onClick={() => setActiveLine("entrant")} className="gap-2"
                  >
                    <PencilLine className="w-4 h-4" /> Entrantes (Verde)
                  </Button>
                  <Button 
                    variant={activeLine === "passerby" ? "secondary" : "outline"} 
                    size="sm" onClick={() => setActiveLine("passerby")} className="gap-2"
                  >
                    <PencilLine className="w-4 h-4" /> Passantes (Amarelo)
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setInSide(inSide === 'right' ? 'left' : 'right')} className="gap-2">
                    <RefreshCw className="w-4 h-4" /> Inverter IN/OUT
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => activeLine === 'entrant' ? setEntrantPoints([]) : setPasserbyPoints([])} className="gap-2">
                    <Trash2 className="w-4 h-4" /> Limpar
                  </Button>
                </div>
                <Button onClick={handleProcess} className="gap-2">
                  Iniciar Processamento <Play className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}

          {/* PROCESSING / FINISHED STAGE */}
          {(stage === 'processing' || stage === 'finished') && (
            <div className="space-y-4">
              {stage === 'processing' && (
                <div className="w-full bg-muted rounded-full h-4 border border-border overflow-hidden">
                  <div className="bg-primary h-4 rounded-full transition-all duration-500" style={{ width: `${progress}%` }}></div>
                </div>
              )}

              <div className="relative rounded-lg overflow-hidden bg-black aspect-video flex justify-center items-center border border-border">
                {stage === 'processing' && videoId ? (
                  <img src={`/api/videos/${videoId}/stream`} alt="Stream" className="w-full h-full object-contain" />
                ) : (
                  <div className="text-center p-6">
                    <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
                    <h2 className="text-2xl font-bold mb-2">Concluído!</h2>
                    <p className="text-muted-foreground mb-6">Resultados disponíveis na aba Histórico.</p>
                    <Button onClick={resetApp}>Processar Outro Vídeo</Button>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* SIDEBAR INSTRUCTIONS */}
      <div className="space-y-6">
        <Card>
          <CardHeader><CardTitle className="text-sm font-medium">Instruções</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-4">
            <div className="flex gap-3"><div className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0">1</div><p>Carregue o vídeo que deseja analisar.</p></div>
            <div className="flex gap-3"><div className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0">2</div><p>Desenhe a linha de Entrantes (Verde) e Passantes (Amarela).</p></div>
            <div className="flex gap-3"><div className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0">3</div><p>Ajuste qual lado da linha verde significa "Entrada" (IN).</p></div>
            <div className="flex gap-3"><div className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0">4</div><p>Inicie o processamento.</p></div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-sm font-medium">Status do Motor</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-center gap-2 text-green-500">
              <CheckCircle2 className="w-4 h-4" />
              <span className="text-sm font-medium">IA Core Online</span>
            </div>
            <p className="text-xs text-muted-foreground mt-2">Pronto para processamento contínuo.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}