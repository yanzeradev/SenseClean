import { useState, useEffect } from 'react';

// 1. Interfaces (Type Definitions) to ensure strict typing for API responses
interface ProcessResponse {
  message: string;
  video_id: string;
  status: string;
}

interface StatusResponse {
  video_id: string;
  status: string;
  progress: number;
}

function App() {
  // State Management
  const [videoId, setVideoId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [progress, setProgress] = useState<number>(0);
  const [isRequesting, setIsRequesting] = useState<boolean>(false);

  // 2. Function to trigger the Background Task
  const handleStartProcessing = async () => {
    setIsRequesting(true);
    setProgress(0);
    setStatus("starting");

    try {
      const response = await fetch("http://127.0.0.1:8000/videos/process", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          // Hardcoded for now. In the future, this comes from an Upload endpoint.
          video_path: "test.mp4", 
          in_side: "right"
        }),
      });

      if (response.ok) {
        const data: ProcessResponse = await response.json();
        console.log("Processing started with ID:", data.video_id);
        
        // Saving the UUID triggers the useEffect polling mechanism
        setVideoId(data.video_id);
        setStatus(data.status);
      } else {
        console.error("Failed to start processing.");
        setStatus("error");
      }
    } catch (error) {
      console.error("Network error:", error);
      setStatus("error");
    } finally {
      setIsRequesting(false);
    }
  };

  // 3. The Polling Mechanism (Side Effect)
  useEffect(() => {
    let pollingInterval: ReturnType<typeof setInterval>;

    // Only poll if we have a videoId and the status is active
    if (videoId && (status === "pending" || status === "processing")) {
      
      pollingInterval = setInterval(async () => {
        try {
          const response = await fetch(`http://127.0.0.1:8000/videos/${videoId}/status`);
          
          if (response.ok) {
            const data: StatusResponse = await response.json();
            setProgress(data.progress);
            setStatus(data.status);

            // If completed or failed, the interval will be cleared on the next render
            if (data.status === "completed" || data.status === "failed") {
              console.log(`Processing finished with status: ${data.status}`);
            }
          }
        } catch (error) {
          console.error("Error fetching status:", error);
        }
      }, 1000); // Ask the server every 1 second
    }

    // Cleanup function: clear the interval when the component unmounts or dependencies change
    return () => {
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, [videoId, status]);

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col font-sans">
      
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 p-4 shadow-sm flex justify-between items-center">
        <h1 className="text-2xl font-bold text-blue-500 flex items-center gap-2">
          <span className="text-white">Sense</span>Clean
        </h1>

        <div>
          <button 
            onClick={handleStartProcessing}
            disabled={isRequesting || status === "processing"}
            className={`px-4 py-2 rounded-md font-semibold transition-colors ${
              isRequesting || status === "processing" 
                ? "bg-gray-600 cursor-not-allowed text-gray-300" 
                : "bg-blue-600 hover:bg-blue-500 text-white cursor-pointer"
            }`}
          >
            {status === "processing" ? "Processing..." : "Start Video Process"}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center p-6 gap-6 w-full max-w-5xl mx-auto">
        
        {/* Progress Bar UI */}
        {(status === "processing" || status === "completed") && (
          <div className="w-full bg-gray-800 rounded-full h-4 mb-4 border border-gray-700 overflow-hidden">
            <div 
              className="bg-blue-500 h-4 rounded-full transition-all duration-500 ease-out" 
              style={{ width: `${progress}%` }}
            ></div>
            <p className="text-center text-xs mt-1 text-gray-400">{Math.round(progress)}%</p>
          </div>
        )}

        {/* Video Player / Stream Viewer */}
        <div className="w-full bg-gray-900 rounded-xl border border-gray-800 overflow-hidden shadow-2xl relative">
          
          <div className="px-4 py-2 bg-gray-950/50 border-b border-gray-800 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${status === "processing" ? "bg-red-500 animate-pulse" : "bg-gray-500"}`}></div>
              <span className="text-xs text-gray-300 font-medium">
                {status === "processing" ? "LIVE STREAM" : "OFFLINE"}
              </span>
            </div>
            <div className="text-xs text-gray-500 font-mono">ID: {videoId || "N/A"}</div>
          </div>

          <div className="relative w-full aspect-video bg-black flex justify-center items-center">
            
            {/* 4. The MJPEG Stream Receiver 
              It only mounts when the backend confirms it's in "processing" state.
            */}
            {status === "processing" && videoId ? (
              <img 
                src={`http://127.0.0.1:8000/videos/${videoId}/stream`} 
                alt="SenseVision Stream" 
                className="w-full h-full object-contain"
              />
            ) : status === "completed" ? (
              <span className="text-green-500 font-semibold">Processing Completed Successfully!</span>
            ) : status === "failed" ? (
              <span className="text-red-500 font-semibold">Processing Failed. Check server logs.</span>
            ) : (
              <span className="text-gray-600">Click "Start Video Process" to begin.</span>
            )}
            
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;