param(
    [Parameter(Mandatory=$true)] [string]$Role,
    [Parameter(Mandatory=$false)] [string]$MasterIP = "",
    [Parameter(Mandatory=$false)] [string]$Token = ""
)

$ErrorActionPreference = 'Stop'

$Global:LogFile = Join-Path $PSScriptRoot "deployment_log.txt"
$Global:KitDir = Join-Path $PSScriptRoot "Kit_AI_Offline"
$Global:ConfigFile = Join-Path $PSScriptRoot "config.json"
$Global:K3sImage = "rancher/k3s:v1.24.17-k3s1"

function Log-Message {
    param([string]$Message)
    $TimeStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Line = "[$TimeStamp] $Message"
    Write-Host $Line
    Add-Content -Path $Global:LogFile -Value $Line -ErrorAction SilentlyContinue
}

function Create-Directories {
    if (!(Test-Path $Global:KitDir)) { New-Item -ItemType Directory -Path $Global:KitDir | Out-Null }
    $ModelDir = Join-Path $Global:KitDir "Models"
    if (!(Test-Path $ModelDir)) { New-Item -ItemType Directory -Path $ModelDir | Out-Null }
}

function Get-PythonExecutable {
    (Get-Command python -ErrorAction Stop).Source
}

function Test-GuiAvailable {
    return [bool](Get-Process explorer -ErrorAction SilentlyContinue)
}

function Get-PhysicalIPv4Address {
    $candidate = Get-NetIPConfiguration -ErrorAction SilentlyContinue |
        Where-Object {
            $_.NetAdapter -and
            $_.NetAdapter.Status -eq 'Up' -and
            $_.IPv4Address -and
            $_.IPv4DefaultGateway -and
            $_.InterfaceAlias -notmatch 'Loopback|vEthernet|Docker|Virtual|Hyper-V|Bluetooth|Wi-Fi Direct|Teredo|TAP|VMware'
        } |
        ForEach-Object { $_.IPv4Address.IPAddress } |
        Where-Object { $_ -and $_ -ne '127.0.0.1' } |
        Select-Object -First 1

    if ($candidate) { return $candidate }

    $fallback = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -and
            $_.IPAddress -ne '127.0.0.1' -and
            $_.InterfaceAlias -notmatch 'Loopback|vEthernet|Docker|Virtual|Hyper-V|Bluetooth|Wi-Fi Direct|Teredo|TAP|VMware'
        } |
        Sort-Object InterfaceMetric |
        Select-Object -First 1

    if ($fallback) { return $fallback.IPAddress }

    throw "Could not resolve a physical IPv4 address."
}

function Test-ClusterExists {
    $cluster = kubectl get nodes --request-timeout=3s --no-headers 2>$null
    return [bool]$cluster
}

function Test-NodeExists {
    param([string]$NodeName)
    return [bool](kubectl get node $NodeName --request-timeout=3s --no-headers 2>$null)
}

