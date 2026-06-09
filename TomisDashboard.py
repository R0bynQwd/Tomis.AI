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
