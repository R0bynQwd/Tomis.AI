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