function Generate-Screensaver {
    $ExistingScreensaver = Join-Path $PSScriptRoot "TOMIS_Screensaver.py"
    if (Test-Path $ExistingScreensaver) {
        Log-Message "Using existing TOMIS_Screensaver.py (skip embedded template)."
        return
    }
    $PyCode = @"
import json
import math
import os
import random
import subprocess
import sys
import threading
import time

import pygame

CONFIG_FILE = "config.json"
LOG_FILE = "deployment_log.txt"
LIFETIME_STATS_FILE = "node_stats.txt"
TASK_EMULATION_FILE = "task_emulation.json"
ACTIVE_STATES = {"Running", "Pending", "ContainerCreating", "CrashLoopBackOff"}


def get_stats():
    if os.path.exists(LIFETIME_STATS_FILE):
        try:
            with open(LIFETIME_STATS_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        except Exception:
            pass
    return 0


def count_active_tasks():
    emulated = 0
    if os.path.exists(TASK_EMULATION_FILE):
        try:
            with open(TASK_EMULATION_FILE, "r", encoding="utf-8") as f:
                emulated = int(json.load(f).get("active_tasks", 0))
        except Exception:
            emulated = 0

    try:
        res = subprocess.run(["kubectl", "get", "pods", "-A", "--no-headers"], capture_output=True, text=True)
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
        "x": w / 2 + random.uniform(-120, 120),
        "y": h / 2 + random.uniform(-120, 120),
        "vx": math.cos(angle) * speed,
        "vy": math.sin(angle) * speed,
        "color": random.choice([(0, 140, 255), (0, 220, 180), (140, 80, 255), (80, 180, 255)]),
        "size": random.randint(1, 3),
        "life": random.randint(220, 520),
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
        self.node_name = os.getenv("COMPUTERNAME", os.getenv("HOSTNAME", "localhost")).lower()
        self.center = (self.w // 2, self.h // 2)
        self.particles = [make_particle(self.w, self.h) for _ in range(95)]
        threading.Thread(target=self.manage, daemon=True).start()

    def manage(self):
        try:
            subprocess.run(["kubectl", "uncordon", self.node_name], capture_output=True)
            while self.run:
                self.m_conn = (subprocess.run(["kubectl", "cluster-info"], capture_output=True).returncode == 0)
                self.a_tasks = count_active_tasks()
                time.sleep(5)
        finally:
            subprocess.run(["kubectl", "cordon", self.node_name], capture_output=True)

    def draw_panel(self):
        panel = pygame.Surface((420, 96), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 140))
        pygame.draw.rect(panel, (0, 160, 255, 160), panel.get_rect(), 1, border_radius=12)
        font = pygame.font.SysFont("segoeui", 20, bold=True)
        small = pygame.font.SysFont("segoeui", 16)
        panel.blit(font.render("TOMIS.AI // NEURAL CORE", True, (180, 220, 255)), (16, 10))
        panel.blit(small.render(f"MASTER: {'ON' if self.m_conn else 'OFF'}", True, (220, 220, 220)), (16, 42))
        panel.blit(small.render(f"ACTIVE TASKS: {self.a_tasks}   LIFETIME: {self.l_tasks}", True, (220, 220, 220)), (16, 62))
        self.screen.blit(panel, (24, self.h - 120))

    def update_particles(self):
        t = time.time() - self.st
        pulse = 95 + int(24 * math.sin(t * 1.0))
        pygame.draw.circle(self.screen, (0, 90, 180), self.center, pulse, 2)
        pygame.draw.circle(self.screen, (0, 180, 255), self.center, pulse // 2, 1)

        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            if p["life"] <= 0 or p["x"] < -20 or p["x"] > self.w + 20 or p["y"] < -20 or p["y"] > self.h + 20:
                p.update(make_particle(self.w, self.h))
            pygame.draw.aaline(self.screen, p["color"], self.center, (int(p["x"]), int(p["y"])))
            pygame.draw.circle(self.screen, p["color"], (int(p["x"]), int(p["y"])), p["size"])

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


if __name__ == "__main__":
    Screensaver().update_render()
"@
    Set-Content -Path (Join-Path $PSScriptRoot "TOMIS_Screensaver.py") -Value $PyCode -Encoding UTF8
}

function Generate-Dashboard {
    $ExistingDashboard = Join-Path $PSScriptRoot "TomisDashboard.py"
    if (Test-Path $ExistingDashboard) {
        Log-Message "Using existing TomisDashboard.py (skip embedded template)."
        return
    }
    $DashCode = @"
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
            'node_name': os.getenv('COMPUTERNAME', os.getenv('HOSTNAME', 'unknown')),
            'active_tasks': count_active_tasks(),
            'emulated_tasks': os.path.exists(TASK_EMULATION_FILE),
            'nodes': nodes,
            'pods': pods
        })
    except Exception as exc:
        return jsonify({'error': f'K3s unreachable: {exc}'}), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=28001)
"@
    Set-Content -Path (Join-Path $PSScriptRoot "TomisDashboard.py") -Value $DashCode -Encoding UTF8
}

function Start-DashboardProcess {
    if (Get-NetTCPConnection -LocalPort 28001 -State Listen -ErrorAction SilentlyContinue) {
        Log-Message "Dashboard already listening on port 28001; skipping start."
        return
    }
    $Python = Get-PythonExecutable
    $DashboardPath = Join-Path $PSScriptRoot "TomisDashboard.py"
    Start-Process -FilePath $Python -ArgumentList "`"$DashboardPath`"" -WorkingDirectory $PSScriptRoot | Out-Null
}

function Start-ScreensaverProcess {
    if (!(Test-GuiAvailable)) {
        Log-Message "No GUI session detected; node will stay active without screensaver."
        return
    }

    $Existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*TOMIS_Screensaver.py*' }
    if ($Existing) {
        Log-Message "Screensaver already running; skipping start."
        return
    }

    $Python = Get-PythonExecutable
    $ScreensaverPath = Join-Path $PSScriptRoot "TOMIS_Screensaver.py"
    Start-Process -FilePath $Python -ArgumentList "`"$ScreensaverPath`"" -WorkingDirectory $PSScriptRoot | Out-Null
    Log-Message "Screensaver started for GUI session."
}

