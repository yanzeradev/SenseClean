import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LayoutDashboard, Video, Camera, Settings } from "lucide-react";
import { VideoAnalysis } from "@/components/VideoAnalysis";
// Deixaremos esses como mock provisório até implementarmos a Fase 8 de verdade
import { Dashboard } from "@/components/Dashboard";

export default function App() {
  const [activeTab, setActiveTab] = useState("analysis");

  return (
    <div className="min-h-screen bg-background flex flex-col font-sans">
      <header className="border-b bg-card px-6 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <Video className="text-primary-foreground w-5 h-5" />
          </div>
          <h1 className="text-xl font-bold tracking-tight">SenseClean</h1>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">Admin</span>
        </div>
      </header>

      <main className="flex-1 container mx-auto py-6 px-4 max-w-6xl flex flex-col items-center">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-col space-y-6 w-full">
          <div className="flex items-center justify-center w-full">
            <TabsList className="grid grid-cols-4 w-full max-w-[650px]">
              <TabsTrigger value="dashboard" className="gap-2">
                <LayoutDashboard className="w-4 h-4" />
                Histórico
              </TabsTrigger>
              <TabsTrigger value="analysis" className="gap-2">
                <Video className="w-4 h-4" />
                Análise de Vídeo
              </TabsTrigger>
              <TabsTrigger value="devices" className="gap-2">
                <Camera className="w-4 h-4" />
                Câmeras
              </TabsTrigger>
              <TabsTrigger value="settings" className="gap-2">
                <Settings className="w-4 h-4" />
                Config
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="dashboard" className="space-y-4">
            <Dashboard />
          </TabsContent>
          <TabsContent value="analysis">
             {/* AQUI ENTRA A NOSSA LÓGICA MÁGICA DE CANVAS E UPLOAD */}
            <VideoAnalysis />
          </TabsContent>
          <TabsContent value="devices">
            <div className="flex items-center justify-center h-[400px] text-muted-foreground">
              Gerenciamento de Câmeras RTSP (Fase 9 em breve).
            </div>
          </TabsContent>
          <TabsContent value="settings">
            <div className="flex items-center justify-center h-[400px] text-muted-foreground">
              Configurações do sistema.
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}