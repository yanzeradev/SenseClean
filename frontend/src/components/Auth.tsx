import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Video, Loader2, AlertCircle, Ticket } from "lucide-react"; // Adicionei o ícone Ticket
import { api } from "@/lib/api";

interface AuthProps {
  onLoginSuccess: (email: string) => void;
}

export function Auth({ onLoginSuccess }: AuthProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [inviteCode, setInviteCode] = useState(''); // Estado já criado por você

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (isLogin) {
        // Rota de Login
        const res = await api.post("/auth/login", { email, password });
        localStorage.setItem("senseclean_token", res.access_token);
        localStorage.setItem("senseclean_user", res.email);
        onLoginSuccess(res.email);
      } else {
        // 💥 Rota de Cadastro: Agora enviando o invite_code
        await api.post("/auth/register", { 
          email, 
          password, 
          invite_code: inviteCode 
        });
        
        setIsLogin(true);
        setError('');
        setInviteCode(''); // Limpa o código após sucesso
        alert("Conta criada com sucesso! Faça login para entrar.");
      }
    } catch (err: any) {
      try {
        const errorData = JSON.parse(err.message);
        setError(errorData.detail || "Erro na autenticação.");
      } catch {
        setError("Erro de conexão com o servidor.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center shadow-lg shadow-primary/20">
          <Video className="text-primary-foreground w-7 h-7" />
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-white">SenseClean</h1>
      </div>

      <Card className="w-full max-w-md bg-card/50 backdrop-blur-xl border-gray-800 shadow-2xl">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl text-center">
            {isLogin ? 'Bem-vindo de volta' : 'Criar nova conta'}
          </CardTitle>
          <CardDescription className="text-center">
            {isLogin 
              ? 'Digite suas credenciais para acessar o painel' 
              : 'Registre-se para iniciar a análise inteligente'}
          </CardDescription>
        </CardHeader>
        
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            
            {error && (
              <div className="p-3 rounded-md bg-destructive/10 border border-destructive/20 flex items-center gap-2 text-destructive text-sm">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <p>{error}</p>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">E-mail</Label>
              <Input 
                id="email" 
                type="email" 
                placeholder="seu@email.com" 
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-background/50"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="password">Senha</Label>
              <Input 
                id="password" 
                type="password" 
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-background/50"
              />
            </div>

            {/* 💥 NOVO CAMPO: Código de Convite (Aparece apenas no Registro) */}
            {!isLogin && (
              <div className="space-y-2 animate-in fade-in slide-in-from-top-2 duration-300">
                <Label htmlFor="inviteCode" className="flex items-center gap-2">
                  <Ticket className="w-3 h-3 text-primary" /> Código de Convite
                </Label>
                <Input 
                  id="inviteCode" 
                  type="text" 
                  placeholder="Digite o código enviado pela Sense" 
                  required
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  className="bg-primary/5 border-primary/20"
                />
              </div>
            )}
          </CardContent>
          
          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full h-11 text-base font-medium" disabled={loading}>
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (isLogin ? 'Entrar' : 'Cadastrar')}
            </Button>
            
            <div className="text-sm text-center text-muted-foreground">
              {isLogin ? "Não tem uma conta? " : "Já possui uma conta? "}
              <button 
                type="button" 
                onClick={() => { setIsLogin(!isLogin); setError(''); }}
                className="text-primary hover:underline font-medium focus:outline-none"
              >
                {isLogin ? 'Registre-se' : 'Faça login'}
              </button>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}