function Test-GPUNode {
    param([string]$NodeName)
    Log-Message "=== GPU DIAGNOSTICS: $NodeName ==="
    
    $NodeInfo = kubectl describe node $NodeName 2>$null
    $HasGPULabel = $NodeInfo -like '*accelerator=nvidia-gpu*'
    $HasGPUCapacity = $NodeInfo -like '*nvidia.com/gpu*'
    
    if ($HasGPULabel -and -not $HasGPUCapacity) {
        Log-Message "[WARNING] GPU label found but NO GPU capacity in Kubernetes - drivers may be missing!"
        return $false
    }
    
    if ($HasGPUCapacity) {
        $GPUCount = $NodeInfo | Select-String 'nvidia.com/gpu:\s+(\d+)' | ForEach-Object { $_.Matches[0].Groups[1].Value }
        Log-Message "[OK] GPU detected: $GPUCount device(s) available"
        return $true
    }
    
    Log-Message "[INFO] No GPU detected on $NodeName (CPU-only mode)"
    return $false
}

function Install-GPUTools {
    param([string]$NodeName, [string]$NodeIP)
    Log-Message "=== GPU TOOLS INSTALLATION: $NodeName ($NodeIP) ==="
    
    if ($NodeName -like '*jetson*') {
        Log-Message "Detected Jetson node - checking NVIDIA tools..."
        $checkCmd = "nvidia-smi 2>/dev/null || echo 'NVIDIA tools missing'"
        # This would require SSH - for now log advisory
        Log-Message "[ADVISORY] Manual installation may be needed on Jetson:"
        Log-Message "  - Install: sudo apt-get install -y nvidia-utils nvidia-cuda-toolkit"
        Log-Message "  - Verify: nvidia-smi && sudo tegrastats --once"
    }
}

function Validate-GPUWorkload {
    param([string]$NodeName)
    Log-Message "=== GPU WORKLOAD TEST: $NodeName ==="
    
    $TestPod = @"
apiVersion: v1
kind: Pod
metadata:
  name: gpu-validation
  namespace: default
spec:
  nodeSelector:
    accelerator: nvidia-gpu
  restartPolicy: Never
  containers:
  - name: gpu-test
    image: nvidia/cuda:11.0-runtime-ubuntu20.04
    imagePullPolicy: IfNotPresent
    command: ["nvidia-smi"]
  tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
"@
    
    $TestPod | kubectl apply -f - 2>$null | Out-Null
    Start-Sleep -Seconds 3
    
    $logs = kubectl logs gpu-validation 2>$null
    if ($logs -like '*CUDA*' -or $logs -like '*GPU*') {
        Log-Message "[OK] GPU workload validated successfully"
        kubectl delete pod gpu-validation 2>$null | Out-Null
        return $true
    } else {
        Log-Message "[WARNING] GPU workload test inconclusive"
        kubectl delete pod gpu-validation 2>$null | Out-Null
        return $false
    }
}

