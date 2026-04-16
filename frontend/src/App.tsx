import React, { useState, useEffect, useRef } from 'react';

// --- 1. TYPES & INTERFACES ---
interface Point { x: number; y: number; }
interface FrameDimensions { width: number; height: number; }

interface UploadResponse {
  video_id: string;
  video_path: string;
  first_frame_url: string;
}

interface StatusResponse {
  video_id: string;
  status: string;
  progress: number;
}

// --- 2. CANVAS COMPONENT ---
// Separamos o Canvas para manter o código limpo e aplicar o Single Responsibility Principle
const DrawingCanvas: React.FC<{
  imageUrl: string;
  entrantPoints: Point[];
  passerbyPoints: Point[];
  activeLine: 'entrant' | 'passerby';
  inSide: 'right' | 'left';
  onAddPoint: (pt: Point) => void;
  onImageLoad: (dims: FrameDimensions) => void;
}> = ({ imageUrl, entrantPoints, passerbyPoints, activeLine, inSide, onAddPoint, onImageLoad }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  // Função para desenhar as linhas no Canvas
  const drawLine = (ctx: CanvasRenderingContext2D, points: Point[], color: string, label: string) => {
    if (points.length === 0) return;
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.fillStyle = color;
    ctx.beginPath();
    points.forEach((p, i) => {
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
      ctx.fillRect(p.x - 4, p.y - 4, 8, 8); // Desenha os "nós" (pontos)
    });
    ctx.stroke();

    // Desenha o texto IN/OUT para a linha de entrantes
    if (points.length >= 2 && label === "Entrantes") {
      const mid = Math.floor(points.length / 2);
      const p1 = points[mid - 1] || points[0];
      const p2 = points[mid];
      const mx = (p1.x + p2.x) / 2;
      const my = (p1.y + p2.y) / 2;
      
      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      const len = Math.sqrt(dx * dx + dy * dy) || 1;
      const unX = -dy / len;
      const unY = dx / len;
      
      ctx.font = 'bold 18px sans-serif';
      ctx.fillStyle = 'white';
      ctx.fillText(inSide === 'right' ? "IN" : "OUT", mx + unX * 30, my + unY * 30);
      ctx.fillText(inSide === 'right' ? "OUT" : "IN", mx - unX * 30, my - unY * 30);
    }
  };

  // Re-desenha toda vez que os pontos mudam
  useEffect(() => {
    const cvs = canvasRef.current;
    const img = imgRef.current;
    if (!cvs || !img || !img.complete) return;

    const ctx = cvs.getContext('2d');
    if (!ctx) return;

    // 💥 CORREÇÃO AQUI: Garante que a resolução de desenho do canvas 
    // seja exatamente igual ao tamanho que ele está ocupando na tela
    cvs.width = cvs.clientWidth;
    cvs.height = cvs.clientHeight;
    
    ctx.clearRect(0, 0, cvs.width, cvs.height);

    drawLine(ctx, entrantPoints, '#22c55e', "Entrantes"); // Verde Tailwind
    drawLine(ctx, passerbyPoints, '#eab308', "Passantes"); // Amarelo Tailwind
  }, [entrantPoints, passerbyPoints, imageUrl, inSide]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const pt = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    onAddPoint(pt);
  };

  return (
    <div className="relative inline-block border-2 border-gray-700 rounded-lg overflow-hidden">
      <img 
        ref={imgRef}
        src={`http://127.0.0.1:8000${imageUrl}`} 
        alt="Primeiro Frame"
        className="block max-w-full h-auto max-h-[60vh] object-contain"
        onLoad={(e) => onImageLoad({ width: e.currentTarget.width, height: e.currentTarget.height })}
      />
      {/* 💥 CORREÇÃO AQUI: Adicionado w-full h-full para cobrir a imagem toda */}
      <canvas 
        ref={canvasRef} 
        onClick={handleCanvasClick}
        className="absolute top-0 left-0 w-full h-full cursor-crosshair"
      />
    </div>
  );
};

