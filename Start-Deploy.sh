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
K3S_VERSION_COMPAT="v1.24.17+k3s1"

log() { echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

# --- 1. GENERARE COMPONENTE ---
generate_screensaver() {
    if [[ -f TOMIS_Screensaver.py ]]; then
        log "Using existing TOMIS_Screensaver.py (skip embedded template)."
        return
    fi
    cat << 'EOF' > TOMIS_Screensaver.py
import json
import math
import os
import random
import subprocess
import sys
import threading
import time

import pygame

CONFIG_FILE = 'config.json'
LOG_FILE = 'deployment_log.txt'
LIFETIME_STATS_FILE = 'node_stats.txt'
TASK_EMULATION_FILE = 'task_emulation.json'
ACTIVE_STATES = {'Running', 'Pending', 'ContainerCreating', 'CrashLoopBackOff'}

def get_stats():
    if os.path.exists(LIFETIME_STATS_FILE):
        try:
            with open(LIFETIME_STATS_FILE, 'r', encoding='utf-8') as f:
                return int(f.read().strip())
        except Exception:
            pass
    return 0

def count_active_tasks():
    emulated = 0
    if os.path.exists(TASK_EMULATION_FILE):
        try:
            with open(TASK_EMULATION_FILE, 'r', encoding='utf-8') as f:
                emulated = int(json.load(f).get('active_tasks', 0))
        except Exception:
            emulated = 0

    try:
        res = subprocess.run(['kubectl', 'get', 'pods', '-A', '--no-headers'], capture_output=True, text=True)
        if res.returncode != 0:
            return emulated
        count = 0
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[3] in ACTIVE_STATES:
                count += 1
        return max(count, emulated)
    except Exception:
        return emulated

def make_particle(w, h):
    angle = random.uniform(0, math.tau)
    speed = random.uniform(0.08, 0.55)
    return {
        'x': w / 2 + random.uniform(-120, 120),
        'y': h / 2 + random.uniform(-120, 120),
        'vx': math.cos(angle) * speed,
        'vy': math.sin(angle) * speed,
        'color': random.choice([(0, 140, 255), (0, 220, 180), (140, 80, 255), (80, 180, 255)]),
        'size': random.randint(1, 3),
        'life': random.randint(220, 520),
    }

class Screensaver:
    def __init__(self):
        pygame.init()
        self.w, self.h = pygame.display.Info().current_w, pygame.display.Info().current_h
        self.screen = pygame.display.set_mode((self.w, self.h), pygame.FULLSCREEN | pygame.DOUBLEBUF)
        pygame.mouse.set_visible(False)
        self.run = True
        self.st = time.time()
        self.m_conn = False
        self.a_tasks = 0
        self.l_tasks = get_stats()
        self.node_name = os.getenv('HOSTNAME', 'localhost').lower()
        self.center = (self.w // 2, self.h // 2)
        self.particles = [make_particle(self.w, self.h) for _ in range(95)]
        threading.Thread(target=self.manage, daemon=True).start()

    def manage(self):
        try:
            subprocess.run(['kubectl', 'uncordon', self.node_name], capture_output=True)
            while self.run:
                self.m_conn = (subprocess.run(['kubectl', 'cluster-info'], capture_output=True).returncode == 0)
                self.a_tasks = count_active_tasks()
                time.sleep(5)
        finally:
            subprocess.run(['kubectl', 'cordon', self.node_name], capture_output=True)

    def draw_panel(self):
        panel = pygame.Surface((420, 96), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 140))
        pygame.draw.rect(panel, (0, 160, 255, 160), panel.get_rect(), 1, border_radius=12)
        font = pygame.font.SysFont('segoeui', 20, bold=True)
        small = pygame.font.SysFont('segoeui', 16)
        panel.blit(font.render('TOMIS.AI // NEURAL CORE', True, (180, 220, 255)), (16, 10))
        panel.blit(small.render(f"MASTER: {'ON' if self.m_conn else 'OFF'}", True, (220, 220, 220)), (16, 42))
        panel.blit(small.render(f'ACTIVE TASKS: {self.a_tasks}   LIFETIME: {self.l_tasks}', True, (220, 220, 220)), (16, 62))
        self.screen.blit(panel, (24, self.h - 120))

    def update_particles(self):
        t = time.time() - self.st
        pulse = 95 + int(24 * math.sin(t * 1.0))
        pygame.draw.circle(self.screen, (0, 90, 180), self.center, pulse, 2)
        pygame.draw.circle(self.screen, (0, 180, 255), self.center, pulse // 2, 1)

        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
            if p['life'] <= 0 or p['x'] < -20 or p['x'] > self.w + 20 or p['y'] < -20 or p['y'] > self.h + 20:
                p.update(make_particle(self.w, self.h))
            pygame.draw.aaline(self.screen, p['color'], self.center, (int(p['x']), int(p['y'])))
            pygame.draw.circle(self.screen, p['color'], (int(p['x']), int(p['y'])), p['size'])

    def update_render(self):
        while self.run:
            for e in pygame.event.get():
                if e.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    self.run = False
            self.screen.fill((3, 4, 10))
            self.update_particles()
            self.draw_panel()
            pygame.display.flip()
            pygame.time.Clock().tick(30)
        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    Screensaver().update_render()
EOF
}

generate_dashboard() {
    if [[ -f TomisDashboard.py ]]; then
        log "Using existing TomisDashboard.py (skip embedded template)."
        return
    fi
    # Am copiat logica Dashboard-ului profesional V21 aici
    cat << 'EOF' > TomisDashboard.py
import json
from flask import Flask, jsonify
import os, subprocess

app = Flask(__name__)
TASK_EMULATION_FILE = 'task_emulation.json'
ACTIVE_STATES = {'Running', 'Pending', 'ContainerCreating', 'CrashLoopBackOff'}

def kubectl_output(args):
    return subprocess.check_output(['kubectl', *args], text=True)

def count_active_tasks():
    emulated = 0
    if os.path.exists(TASK_EMULATION_FILE):
        try:
            with open(TASK_EMULATION_FILE, 'r', encoding='utf-8') as f:
                emulated = int(json.load(f).get('active_tasks', 0))
        except Exception:
            emulated = 0

    try:
        out = kubectl_output(['get', 'pods', '-A', '--no-headers'])
        total = 0
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[3] in ACTIVE_STATES:
                total += 1
        return max(total, emulated)
    except Exception:
        return emulated

@app.route('/')
def home():
    return "<h1>TOMIS.AI COMMAND CENTER ACTIVE</h1><p>Check /stats for live cluster data.</p>"

@app.route('/stats')
def stats():
    try:
        nodes = kubectl_output(['get', 'nodes', '-o', 'wide'])
        pods = kubectl_output(['get', 'pods', '-A'])
        return jsonify({
            'node_name': os.getenv('HOSTNAME', 'unknown'),
            'active_tasks': count_active_tasks(),
            'emulated_tasks': os.path.exists(TASK_EMULATION_FILE),
            'nodes': nodes,
            'pods': pods
        })
    except Exception as exc:
        return jsonify({'error': f'K3s unreachable: {exc}'}), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=28001)
EOF
}

# --- 2. LOGICA DE INSTALARE ---
install_deps() {
    log "Instalare dependinte sistem Linux..."
    apt-get update -qq && apt-get install -y curl nfs-common python3-pip docker.io -qq
    pip3 install flask pygame-ce --quiet
}

has_gui() {
    [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]
}

ensure_memory_cgroup() {
    if grep -q 'Raspberry Pi' /proc/device-tree/model 2>/dev/null; then
        if ! grep -q 'cgroup_memory=1' /boot/cmdline.txt 2>/dev/null; then
            log "Activez memory cgroup pentru Raspberry Pi (necesita reboot)."
            sed -i '1 s|$| cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1|' /boot/cmdline.txt
            touch /var/run/tomis-reboot-required
        fi
    fi
}

master_api_reachable() {
    local ip="$1"
    timeout 3 bash -lc "cat < /dev/null > /dev/tcp/${ip}/6443" >/dev/null 2>&1
}

write_node_capabilities() {
    local cap_file="./node_capabilities.json"
    local cpu mem gpu runtime
    cpu=$(nproc 2>/dev/null || echo 0)
    mem=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)
    gpu="false"
    runtime="runc"
    if command -v nvidia-container-runtime >/dev/null 2>&1; then
        gpu="true"
        runtime="nvidia"
    fi
    cat > "$cap_file" <<EOF
{"cpu_cores": $cpu, "memory_mb": $mem, "gpu_available": $gpu, "preferred_runtime": "$runtime"}
EOF
    log "Capabilitati hardware detectate dinamic: CPU=${cpu}, RAM=${mem}MB, GPU=${gpu}, runtime=${runtime}"
}

