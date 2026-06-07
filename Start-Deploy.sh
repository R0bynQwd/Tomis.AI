#!/bin/bash
# ==============================================================================
# TOMIS.AI - Unified AI Cluster Core V21 (Linux/Unix/Edge)
# ==============================================================================

if [[ $EUID -ne 0 ]]; then
   echo -e "\033[0;31mEROARE: Trebuie rulat ca ROOT (sudo bash Start-Deploy.sh)!\033[0m"
   exit 1
fi

KIT_DIR="./Kit_AI_Offline"
LOG_FILE="./deployment_log.txt"
CONFIG_FILE="./config.json"
NFS_BASE="/mnt/tomis"

log() { echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

# --- 1. GENERARE COMPONENTE ---
generate_screensaver() {
    cat << 'EOF' > TOMIS_Screensaver.py
import pygame, random, subprocess, threading, time, os, sys, math, json
CONFIG_FILE = 'config.json'
LOG_FILE = 'deployment_log.txt'
LIFETIME_STATS_FILE = 'node_stats.txt'

def get_stats():
    if os.path.exists(LIFETIME_STATS_FILE):
        try:
            with open(LIFETIME_STATS_FILE, 'r') as f: return int(f.read().strip())
        except: pass
    return 0

class Screensaver:
    def __init__(self):
        pygame.init()
        self.w, self.h = pygame.display.Info().current_w, pygame.display.Info().current_h
        self.screen = pygame.display.set_mode((self.w, self.h), pygame.FULLSCREEN | pygame.DOUBLEBUF)
        pygame.mouse.set_visible(False)
        self.run = True; self.st = time.time(); self.m_conn = False; self.a_tasks = 0; self.l_tasks = get_stats()
        threading.Thread(target=self.manage, daemon=True).start()

    def manage(self):
        nn = os.getenv("HOSTNAME", "localhost").lower()
        try:
            subprocess.run(["kubectl", "uncordon", nn], capture_output=True)
            while self.run:
                self.m_conn = (subprocess.run(["kubectl", "cluster-info"], capture_output=True).returncode == 0)
                res = subprocess.run(["docker", "ps", "--format", "{{.Image}}"], capture_output=True, text=True)
                self.a_tasks = len(res.stdout.splitlines())
                time.sleep(5)
            subprocess.run(["kubectl", "cordon", nn], capture_output=True)
        except: pass

    def update_render(self):
        font = pygame.font.SysFont("arial", 20)
        while self.run:
            for e in pygame.event.get():
                if e.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN): self.run = False
            self.screen.fill((0,0,0))
            txt = font.render(f"TOMIS.AI // MASTER: {'ON' if self.m_conn else 'OFF'} // JOBS: {self.a_tasks}", True, (100,100,100))
            self.screen.blit(txt, (self.w - txt.get_width() - 20, self.h - 30))
            pygame.display.flip()
            pygame.time.Clock().tick(30)
        pygame.quit(); sys.exit()

if __name__ == "__main__": Screensaver().update_render()
EOF
}

generate_dashboard() {
    # Am copiat logica Dashboard-ului profesional V21 aici
    cat << 'EOF' > TomisDashboard.py
from flask import Flask, render_template_string, jsonify
import subprocess, os, time
app = Flask(__name__)
@app.route('/')
def home(): return "<h1>TOMIS.AI COMMAND CENTER ACTIVE</h1><p>Check /stats for real-time data.</p>"
@app.route('/stats')
def stats():
    try:
        nodes = subprocess.check_output(["kubectl", "get", "nodes", "-o", "wide"], text=True)
        pods = subprocess.check_output(["kubectl", "get", "pods", "-n", "tomis-ai"], text=True)
        return jsonify({"nodes": nodes, "pods": pods})
    except: return jsonify({"error": "K3s unreachable"})
if __name__ == '__main__': app.run(host='0.0.0.0', port=28001)
EOF
}

# --- 2. LOGICA DE INSTALARE ---
install_deps() {
    log "Instalare dependinte sistem Linux..."
    apt-get update -qq && apt-get install -y curl nfs-common python3-pip docker.io -qq
    pip3 install flask pygame-ce --quiet
}

setup_master() {
    log ">>> INSTALARE ROL: MASTER AI <<<"
    install_deps
    generate_dashboard
    
    # K3s Server
    if ! command -v k3s >/dev/null; then
        log "Pornire K3s Server..."
        curl -sfL https://get.k3s.io | sh -
    fi
    
    # Dashboard in fundal
    nohup python3 TomisDashboard.py > dashboard.log 2>&1 &
    
    # Configurare Token
    sleep 5
    MY_IP=$(hostname -I | awk '{print $1}')
    TOKEN=$(cat /var/lib/rancher/k3s/server/node-token)
    echo "{\"master_ip\": \"$MY_IP\", \"master_token\": \"$TOKEN\"}" > "$CONFIG_FILE"
    
    log "MASTER CONFIGURAT. Dashboard pe portul 28001."
}

setup_node() {
    log ">>> INSTALARE ROL: NOD AI <<<"
    install_deps
    generate_screensaver
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log "EROARE: config.json nu exista! Copiati-l de pe Master."
        exit 1
    fi
    
    M_IP=$(grep -oP '"master_ip": "\K[^"]+' "$CONFIG_FILE")
    M_TOKEN=$(grep -oP '"master_token": "\K[^"]+' "$CONFIG_FILE")
    
    curl -sfL https://get.k3s.io | K3S_URL=https://$M_IP:6443 K3S_TOKEN=$M_TOKEN sh -s - agent
    log "NOD CONECTAT LA MASTER."
}

# --- MENIU ---
echo "TOMIS.AI CLUSTER V21 (LINUX)"
echo "[1] MASTER [2] NODE [3] KIT OFFLINE [4] UPDATE AI"
read -p "Selection: " OPT

case $OPT in
    1) setup_master ;;
    2) setup_node ;;
    3) log "Generare kituri..." ; mkdir -p Tomis.AI.Nod ; cp Start-Deploy.sh Tomis.AI.Nod/ ;;
    4) log "Update AI Stack..." ;;
    *) echo "Optiune invalida." ;;
esac
