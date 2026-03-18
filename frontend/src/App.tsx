import { useState } from 'react'

function App() {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [streamKey, setStreamKey] = useState(Date.now());
  
  // NOVO: Estado para guardar o caminho que o backend nos devolveu
  const [serverVideoPath, setServerVideoPath] = useState<string>("");

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; 
    
    if (file) {
      setVideoFile(file);
      setIsUploading(true);
      
      const formData = new FormData();
      formData.append("file", file);

      try {
        const response = await fetch("http://127.0.0.1:8000/video/upload", {
          method: "POST",
          body: formData,
        });

        if (response.ok) {
          // NOVO: Extrai o video_path que o Python retornou
          const data = await response.json();
          console.log("Upload finalizado! Caminho no servidor:", data.video_path);
          
          setServerVideoPath(data.video_path); // Salva o caminho
          setStreamKey(Date.now()); // Força o refresh da tag <img>
        }
      } catch (error) {
        console.error("Erro ao enviar vídeo:", error);
      } finally {
        setIsUploading(false);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col font-sans">
      <header className="bg-gray-900 border-b border-gray-800 p-4 shadow-sm flex justify-between items-center">
        <h1 className="text-2xl font-bold text-blue-500 flex items-center gap-2">
          <span className="text-white">Sense</span>Vision
        </h1>

        <div>
          <input 
            type="file" 
            id="video-upload" 
            accept="video/mp4" 
            className="hidden" 
            onChange={handleUpload}
          />
          <label 
            htmlFor="video-upload" 
            className={`px-4 py-2 rounded-md font-semibold cursor-pointer transition-colors ${
              isUploading ? "bg-gray-600 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-500 text-white"
            }`}
          >
            {isUploading ? "Processando IA..." : (videoFile ? "Trocar Vídeo" : "Upload Video")}
          </label>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center p-6 gap-6">
        {/* ... (código dos contadores e títulos continua igual) ... */}

        <div className="w-full max-w-5xl bg-gray-900 rounded-xl border border-gray-800 overflow-hidden shadow-2xl relative">
          <div className="px-4 py-2 bg-gray-950/50 border-b border-gray-800 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
              <span className="text-xs text-gray-300 font-medium">LIVE</span>
            </div>
          </div>

          <div className="relative w-full aspect-video bg-black flex justify-center items-center">
            {/* NOVO: A URL agora passa o parâmetro '?video_path=...' apenas se um vídeo tiver sido carregado */}
            {serverVideoPath ? (
              <img 
                key={streamKey}
                src={`http://127.0.0.1:8000/video/stream?video_path=${encodeURIComponent(serverVideoPath)}`} 
                alt="SenseVision Stream" 
                className="w-full h-full object-contain"
              />
            ) : (
              <span className="text-gray-500">Aguardando envio do vídeo...</span>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

export default App