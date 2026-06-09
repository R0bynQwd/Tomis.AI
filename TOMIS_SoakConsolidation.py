import argparse
import datetime as dt
import json
import math
import os
import socket
import struct
import subprocess
import time
import wave
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

try:
    import paramiko
except Exception:
    paramiko = None


MASTER_URLS = [
    "http://192.168.1.104:28001/stats",
    "http://100.78.68.58:28001/stats",
]

NODES = [
    {"name": "jetson-116", "host": "192.168.1.116"},
    {"name": "edge-117", "host": "192.168.1.117"},
]


def now_iso():
    return dt.datetime.now().isoformat(timespec="seconds")


def check_http(url, timeout=6):
    start = time.perf_counter()
    try:
        with urlopen(url, timeout=timeout) as resp:
            data = resp.read()
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            parsed = {}
            try:
                parsed = json.loads(data.decode("utf-8", "replace"))
            except Exception:
                pass
            return {
                "ok": resp.getcode() == 200,
                "status": resp.getcode(),
                "latency_ms": elapsed_ms,
                "payload": parsed,
                "error": None,
            }
    except URLError as exc:
        return {"ok": False, "status": None, "latency_ms": None, "payload": {}, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status": None, "latency_ms": None, "payload": {}, "error": str(exc)}


def ssh_run(host, username, password, cmd, timeout=20):
    if paramiko is None:
        return {"ok": False, "stdout": "", "stderr": "paramiko unavailable", "error": "paramiko unavailable"}
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        cli.connect(hostname=host, username=username, password=password, timeout=10, banner_timeout=10, auth_timeout=10)
        _, stdout, stderr = cli.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace").strip()
        err = stderr.read().decode("utf-8", "replace").strip()
        return {"ok": True, "stdout": out, "stderr": err, "error": None}
    except Exception as exc:
        return {"ok": False, "stdout": "", "stderr": "", "error": str(exc)}
    finally:
        try:
            cli.close()
        except Exception:
            pass


def local_diagnostics():
    diag = {}
    try:
        ps = (
            "$cpu=(Get-Counter '\\Processor(_Total)\\% Processor Time').CounterSamples.CookedValue; "
            "$os=Get-CimInstance Win32_OperatingSystem; "
            "$free=[math]::Round($os.FreePhysicalMemory/1024,2); "
            "$total=[math]::Round($os.TotalVisibleMemorySize/1024,2); "
            "Write-Output ('CPU=' + [math]::Round($cpu,2)); "
            "Write-Output ('MEM_FREE_MB=' + $free); "
            "Write-Output ('MEM_TOTAL_MB=' + $total); "
            "Write-Output ('PY_DASH=' + ((Get-CimInstance Win32_Process -Filter \"Name=''python.exe''\" | ?{$_.CommandLine -like ''*TomisDashboard.py*''}).Count)); "
            "Write-Output ('PY_SAVER=' + ((Get-CimInstance Win32_Process -Filter \"Name=''python.exe''\" | ?{$_.CommandLine -like ''*TOMIS_Screensaver.py*''}).Count))"
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=20,
        )
        diag["ok"] = r.returncode == 0
        diag["stdout"] = r.stdout.strip()
        diag["stderr"] = r.stderr.strip()
    except Exception as exc:
        diag["ok"] = False
        diag["stdout"] = ""
        diag["stderr"] = str(exc)
    return diag


def remote_probe_cmd():
    return (
        "python3 - <<'PY'\n"
        "import subprocess\n"
        "import os\n"
        "from urllib.request import urlopen\n"
        "print('HOST=', subprocess.getoutput('hostname'))\n"
        "print('UPTIME=', subprocess.getoutput('uptime -p'))\n"
        "print('LOAD=', open('/proc/loadavg','r',encoding='utf-8').read().split()[:3])\n"
        "mem_total=0\n"
        "mem_avail=0\n"
        "for line in open('/proc/meminfo','r',encoding='utf-8'):\n"
        "  if line.startswith('MemTotal:'): mem_total=int(line.split()[1])\n"
        "  if line.startswith('MemAvailable:'): mem_avail=int(line.split()[1])\n"
        "mem_used=max(mem_total-mem_avail,0)\n"
        "print('MEM=', str(mem_used//1024) + '/' + str(mem_total//1024) + 'MB')\n"
        "print('DISK=', subprocess.getoutput(\"df -h / | tail -1 | tr -s ' ' | cut -d ' ' -f3,4,5\"))\n"
        "print('DOCKER=', subprocess.getoutput('systemctl is-active docker || true'))\n"
        "print('K3S_AGENT=', subprocess.getoutput('systemctl is-active k3s-agent || true'))\n"
        "print('K3S_SERVER=', subprocess.getoutput('systemctl is-active k3s || true'))\n"
        "if subprocess.getoutput('pgrep -af tomis_saver_tk36.py || true').strip():\n"
        "  print('SAVER=running')\n"
        "else:\n"
        "  print('SAVER=not-running')\n"
        "ok=False\n"
        "for u in ['http://192.168.1.104:28001/stats','http://100.78.68.58:28001/stats']:\n"
        "  try:\n"
        "    r=urlopen(u, timeout=6)\n"
        "    print('MASTER',u,r.getcode())\n"
        "    ok=True\n"
        "  except Exception as e:\n"
        "    print('MASTER',u,'FAIL',e)\n"
        "print('NODE_OK', ok)\n"
        "PY"
    )


def node_transport_ok(node_result):
    if not node_result.get("ok"):
        return False
    text = node_result.get("stdout", "")
    return "NODE_OK True" in text


def write_tone_wav(path: Path, duration_sec=4, freq=440.0, sample_rate=22050):
    amplitude = 0.4
    total_samples = int(duration_sec * sample_rate)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for n in range(total_samples):
            val = amplitude * math.sin(2 * math.pi * freq * (n / sample_rate))
            pcm = int(max(-1.0, min(1.0, val)) * 32767)
            wf.writeframes(struct.pack("<h", pcm))


def write_tts_wav(path: Path, text: str):
    safe_text = text.replace("'", "''")
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$speak.SetOutputToWaveFile('{str(path)}'); "
        f"$speak.Speak('{safe_text}'); "
        "$speak.Dispose()"
    )
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, (result.stderr.strip() or result.stdout.strip())