diagnose_gpu() {
    log "=== GPU DIAGNOSTICS ==="
    local node_name="${1:-$(hostname)}"
    
    if [[ -f /proc/device-tree/model ]] && grep -q "Jetson" /proc/device-tree/model; then
        log "[JETSON DETECTED] Checking NVIDIA tools..."
        if ! command -v nvidia-smi &> /dev/null; then
            log "[WARNING] nvidia-smi not found! Install with:"
            log "   sudo apt-get install -y nvidia-utils nvidia-cuda-toolkit"
            return 1
        else
            log "[OK] NVIDIA tools available"
            nvidia-smi --query-gpu=index,name,driver_version --format=csv,noheader | while read line; do
                log "  GPU: $line"
            done
            return 0
        fi
    fi
    
    if [[ -f /sys/devices/virtual/dmi/id/board_name ]] && grep -q "Raspberry" /sys/devices/virtual/dmi/id/board_name 2>/dev/null; then
        log "[RASPBERRY PI DETECTED] CPU-only mode (no GPU)"
        return 0
    fi
    
    if [[ -c /dev/nvidia0 ]]; then
        log "[GPU DEVICE FOUND] /dev/nvidia0 exists"
        if command -v tegrastats &> /dev/null; then
            log "  tegrastats available - GPU ready"
            return 0
        fi
    fi
    
    log "[INFO] No GPU detected on this node"
    return 0
}