function Start-TaskEmulation {
    Log-Message "=== EMULATING TASK LOAD ==="
    $Python = Get-PythonExecutable
    $EmulatorPath = Join-Path $PSScriptRoot "TOMIS_TaskEmulator.py"
    $EmulatorCode = @"
import json
import os
import time

STATE_FILE = 'task_emulation.json'
LIFETIME_FILE = 'node_stats.txt'

def read_lifetime():
    try:
        if os.path.exists(LIFETIME_FILE):
            with open(LIFETIME_FILE, 'r', encoding='utf-8') as f:
                return int(f.read().strip())
    except Exception:
        pass
    return 0

def write_state(active_tasks, lifetime_tasks):
    payload = {
        'active_tasks': active_tasks,
        'session_tasks': active_tasks,
        'lifetime_tasks': lifetime_tasks,
        'updated_at': time.time()
    }
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    with open(LIFETIME_FILE, 'w', encoding='utf-8') as f:
        f.write(str(lifetime_tasks))

def main():
    lifetime = read_lifetime()
    active = 3
    while True:
        active = 3 + (int(time.time()) % 4)
        lifetime += 1
        write_state(active, lifetime)
        time.sleep(5)

if __name__ == '__main__':
    main()
"@
    Set-Content -Path $EmulatorPath -Value $EmulatorCode -Encoding UTF8

    $Existing = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*TOMIS_TaskEmulator.py*' }
    if ($Existing) {
        Log-Message "Task emulator already running; refreshing state file only."
    } else {
        Start-Process -FilePath $Python -ArgumentList "`"$EmulatorPath`"" -WorkingDirectory $PSScriptRoot | Out-Null
        Log-Message "Local task emulator started."
    }

    if (kubectl get nodes --request-timeout=3s --no-headers 2>$null) {
        $Manifest = @"
apiVersion: v1
kind: Namespace
metadata:
  name: tomis-emulation
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tomis-task-emulator
  namespace: tomis-emulation
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tomis-task-emulator
  template:
    metadata:
      labels:
        app: tomis-task-emulator
    spec:
      containers:
      - name: sleeper
        image: busybox:1.36
        imagePullPolicy: IfNotPresent
        command: ["sh", "-c", "echo TOMIS task emulation started; while true; do sleep 3600; done"]
        resources:
          requests:
            cpu: 5m
            memory: 8Mi
          limits:
            cpu: 20m
            memory: 16Mi
"@
        $ManifestPath = Join-Path $env:TEMP "tomis-task-emulator.yaml"
        Set-Content -Path $ManifestPath -Value $Manifest -Encoding UTF8
        kubectl apply -f $ManifestPath | Out-Host
        Start-Sleep -Seconds 3
        kubectl get pods -n tomis-emulation | Out-Host
    } else {
        Log-Message "Kubernetes is not reachable; local task emulation only."
    }
}

function Download-Essentials {
    Create-Directories
    Log-Message "Downloading Core Binaries (k3d)..."
    if (!(Test-Path (Join-Path $Global:KitDir "k3d.exe"))) {
        curl.exe -L -o (Join-Path $Global:KitDir "k3d.exe") "https://github.com/k3d-io/k3d/releases/latest/download/k3d-windows-amd64.exe"
    }
    if (!(Test-Path "C:\Windows\System32\k3d.exe")) {
        Copy-Item (Join-Path $Global:KitDir "k3d.exe") "C:\Windows\System32\k3d.exe" -Force
    }
}

if ($Role -eq "MASTER") {
    Log-Message "=== INITIALIZING MASTER ROLE ==="
    Download-Essentials
    Generate-Dashboard
    Generate-Screensaver
    
    # Create Cluster (Allowing NodePorts for AI services)
    if (!(Test-ClusterExists)) {
        k3d cluster create tomis-cluster --image $Global:K3sImage --api-port "0.0.0.0:6443" --port "28002-28015:28002-28015@loadbalancer" --k3s-arg "--service-node-port-range=28000-32767@server:0" --wait
    } else {
        Log-Message "tomis-cluster already exists; reusing current cluster."
    }
    
    $IP = Get-PhysicalIPv4Address
    $Token = "TOMIS_SECRET_" + (Get-Random -Minimum 1000 -Maximum 9999)
    $Config = @{ master_ip = $IP; master_token = $Token } | ConvertTo-Json
    Set-Content $Global:ConfigFile $Config
    
    # Label Master as CPU-only (K3d on Windows = no GPU)
    Start-Sleep -Seconds 3
    kubectl label node k3d-tomis-cluster-server-0 "accelerator=cpu-only" --overwrite 2>$null | Out-Null
    Log-Message "[CPU-ONLY] Master node labeled for container scheduling (no GPU support in k3d/Docker Desktop)"
    
    # GPU Diagnostics on Master
    Log-Message "`n=== GPU DIAGNOSTICS SCAN ==="
    $Nodes = kubectl get nodes --no-headers 2>$null
    if ($Nodes) {
        foreach ($NodeLine in $Nodes) {
            $NodeName = ($NodeLine -split '\s+')[0]
            Test-GPUNode -NodeName $NodeName
        }
    }
    
    # Windows GPU Support Info
    Log-Message "`n=== WINDOWS DOCKER GPU STATUS ==="
    $DockerGPU = docker info 2>$null | Select-String -Pattern 'nvidia|gpu' -Quiet
    if ($DockerGPU) {
        Log-Message "[OK] Docker Desktop has GPU support enabled"
    } else {
        Log-Message "[INFO] Windows Master (K3d) runs CPU-only - GPU workloads route to edge nodes (Jetson, specialized servers)"
    }
    
    # Start Dashboard
    Start-DashboardProcess
    Start-ScreensaverProcess
    Log-Message "Master Active at $IP. Dashboard on port 28001."
}
elseif ($Role -eq "NODE") {
    Log-Message "=== INITIALIZING NODE ROLE ==="
    Download-Essentials
    Generate-Screensaver
    if (!(Test-Path $Global:ConfigFile)) { Log-Message "ERROR: config.json missing!"; exit }
    $Conf = Get-Content $Global:ConfigFile | ConvertFrom-Json
    $NodeName = "k3d-tomis-node-$($env:COMPUTERNAME.ToLower())"
    if (!(Test-NodeExists -NodeName $NodeName)) {
        k3d node create "tomis-node-$($env:COMPUTERNAME.ToLower())" --cluster tomis-cluster --k3s-node-label "accelerator=nvidia-gpu"
        Log-Message "Node joined cluster."
    } else {
        Log-Message "Node already present in cluster; skipping create."
    }
    
    # GPU Check on Node after join
    Log-Message "`n=== GPU INITIALIZATION ON NODE ==="
    Start-Sleep -Seconds 5
    Test-GPUNode -NodeName $NodeName
    
    Start-ScreensaverProcess
}
elseif ($Role -in @("EMULATE", "EMULATE_TASKS", "LOAD_TEST")) {
    Log-Message "=== EMULATING TASKS ==="
    Download-Essentials
    Start-TaskEmulation
    Log-Message "Task emulation deployed."
}