// --- 3. MAIN APP COMPONENT ---
export default function App() {
  // State Machine
  const [stage, setStage] = useState<'upload' | 'drawing' | 'processing' | 'finished' | 'error'>('upload');
  
  // Data States
  const [videoId, setVideoId] = useState<string | null>(null);
  const [firstFrameUrl, setFirstFrameUrl] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string>("");

  // Canvas States
  const [entrantPoints, setEntrantPoints] = useState<Point[]>([]);
  const [passerbyPoints, setPasserbyPoints] = useState<Point[]>([]);
  const [activeLine, setActiveLine] = useState<'entrant' | 'passerby'>('entrant');
  const [inSide, setInSide] = useState<'right' | 'left'>('right');
  const [frameDims, setFrameDims] = useState<FrameDimensions | null>(null);

  // -- Actions --
  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; 
    if (!file) return;
    
    setStage('upload');
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://127.0.0.1:8000/videos/upload", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const data: UploadResponse = await response.json();
        setVideoId(data.video_id);
        setFirstFrameUrl(data.first_frame_url);
        setStage('drawing');
      } else {
        throw new Error("Falha no upload do vídeo.");
      }
    } catch (error: any) {
      setErrorMsg(error.message);
      setStage('error');
    }
  };

  const handleProcess = async () => {
    if (entrantPoints.length < 2 || passerbyPoints.length < 2) {
      alert("Por favor, desenhe ambas as linhas (Entrantes e Passantes) com pelo menos 2 pontos cada.");
      return;
    }
    if (!frameDims) return;

    setStage('processing');
    setProgress(0);

    try {
      const response = await fetch("http://127.0.0.1:8000/videos/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_id: videoId,
          in_side: inSide,
          entrant_line_points: entrantPoints,
          passerby_line_points: passerbyPoints,
          frame_dimensions: frameDims
        }),
      });

      if (!response.ok) throw new Error("Erro ao iniciar processamento.");
    } catch (error: any) {
      setErrorMsg(error.message);
      setStage('error');
    }
  };

  const resetApp = () => {
    setStage('upload');
    setVideoId(null);
    setEntrantPoints([]);
    setPasserbyPoints([]);
    setProgress(0);
  };

  // -- Polling Effect (Same as before) --
  useEffect(() => {
    let pollingInterval: ReturnType<typeof setInterval>;

    if (videoId && stage === "processing") {
      pollingInterval = setInterval(async () => {
        try {
          const response = await fetch(`http://127.0.0.1:8000/videos/${videoId}/status`);
          if (response.ok) {
            const data: StatusResponse = await response.json();
            setProgress(data.progress);

            if (data.status === "completed") setStage('finished');
            else if (data.status === "failed") {
              setErrorMsg("Ocorreu um erro no processamento interno do servidor.");
              setStage('error');
            }
          }
        } catch (error) {
          console.error("Error fetching status:", error);
        }
      }, 1000);
    }
    return () => clearInterval(pollingInterval);
  }, [videoId, stage]);

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col font-sans">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 p-4 shadow-sm flex justify-between items-center">
        <h1 className="text-2xl font-bold text-blue-500 flex items-center gap-2">
          <span className="text-white">Sense</span>Clean
        </h1>
        {stage !== 'upload' && (
          <button onClick={resetApp} className="text-sm text-gray-400 hover:text-white transition">
            Voltar ao Início
          </button>
        )}
      </header>

      {/* Main Content based on State Machine */}
      <main className="flex-1 flex flex-col items-center p-6 gap-6 w-full max-w-5xl mx-auto">
        
        {/* STAGE: UPLOAD */}
        {stage === 'upload' && (
          <div className="flex flex-col items-center justify-center h-64 w-full border-2 border-dashed border-gray-700 rounded-xl bg-gray-900 mt-10">
            <input type="file" id="video-upload" accept="video/mp4" className="hidden" onChange={handleUpload} />
            <label htmlFor="video-upload" className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-md cursor-pointer font-semibold shadow-lg transition-all">
              Selecione o Vídeo (MP4)
            </label>
            <p className="text-gray-500 mt-4 text-sm">O sistema irá extrair o primeiro frame para configuração.</p>
          </div>
        )}

        {/* STAGE: DRAWING */}
        {stage === 'drawing' && firstFrameUrl && (
          <div className="flex flex-col items-center w-full gap-4">
            <div className="bg-gray-900 p-4 rounded-xl border border-gray-800 w-full flex flex-wrap justify-center gap-4 shadow-lg">
              <button 
                onClick={() => setActiveLine('entrant')}
                className={`px-4 py-2 rounded-md font-semibold transition-colors ${activeLine === 'entrant' ? 'bg-green-600 text-white' : 'bg-gray-800 text-gray-300'}`}
              >
                Linha Entrantes (Verde)
              </button>
              <button 
                onClick={() => setActiveLine('passerby')}
                className={`px-4 py-2 rounded-md font-semibold transition-colors ${activeLine === 'passerby' ? 'bg-yellow-500 text-black' : 'bg-gray-800 text-gray-300'}`}
              >
                Linha Passantes (Amarelo)
              </button>
              <div className="w-px h-10 bg-gray-700 hidden sm:block"></div>
              <button onClick={() => activeLine === 'entrant' ? setEntrantPoints([]) : setPasserbyPoints([])} className="px-4 py-2 bg-red-900/50 hover:bg-red-600 text-red-200 hover:text-white rounded-md transition">
                Limpar Linha Atual
              </button>
              <button onClick={() => setInSide(inSide === 'right' ? 'left' : 'right')} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md transition">
                Inverter IN/OUT
              </button>
            </div>

            <DrawingCanvas 
              imageUrl={firstFrameUrl}
              entrantPoints={entrantPoints}
              passerbyPoints={passerbyPoints}
              activeLine={activeLine}
              inSide={inSide}
              onAddPoint={(pt) => activeLine === 'entrant' ? setEntrantPoints([...entrantPoints, pt]) : setPasserbyPoints([...passerbyPoints, pt])}
              onImageLoad={setFrameDims}
            />

            <button onClick={handleProcess} className="px-8 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-md font-bold shadow-lg text-lg w-full max-w-md mt-4 transition-all">
              🚀 Iniciar Processamento IA
            </button>
          </div>
        )}

        {/* STAGE: PROCESSING OR FINISHED */}
        {(stage === 'processing' || stage === 'finished') && (
          <div className="w-full flex flex-col items-center w-full">
            {stage === 'processing' && (
              <div className="w-full bg-gray-800 rounded-full h-4 mb-4 border border-gray-700 overflow-hidden">
                <div className="bg-blue-500 h-4 rounded-full transition-all duration-500 ease-out" style={{ width: `${progress}%` }}></div>
                <p className="text-center text-xs mt-1 text-gray-400">{Math.round(progress)}% Processado</p>
              </div>
            )}

            <div className="w-full bg-gray-900 rounded-xl border border-gray-800 overflow-hidden shadow-2xl relative">
              <div className="px-4 py-2 bg-gray-950/50 border-b border-gray-800 flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${stage === 'processing' ? "bg-red-500 animate-pulse" : "bg-green-500"}`}></div>
                  <span className="text-xs text-gray-300 font-medium">{stage === 'processing' ? "LIVE STREAM" : "CONCLUÍDO"}</span>
                </div>
              </div>

              <div className="relative w-full aspect-video bg-black flex justify-center items-center">
                {stage === 'processing' && videoId ? (
                  <img src={`http://127.0.0.1:8000/videos/${videoId}/stream`} alt="Stream" className="w-full h-full object-contain" />
                ) : (
                  <div className="text-center">
                    <h2 className="text-2xl font-bold text-green-500 mb-2">Processamento Finalizado!</h2>
                    <p className="text-gray-400">Os resultados foram salvos no banco de dados.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* STAGE: ERROR */}
        {stage === 'error' && (
          <div className="text-center bg-red-900/30 border border-red-800 p-8 rounded-xl w-full max-w-lg mt-10">
            <h2 className="text-xl font-bold text-red-500 mb-4">Ops! Algo deu errado.</h2>
            <p className="text-red-200 mb-6">{errorMsg}</p>
            <button onClick={resetApp} className="px-6 py-2 bg-red-700 hover:bg-red-600 text-white rounded-md font-semibold transition">
              Tentar Novamente
            </button>
          </div>
        )}
      </main>
    </div>
  );
}