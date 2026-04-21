# pyinstaller --noconsole --onefile --name "SenseVisionAgent" install.py
import os
import sys
import time
import socket
import requests
import subprocess
import urllib.request
import ctypes
import json
import customtkinter as ctk  # 💥 A NOVA MÁGICA VISUAL
from tkinter import messagebox

# ============================================================================
# ⚙️ CONFIGURAÇÕES & CONSTANTES
# ============================================================================

TAILSCALE_AUTH_KEY = "tskey-auth-kU3nQ4eqN521CNTRL-FHB5wzGYNrVmnjqQfzzMqVpbFpLhDyKw" # <--- COLOQUE SUA CHAVE AQUI
API_BASE_URL = "http://137.131.224.146/api" # <--- IP DA SUA NUVEM
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sense_agent.log")

CREATE_NO_WINDOW = 0x08000000

# ============================================================================
# 🛠️ UTILITÁRIOS
# ============================================================================

def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(entry + "\n")
    except: pass

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def save_config(token, email):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"api_token": token, "email": email}, f)

def load_config():
    if not os.path.exists(CONFIG_FILE): return None
    try:
        with open(CONFIG_FILE, "r") as f: return json.load(f)
    except: return None

# ============================================================================
# 🚀 INFRAESTRUTURA: TAILSCALE E SUBNET ROUTING
# ============================================================================

def install_tailscale():
    if not os.path.exists(r"C:\Program Files\Tailscale\tailscale.exe"):
        try:
            log("Baixando Tailscale...")
            urllib.request.urlretrieve("https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe", "ts-setup.exe")
            log("Instalando Tailscale...")
            subprocess.run(["ts-setup.exe", "/quiet", "/norestart"], check=True, creationflags=CREATE_NO_WINDOW)
            time.sleep(10)
            if os.path.exists("ts-setup.exe"): os.remove("ts-setup.exe")
        except Exception as e: 
            log(f"Erro ao instalar Tailscale: {e}")
            return False
    return True

def configure_tailscale():
    ts = r"C:\Program Files\Tailscale\tailscale.exe"
    subprocess.run([ts, "logout"], stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
    
    hostname = f"cliente-{socket.gethostname()}"
    
    # 💥 A BALA DE PRATA: Advertise Routes!
    # Isso diz ao Tailscale para pegar o tráfego da Oracle e jogar para as câmeras na rede local
    routes = "192.168.0.0/24,192.168.1.0/24,10.0.0.0/24"
    
    cmd = [
        ts, "up", 
        "--authkey", TAILSCALE_AUTH_KEY, 
        "--hostname", hostname, 
        "--advertise-routes", routes, 
        "--unattended", "--force-reauth", "--reset"
    ]
    
    try:
        log("Conectando à malha da SenseClean...")
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, creationflags=CREATE_NO_WINDOW)
        return True
    except Exception as e: 
        log(f"Erro no Tailscale: {e}")
        return False

# ============================================================================
# 🔐 INTERFACE GRÁFICA MODERNA (CUSTOM TKINTER)
# ============================================================================

def show_login_gui():
    ctk.set_appearance_mode("Dark")  # Modo Escuro
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("SenseClean Agent")
    root.geometry("400x450")
    root.resizable(False, False)
    
    # Centralizar a janela
    x = int((root.winfo_screenwidth() / 2) - (400 / 2))
    y = int((root.winfo_screenheight() / 2) - (450 / 2))
    root.geometry(f"+{x}+{y}")

    def perform_login():
        email = entry_email.get()
        password = entry_pass.get()
        
        if not email or not password:
            messagebox.showwarning("Atenção", "Preencha e-mail e senha.")
            return

        btn_entrar.configure(state="disabled", text="Conectando à Nuvem...")
        root.update()

        try:
            # 💥 Rota atualizada para o nosso FastAPI
            payload = {"email": email, "password": password}
            resp = requests.post(f"{API_BASE_URL}/auth/login", json=payload, timeout=10)
            
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                save_config(token, email)
                
                # Feedback visual bonito
                btn_entrar.configure(text="Sucesso! Configurando rede...", fg_color="green")
                root.update()
                time.sleep(1)
                root.destroy() 
            else:
                messagebox.showerror("Acesso Negado", "E-mail ou senha incorretos.")
                btn_entrar.configure(state="normal", text="Entrar e Ativar Computador")
        except Exception as e:
            messagebox.showerror("Erro de Rede", f"Não foi possível conectar ao servidor Oracle.\nVerifique sua internet.")
            btn_entrar.configure(state="normal", text="Entrar e Ativar Computador")

    # Design da Tela
    lbl_title = ctk.CTkLabel(root, text="SenseClean", font=ctk.CTkFont(size=24, weight="bold"))
    lbl_title.pack(pady=(40, 5))
    
    lbl_subtitle = ctk.CTkLabel(root, text="Autentique-se para plugar as câmeras na IA.", font=ctk.CTkFont(size=12), text_color="gray")
    lbl_subtitle.pack(pady=(0, 30))

    entry_email = ctk.CTkEntry(root, placeholder_text="Seu E-mail", width=300, height=40)
    entry_email.pack(pady=10)

    entry_pass = ctk.CTkEntry(root, placeholder_text="Sua Senha", show="*", width=300, height=40)
    entry_pass.pack(pady=10)

    btn_entrar = ctk.CTkButton(root, text="Entrar e Ativar Computador", command=perform_login, width=300, height=45, font=ctk.CTkFont(weight="bold"))
    btn_entrar.pack(pady=30)

    root.mainloop()

# ============================================================================
# 🏁 LOOP PRINCIPAL DO SERVIÇO
# ============================================================================

def service_loop():
    log("🚀 Iniciando SenseClean Agent Service...")
    
    config = load_config()
    while not config:
        time.sleep(10)
        config = load_config()
    
    log(f"👤 Autenticado como: {config.get('email')}")

    install_tailscale()
    configure_tailscale()

    os.system("powercfg /change standby-timeout-ac 0")
    log("🟢 Agente em operação. Roteamento de Sub-rede Ativo.")
    
    # O loop agora é super leve, só serve para manter o script .exe do InnoSetup aberto
    while True:
        time.sleep(60)

def main():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        return
    
    if len(sys.argv) > 1 and sys.argv[1] == "--configure":
        show_login_gui()
        if load_config(): service_loop()
    else:
        if not load_config(): show_login_gui()
        if load_config(): service_loop()

if __name__ == "__main__":
    main()