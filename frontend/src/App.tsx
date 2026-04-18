import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LayoutDashboard, Video, Camera, Settings, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";

// Imports dos componentes
import { VideoAnalysis } from "./components/VideoAnalysis";
import { Dashboard } from "./components/Dashboard";
import { DeviceList } from "./components/DeviceList";
import { Auth } from "./components/Auth"; // 💥 NOSSO NOVO COMPONENTE

export default function App() {
  const [activeTab, setActiveTab] = useState("analysis");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userEmail, setUserEmail] = useState<string>('');

  // Verifica se já existe um login salvo ao abrir a página
  useEffect(() => {
    const token = localStorage.getItem("senseclean_token");
    const email = localStorage.getItem("senseclean_user");
    if (token && email) {
      setIsAuthenticated(true);
      setUserEmail(email);
    }
  }, []);

  const handleLoginSuccess = (email: string) => {
    setIsAuthenticated(true);
    setUserEmail(email);
  };

  const handleLogout = () => {
    localStorage.removeItem("senseclean_token");
    localStorage.removeItem("senseclean_user");
    setIsAuthenticated(false);
    setUserEmail('');
  };

  // 💥 SE NÃO ESTIVER LOGADO, MOSTRA APENAS A TELA DE LOGIN
  if (!isAuthenticated) {
    return <Auth onLoginSuccess={handleLoginSuccess} />;
  }

  // 💥 SE ESTIVER LOGADO, MOSTRA O SISTEMA
  return (
    <div className="min-h-screen bg-background flex flex-col font-sans">
      <header className="border-b bg-card px-6 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <Video className="text-primary-foreground w-5 h-5" />
          </div>
          <h1 className="text-xl font-bold tracking-tight">SenseClean</h1>
        </div>
        
        {/* Painel do Usuário Logado */}
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-muted-foreground bg-secondary/50 px-3 py-1 rounded-full">
            {userEmail}
          </span>
          <Button variant="ghost" size="icon" onClick={handleLogout} title="Sair" className="text-red-400 hover:text-red-300 hover:bg-red-950/30">
            <LogOut className="w-5 h-5" />
          </Button>
        </div>
      </header>

      <main className="flex-1 container mx-auto py-6 px-4 max-w-6xl flex flex-col items-center">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-col space-y-6 w-full">
          <div className="flex items-center justify-center w-full">
            <TabsList className="grid grid-cols-4 w-full max-w-[650px]">
              <TabsTrigger value="dashboard" className="gap-2">
                <LayoutDashboard className="w-4 h-4" /> Histórico
              </TabsTrigger>
              <TabsTrigger value="analysis" className="gap-2">
                <Video className="w-4 h-4" /> Análise de Vídeo
              </TabsTrigger>
              <TabsTrigger value="devices" className="gap-2">
                <Camera className="w-4 h-4" /> Câmeras
              </TabsTrigger>
              <TabsTrigger value="settings" className="gap-2">
                <Settings className="w-4 h-4" /> Config
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="dashboard" className="space-y-4"><Dashboard /></TabsContent>
          <TabsContent value="analysis"><VideoAnalysis /></TabsContent>
          <TabsContent value="devices"><DeviceList /></TabsContent>
          <TabsContent value="settings">
            <div className="flex items-center justify-center h-[400px] text-muted-foreground">Configurações do sistema.</div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}