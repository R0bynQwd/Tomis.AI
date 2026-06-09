import json
from flask import Flask, jsonify
import os, subprocess

app = Flask(__name__)
TASK_EMULATION_FILE = 'task_emulation.json'
ACTIVE_STATES = {'Running', 'Pending', 'ContainerCreating', 'CrashLoopBackOff'}

def kubectl_output(args, timeout=2):
    proc = subprocess.run(
        ['kubectl', *args],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or 'kubectl command failed')
    return proc.stdout

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
    nodes = ''
    pods = ''
    cluster_reachable = True
    error = None
    try:
        nodes = kubectl_output(['get', 'nodes', '-o', 'wide'], timeout=2)
        pods = kubectl_output(['get', 'pods', '-A'], timeout=2)
    except Exception as exc:
        cluster_reachable = False
        error = str(exc)

    payload = {
        'node_name': os.getenv('COMPUTERNAME', os.getenv('HOSTNAME', 'unknown')),
        'active_tasks': count_active_tasks(),
        'emulated_tasks': os.path.exists(TASK_EMULATION_FILE),
        'cluster_reachable': cluster_reachable,
        'nodes': nodes,
        'pods': pods
    }
    if error:
        payload['error'] = f'K3s unreachable: {error}'
    return jsonify(payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=28001, threaded=True)
