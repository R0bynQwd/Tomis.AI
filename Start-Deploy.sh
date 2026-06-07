#!/bin/bash
# ==============================================================================
# TOMIS.AI - Unified AI Cluster Core V20 (Master + Dashboard)
# ==============================================================================

KIT_DIR="./Kit_AI_Offline"
LOG_FILE="./deployment_log.txt"
CONFIG_FILE="./config.json"

log() { echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

# --- GENERARE DASHBOARD WEB (MASTER SIDE) ---
generate_dashboard() {
    cat << 'EOF' > TomisDashboard.py
from flask import Flask, render_template_string, jsonify
import subprocess, os, time, threading

app = Flask(__name__)

# CSS - Stealth Theme (HD)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <title>TOMIS.AI COMMAND CENTER</title>
    <style>
        body { background: #050505; color: #ccc; font-family: 'Segoe UI', sans-serif; margin: 0; }
        .header { background: #111; padding: 20px; border-bottom: 2px solid #222; display: flex; justify-content: space-between; align-items: center; }
        .branding { color: #555; font-size: 24px; font-weight: bold; letter-spacing: 2px; }
        .container { padding: 30px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .card { background: #111; border: 1px solid #222; padding: 20px; border-radius: 8px; }
        h2 { color: #008cff; border-bottom: 1px solid #333; padding-bottom: 10px; margin-top: 0; }
        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .stat-box { background: #1a1a1a; padding: 15px; border-radius: 4px; text-align: center; }
        .stat-val { font-size: 28px; font-weight: bold; color: #fff; }
        .stat-label { font-size: 12px; color: #666; text-transform: uppercase; }
        .guide { background: #0a1a2a; border-left: 4px solid #008cff; padding: 15px; font-size: 14px; line-height: 1.6; }
        code { background: #000; color: #00ff41; padding: 2px 5px; border-radius: 3px; }
        .status-online { color: #00ff41; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <div class="branding">ΤΟΜΙΣ.ΑΙ // MASTER_CORE</div>
        <div id="clock">--:--:--</div>
    </div>
    <div class="container">
        <div class="card">
            <h2>CLUSTER STATUS (REAL-TIME)</h2>
            <div class="stat-grid">
                <div class="stat-box"><div class="stat-val" id="node-count">0</div><div class="stat-label">Noduri Active</div></div>
                <div class="stat-box"><div class="stat-val" id="pod-count">0</div><div class="stat-label">Containere AI</div></div>
                <div class="stat-box"><div class="stat-val" id="cpu-load">--%</div><div class="stat-label">Incarcare Cluster</div></div>
                <div class="stat-box"><div class="stat-val" id="task-total">0</div><div class="stat-label">Sarcini Lifetime</div></div>
            </div>
            <div style="margin-top:20px;">
                <p>Nod Windows Master: <span class="status-online" id="master-status">ONLINE</span></p>
                <div id="node-list" style="font-size:13px; color:#888;"></div>
            </div>
        </div>
        
        <div class="card">
            <h2>GHID TRANSMITERE SARCINI</h2>
            <div class="guide">
                <strong>1. OCR (Toate limbile + AutoDetect):</strong><br>
                <code>curl -X POST http://MASTER_IP:28001/api/ocr -F "image=@document.jpg"</code><br><br>
                <strong>2. Whisper ASR (Consens + Detectie 3 Puncte):</strong><br>
                <code>curl -X POST http://MASTER_IP:28001/api/asr -F "audio=@voce.mp3"</code><br><br>
                <strong>3. Vision (Clasificare Obiecte):</strong><br>
                <code>curl -X POST http://MASTER_IP:28001/api/vision -F "media=@video.mp4"</code>
            </div>
            <p style="font-size:12px; color:#555; margin-top:15px;">
                * Sarcina este trimisa automat catre nodul cu cel mai bun GPU.<br>
                * Consensus Engine va valida rezultatul pe 2 noduri diferite.
            </p>
        </div>
    </div>

    <script>
        function updateStats() {
            fetch('/stats').then(res => res.json()).then(data => {
                document.getElementById('node-count').innerText = data.nodes;
                document.getElementById('pod-count').innerText = data.pods;
                document.getElementById('task-total').innerText = data.lifetime;
                document.getElementById('clock').innerText = new Date().toLocaleTimeString();
                
                let nodesHtml = "ACTIVE NODES:<br>";
                data.node_names.forEach(n => { nodesHtml += "» " + n + "<br>"; });
                document.getElementById('node-list').innerHTML = nodesHtml;
            });
        }
        setInterval(updateStats, 3000);
        updateStats();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/stats')
def stats():
    try:
        nodes = subprocess.check_output(["kubectl", "get", "nodes", "--no-headers"], text=True).count("\n")
        node_names = subprocess.check_output(["kubectl", "get", "nodes", "-o", "custom-columns=NAME:.metadata.name", "--no-headers"], text=True).splitlines()
        pods = subprocess.check_output(["kubectl", "get", "pods", "-A", "--no-headers"], text=True).count("\n")
        
        lifetime = 0
        if os.path.exists("node_stats.txt"):
            with open("node_stats.txt", "r") as f: lifetime = f.read().strip()
            
        return jsonify({
            "nodes": nodes,
            "node_names": node_names,
            "pods": pods,
            "lifetime": lifetime
        })
    except:
        return jsonify({"nodes": 0, "node_names": [], "pods": 0, "lifetime": 0})

if __name__ == '__main__':
    print("TOMIS.AI Dashboard starting on port 28001...")
    app.run(host='0.0.0.0', port=28001)
EOF
}

# --- LOGICA MASTER (START DASHBOARD) ---
setup_master() {
    log "Instalare Master V20..."
    generate_dashboard
    # Pornim Dashboard-ul in fundal
    pip3 install flask --quiet
    nohup python3 TomisDashboard.py > dashboard.log 2>&1 &
    log "Dashboard Master activ pe http://$(hostname -I | awk '{print $1}'):28001"

    # --- INTEGRARE MODULE EXTRA ---
    if [ -f "./extra.sh" ]; then
        log "Executie module extra..."
        bash ./extra.sh
    fi
}

# --- MENIU SI LOGICA BASH ---
echo "TOMIS.AI CLUSTER V20"
echo "[1] MASTER [2] NODE [3] KIT OFFLINE [4] UPDATE AI STACK"
read -p "Select: " OPT

case $OPT in
    1) setup_master ;;
    *) log "Executie rol..." ;;
esac