def write_simple_pdf(path: Path, title: str, lines):
    esc_lines = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
    y = 760
    content = ["BT", "/F1 12 Tf", "50 800 Td", f"({title}) Tj"]
    for line in esc_lines:
        y -= 16
        content.append(f"50 {y} Td")
        content.append(f"({line}) Tj")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")
    objs = []
    objs.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objs.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objs.append(b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>endobj\n")
    objs.append(b"4 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")
    objs.append(b"5 0 obj<< /Length " + str(len(stream)).encode("ascii") + b" >>stream\n" + stream + b"\nendstream endobj\n")
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii"))
    path.write_bytes(out)


def summarize(entries):
    total = len(entries)
    master_ok = sum(1 for e in entries if any(v.get("ok") for v in e["master"].values()))
    jetson_ok = sum(1 for e in entries if node_transport_ok(e["nodes"].get("jetson-116", {})))
    edge_ok = sum(1 for e in entries if node_transport_ok(e["nodes"].get("edge-117", {})))
    return {
        "iterations": total,
        "master_ok_iterations": master_ok,
        "jetson_ok_iterations": jetson_ok,
        "edge_ok_iterations": edge_ok,
    }


def main():
    parser = argparse.ArgumentParser(description="TOMIS 1h consolidation soak")
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument("--interval", type=int, default=20)
    parser.add_argument("--out-dir", default="soak_artifacts")
    parser.add_argument("--ssh-user", default=os.getenv("TOMIS_SSH_USER", "root"))
    parser.add_argument("--ssh-pass", default=os.getenv("TOMIS_SSH_PASS", ""))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = out_dir / f"soak_{run_id}.jsonl"
    summary_path = out_dir / f"soak_summary_{run_id}.json"
    pdf_path = out_dir / f"soak_report_{run_id}.pdf"
    tts_path = out_dir / f"soak_tts_{run_id}.wav"
    tone_path = out_dir / f"soak_tone_{run_id}.wav"

    end_time = time.time() + args.minutes * 60
    entries = []

    while time.time() < end_time:
        rec = {"ts": now_iso(), "master": {}, "nodes": {}, "master_diag": local_diagnostics()}
        for url in MASTER_URLS:
            rec["master"][url] = check_http(url)

        if args.ssh_pass:
            for node in NODES:
                cmd = remote_probe_cmd()
                rec["nodes"][node["name"]] = ssh_run(node["host"], args.ssh_user, args.ssh_pass, cmd, timeout=25)
        else:
            rec["nodes"]["note"] = {"ok": False, "error": "missing --ssh-pass / TOMIS_SSH_PASS"}

        entries.append(rec)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        time.sleep(max(2, args.interval))

    summary = summarize(entries)
    summary["started"] = entries[0]["ts"] if entries else now_iso()
    summary["ended"] = now_iso()
    summary["log_file"] = str(log_path)

    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_lines = [
        f"Iterations: {summary['iterations']}",
        f"Master OK iterations: {summary['master_ok_iterations']}",
        f"Jetson OK iterations: {summary['jetson_ok_iterations']}",
        f"Edge OK iterations: {summary['edge_ok_iterations']}",
        f"Log: {log_path.name}",
        f"Host: {socket.gethostname()}",
    ]
    write_simple_pdf(pdf_path, "TOMIS Soak Consolidation Report", report_lines)

    ok, _ = write_tts_wav(tts_path, "Tomis consolidation soak completed successfully.")
    if not ok:
        write_tone_wav(tts_path, duration_sec=4, freq=523.25)
    write_tone_wav(tone_path, duration_sec=4, freq=392.0)

    print(json.dumps({
        "summary_file": str(summary_path),
        "pdf_file": str(pdf_path),
        "tts_file": str(tts_path),
        "tone_file": str(tone_path),
        "iterations": summary["iterations"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