validate_gpu_workload() {
    local node_name="${1:-$(hostname)}"
    log "=== GPU WORKLOAD VALIDATION: $node_name ==="
    
    if ! command -v nvidia-smi &> /dev/null; then
        log "[SKIP] nvidia-smi not available; skipping GPU test"
        return 0
    fi
    
    # Test CUDA availability
    if python3 -c "import cupy; print('CuPy OK')" 2>/dev/null | grep -q OK; then
        log "[OK] CuPy (GPU acceleration) available"
        return 0
    fi
    
    # Fallback to checking if drivers load
    if dmesg | grep -i nvidia | head -1 2>/dev/null; then
        log "[OK] NVIDIA drivers loaded in kernel"
        return 0
    fi
    
    log "[WARNING] GPU drivers may not be properly loaded"
    return 1
}

start_screensaver() {
    if has_gui; then
        if pgrep -f "TOMIS_Screensaver.py" >/dev/null 2>&1; then
            log "Screensaver already running; skipping start."
        else
            nohup python3 TOMIS_Screensaver.py > screensaver.log 2>&1 &
            log "Screensaver pornit pentru sesiune GUI."
        fi
    else
        log "Fara GUI detectat; nodul ramane activ fara screensaver."
    fi
}

setup_master() {
    log ">>> INSTALARE ROL: MASTER AI <<<"
    install_deps
    generate_dashboard
    
    # K3s Server
    if ! command -v k3s >/dev/null; then
        log "Pornire K3s Server..."
        curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="$K3S_VERSION_COMPAT" sh -
    fi
    
    # Dashboard in fundal
    nohup python3 TomisDashboard.py > dashboard.log 2>&1 &
    
    # Configurare Token
    sleep 5
    MY_IP=$(hostname -I | awk '{print $1}')
    TOKEN=$(cat /var/lib/rancher/k3s/server/node-token)
    echo "{\"master_ip\": \"$MY_IP\", \"master_token\": \"$TOKEN\"}" > "$CONFIG_FILE"
    start_screensaver
    
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

    write_node_capabilities
    ensure_memory_cgroup
    
    # GPU DIAGNOSTICS
    log ""
    diagnose_gpu
    validate_gpu_workload
    log ""

    if [[ -z "$M_IP" || -z "$M_TOKEN" ]]; then
        log "Config invalid (master_ip/master_token lipsa). Trecere in mod EDGE_STANDALONE."
        systemctl stop k3s-agent >/dev/null 2>&1 || true
        systemctl disable k3s-agent >/dev/null 2>&1 || true
        start_screensaver
        log "NOD ACTIV in mod standalone GPU/container-centric (fara join K3s)."
        return
    fi

    if ! master_api_reachable "$M_IP"; then
        log "API K3s master ($M_IP:6443) inaccesibil. Trecere in mod EDGE_STANDALONE."
        systemctl stop k3s-agent >/dev/null 2>&1 || true
        systemctl disable k3s-agent >/dev/null 2>&1 || true
        start_screensaver
        log "NOD ACTIV in mod standalone GPU/container-centric (fara join K3s)."
        return
    fi

    curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="$K3S_VERSION_COMPAT" K3S_URL=https://$M_IP:6443 K3S_TOKEN=$M_TOKEN sh -s - agent
    systemctl enable --now k3s-agent >/dev/null 2>&1 || true
    if [[ -f /var/run/tomis-reboot-required ]]; then
        log "Reboot necesar pentru activare memory cgroup. Rulez reboot in 5 secunde."
        sleep 5
        reboot
    fi
    start_screensaver
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
