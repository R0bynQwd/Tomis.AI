from flask import Flask, render_template_string, jsonify
import subprocess, os, time, threading

app = Flask(__name__)

# CSS - Stealth Premium Theme
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TOMIS.AI // COMMAND CENTER</title>
    <!-- Bootstrap 5 & Chart.js via CDN -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background: #050505; color: #e0e0e0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .navbar { background: #0a0a0a; border-bottom: 1px solid #1a1a1a; }
        .branding { font-size: 24px; font-weight: bold; letter-spacing: 3px; color: #008cff; }
        .card { background: #0d0d0d; border: 1px solid #1a1a1a; border-radius: 12px; margin-bottom: 20px; }
        .card-header { border-bottom: 1px solid #1a1a1a; color: #00ff41; font-weight: bold; letter-spacing: 1px; }
        .stat-box { text-align: center; padding: 20px; border-right: 1px solid #1a1a1a; }
        .stat-box:last-child { border-right: none; }
        .stat-val { font-size: 32px; font-weight: 800; color: #fff; }
        .stat-label { font-size: 11px; color: #666; text-transform: uppercase; }
        .guide-box { background: #000; border-left: 4px solid #008cff; padding: 15px; margin-bottom: 15px; border-radius: 4px; }
        code { color: #00ff41; }
        .badge-ready { background: #00ff4133; color: #00ff41; border: 1px solid #00ff41; }
        .badge-wait { background: #ffaa0033; color: #ffaa00; border: 1px solid #ffaa00; }
        #clock { color: #555; font-family: 'Consolas', monospace; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark p-3">
        <div class="container-fluid">
            <span class="branding">ΤΟΜΙΣ.ΑΙ // MASTER</span>
            <span id="clock">00:00:00</span>
        </div>
    </nav>

    <div class="container-fluid p-4">
        <div class="row">
            <!-- Colona 1: Statisctici si Grafic -->
            <div class="col-lg-8">
                <div class="card p-0">
                    <div class="d-flex stat-row">
                        <div class="stat-box flex-fill"><div class="stat-val" id="node-count">0</div><div class="stat-label">Active Nodes</div></div>
                        <div class="stat-box flex-fill"><div class="stat-val" id="pod-count">0</div><div class="stat-label">AI Engines</div></div>
                        <div class="stat-box flex-fill"><div class="stat-val" id="task-session">0</div><div class="stat-label">Session Jobs</div></div>
                        <div class="stat-box flex-fill"><div class="stat-val" id="task-total">0</div><div class="stat-label">Lifetime Jobs</div></div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">CLUSTER LOAD ARCHITECTURE</div>
                    <div class="card-body">
                        <canvas id="loadChart" height="150"></canvas>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">NODE REGISTRY</div>
                    <div class="card-body p-0">
                        <table class="table table-dark table-hover mb-0" id="node-table">
                            <thead><tr><th>NAME</th><th>ROLE</th><th>STATUS</th><th>HW ACCEL</th></tr></thead>
                            <tbody id="node-rows"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Colona 2: Ghid API si Statusuri -->
            <div class="col-lg-4">
                <div class="card">
                    <div class="card-header">QUICK START API GUIDE</div>
                    <div class="card-body">
                        <div class="guide-box">
                            <strong>1. WHISPER ASR (Transcribe)</strong><br>
                            <code>curl -X POST http://{{host}}:28002/asr -F "audio=@file.mp3"</code>
                        </div>
                        <div class="guide-box">
                            <strong>2. TESSERACT OCR (Read Image)</strong><br>
                            <code>curl -X POST http://{{host}}:28003/ocr -F "image=@doc.png"</code>
                        </div>
                        <div class="guide-box">
                            <strong>3. OLLAMA LLM (Generate)</strong><br>
                            <code>curl -X POST http://{{host}}:28010/api/generate -d '{"model":"gemma2","prompt":"Hello"}'</code>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">AI POD STATUS</div>
                    <div class="card-body scrollable" style="max-height: 400px; overflow-y: auto;">
                        <div id="pod-list"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('loadChart').getContext('2d');
        const loadChart = new Chart(ctx, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Jobs In Execution', borderColor: '#008cff', data: [], tension: 0.4, fill: true, backgroundColor: 'rgba(0,140,255,0.1)' }] },
            options: { responsive: true, scales: { y: { beginAtZero: true, grid: { color: '#222' } }, x: { grid: { color: '#222' } } }, plugins: { legend: { display: false } } }
        });

        function updateUI() {
            fetch('/stats').then(r => r.json()).then(data => {
                document.getElementById('node-count').innerText = data.nodes_raw.length;
                document.getElementById('pod-count').innerText = data.pods_raw.length;
                document.getElementById('task-total').innerText = data.lifetime;
                document.getElementById('clock').innerText = new Date().toLocaleTimeString();

                // Update Charts
                if (loadChart.data.labels.length > 20) { loadChart.data.labels.shift(); loadChart.data.datasets[0].data.shift(); }
                loadChart.data.labels.push(new Date().toLocaleTimeString().split(' ')[0]);
                loadChart.data.datasets[0].data.push(data.pods_raw.length);
                loadChart.update();

                // Update Nodes
                let nHtml = "";
                data.nodes_raw.forEach(n => {
                    let st = n.includes("Ready") ? '<span class="badge badge-ready">READY</span>' : '<span class="badge badge-wait">SYNCING</span>';
                    let hw = n.includes("nvidia") ? "NVIDIA GPU" : "CPU ONLY";
                    nHtml += `<tr><td>${n.split(' ')[0]}</td><td>Worker</td><td>${st}</td><td>${hw}</td></tr>`;
                });
                document.getElementById('node-rows').innerHTML = nHtml;

                // Update Pods
                let pHtml = "";
                data.pods_raw.forEach(p => {
                    let color = p.includes("Running") ? "#00ff41" : "#ffaa00";
                    pHtml += `<div class="mb-2" style="font-size:12px; border-bottom: 1px solid #1a1a1a; padding-bottom:5px;">
                                <span style="color:${color}">●</span> ${p.split(' ')[0].substring(0,30)}...
                              </div>`;
                });
                document.getElementById('pod-list').innerHTML = pHtml;
            });
        }

        setInterval(updateUI, 3000);
        updateUI();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    host_ip = subprocess.check_output(["hostname", "-I"], text=True).split(' ')[0] if os.name != 'nt' else "localhost"
    return render_template_string(HTML_TEMPLATE, host=host_ip)

@app.route('/stats')
def stats():
    try:
        nodes = subprocess.check_output(["kubectl", "get", "nodes", "-o", "wide", "--no-headers"], text=True).splitlines()
        pods = subprocess.check_output(["kubectl", "get", "pods", "-n", "tomis-ai", "--no-headers"], text=True).splitlines()
        lifetime = 0
        if os.path.exists("node_stats.txt"):
            with open("node_stats.txt", "r") as f: lifetime = f.read().strip()
        return jsonify({
            "nodes_raw": nodes,
            "pods_raw": pods,
            "lifetime": lifetime
        })
    except:
        return jsonify({"nodes_raw": [], "pods_raw": [], "lifetime": 0})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=28001)
