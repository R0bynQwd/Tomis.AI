param(
    [Parameter(Mandatory=$true)] [string]$Role,
    [Parameter(Mandatory=$false)] [string]$MasterIP = "",
    [Parameter(Mandatory=$false)] [string]$Token = ""
)

$Global:LogFile = Join-Path $PSScriptRoot "deployment_log.txt"
$Global:KitDir = Join-Path $PSScriptRoot "Kit_AI_Offline"
$Global:ConfigFile = Join-Path $PSScriptRoot "config.json"

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

function Generate-Screensaver {
    $PyCode = @"
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
        nn = os.getenv("COMPUTERNAME", "localhost").lower()
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
        font = pygame.font.SysFont("arial", 18)
        while self.run:
            for e in pygame.event.get():
                if e.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN): self.run = False
            self.screen.fill((0,0,0))
            for _ in range(100): pygame.draw.circle(self.screen, (40,40,40), (random.randint(0,self.w), random.randint(0,self.h)), 1)
            txt = font.render(f"TOMIS.AI V21 // MASTER: {'ON' if self.m_conn else 'OFF'} // JOBS: {self.a_tasks} // LIFETIME: {self.l_tasks}", True, (80,80,80))
            self.screen.blit(txt, (self.w - txt.get_width() - 20, self.h - 30))
            pygame.display.flip()
            pygame.time.Clock().tick(60)
        pygame.quit(); sys.exit()

if __name__ == "__main__": Screensaver().update_render()
"@
    Set-Content -Path (Join-Path $PSScriptRoot "TOMIS_Screensaver.py") -Value $PyCode -Encoding UTF8
}

function Generate-Dashboard {
    $DashCode = @"
from flask import Flask, render_template_string, jsonify
import subprocess, os, time
app = Flask(__name__)
@app.route('/')
def home(): return "<h1>TOMIS.AI COMMAND CENTER ACTIVE</h1><p>Check /stats for JSON data.</p>"
@app.route('/stats')
def stats():
    try:
        nodes = subprocess.check_output(["kubectl", "get", "nodes"], text=True)
        pods = subprocess.check_output(["kubectl", "get", "pods", "-A"], text=True)
        return jsonify({"nodes": nodes, "pods": pods})
    except: return jsonify({"error": "K3s unreachable"})
if __name__ == '__main__': app.run(host='0.0.0.0', port=28001)
"@
    Set-Content -Path (Join-Path $PSScriptRoot "TomisDashboard.py") -Value $DashCode -Encoding UTF8
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
    
    # Create Cluster
    k3d cluster create tomis-cluster --port "28001-28015:28001-28015@loadbalancer" --wait
    
    $IP = (Test-Connection -ComputerName $env:COMPUTERNAME -Count 1).IPV4Address.IPAddressToString
    $Token = "TOMIS_SECRET_" + (Get-Random -Minimum 1000 -Maximum 9999)
    $Config = @{ master_ip = $IP; master_token = $Token } | ConvertTo-Json
    Set-Content $Global:ConfigFile $Config
    
    # Start Dashboard
    Start-Process "python" -ArgumentList "TomisDashboard.py" -NoNewWindow
    Log-Message "Master Active at $IP. Dashboard on port 28001."
}
elseif ($Role -eq "NODE") {
    Log-Message "=== INITIALIZING NODE ROLE ==="
    Download-Essentials
    Generate-Screensaver
    if (!(Test-Path $Global:ConfigFile)) { Log-Message "ERROR: config.json missing!"; exit }
    $Conf = Get-Content $Global:ConfigFile | ConvertFrom-Json
    k3d node create "tomis-node-$($env:COMPUTERNAME.ToLower())" --cluster tomis-cluster --k3s-node-label "accelerator=nvidia-gpu"
    Log-Message "Node joined cluster."
}
